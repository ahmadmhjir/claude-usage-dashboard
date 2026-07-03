#!/usr/bin/env python3
"""One-shot (re-runnable) calibration backfill.

The automatic time-loop logs every turn to ~/.claude/time-loop/durations.log but, until
the tagging fix landed, never recorded the task-type — so every historical row is
`untagged` and the live priors (~/.claude/calibration/token-priors.md) are still the
uncalibrated EXAMPLE TEMPLATE (all rows n=0). This script closes that gap from data
already on disk:

  1. scan every Claude Code transcript for PREDICT lines -> (timestamp, task-type)
  2. re-tag each durations.log row by joining it to the PREDICT that started its turn
  3. compute a per-task-type band (tokens / time / burn) from the re-tagged rows
  4. rewrite the live priors table with those bands (and strip the template header)

Idempotent: re-run after more tagged turns accumulate to re-distill. `--dry-run` reads
everything and prints the would-be changes without writing.

Task-type vocab + tagging logic are imported from time-loop.py so there is exactly one
definition of "what counts as a task-type."
"""
import os, re, sys, json, glob, argparse, statistics, importlib.util
from datetime import datetime

# import the sibling hook module despite its hyphenated filename (single source of truth
# for PRIORS/LOG paths + parse_task_type/load_task_types/to_tag/pctl/human_time)
_spec = importlib.util.spec_from_file_location(
    "time_loop", os.path.join(os.path.dirname(os.path.abspath(__file__)), "time-loop.py"))
tl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tl)

PROJECTS = os.path.expanduser("~/.claude/projects")
JOIN_SLACK = 60  # seconds of tolerance when matching a PREDICT to a durations row


def to_epoch(ts):
    """Epoch from either a tz-naive local iso (durations.log) or a UTC '...Z' iso."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


# ---- 1. harvest PREDICT lines from every transcript -----------------------
def scan_predicts(vocab):
    """Return sorted [(epoch, task_type)] for every tagged PREDICT line on disk."""
    hits = []
    for jf in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")):
        try:
            with open(jf) as f:
                for line in f:
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    if o.get("type") != "assistant":
                        continue
                    ts = o.get("timestamp")
                    content = (o.get("message") or {}).get("content") or []
                    if not ts or not isinstance(content, list):
                        continue
                    text = "".join(b.get("text", "") for b in content
                                   if isinstance(b, dict) and b.get("type") == "text")
                    pl = next((ln for ln in text.splitlines()
                               if re.match(r"\s*PREDICT\b", ln, re.I)), None)
                    if not pl:
                        continue
                    tt = tl.parse_task_type(pl, vocab)
                    ep = to_epoch(ts)
                    if tt != "untagged" and ep is not None:
                        hits.append((ep, tt))
        except Exception:
            continue
    hits.sort()
    return hits


def match_tag(row_end, elapsed, hits):
    """Task-type of the PREDICT closest to this turn's start (row_end - elapsed)."""
    start = row_end - elapsed
    lo, hi = start - JOIN_SLACK, row_end + JOIN_SLACK
    best, best_d = None, 1e18
    for ep, tt in hits:
        if ep < lo:
            continue
        if ep > hi:
            break
        d = abs(ep - start)
        if d < best_d:
            best, best_d = tt, d
    return best


# ---- 2. re-tag durations.log ----------------------------------------------
def retag_log(hits, dry):
    """Rewrite field 6 of untagged rows; return (changed, parsed_rows)."""
    try:
        src = open(tl.LOG).read().splitlines()
    except Exception as e:
        print(f"cannot read {tl.LOG}: {e}")
        return 0, []
    out_lines, rows, changed = [], [], 0
    for line in src:
        p = line.split("\t")
        if len(p) >= 6 and p[1].isdigit():
            row_end = to_epoch(p[0])
            elapsed = int(p[1])
            if row_end is not None and p[5].strip() == "untagged":
                tt = match_tag(row_end, elapsed, hits)
                if tt:
                    p[5] = tt
                    changed += 1
            rows.append({
                "elapsed": elapsed,
                "out": int(p[2]) if p[2].lstrip("-").isdigit() and int(p[2]) >= 0 else None,
                "nc": int(p[3]) if p[3].lstrip("-").isdigit() and int(p[3]) >= 0 else None,
                "tag": p[5].strip(),
            })
            out_lines.append("\t".join(p))
        else:
            out_lines.append(line)
    if changed and not dry:
        try:
            open(tl.LOG + ".bak", "w").write("\n".join(src) + "\n")  # safety backup
        except Exception:
            pass
        open(tl.LOG, "w").write("\n".join(out_lines) + "\n")
    return changed, rows


# ---- 3. per-task-type bands ------------------------------------------------
def compute_stats(rows, min_n=3):
    agg = {}
    for r in rows:
        tg = r.get("tag")
        if tg and tg != "untagged":
            agg.setdefault(tg, []).append(r)
    stats = {}
    for tg, rs in agg.items():
        n = len(rs)
        if n < min_n:
            continue
        nc = sorted(r["nc"] for r in rs if r["nc"] is not None)
        ts = sorted(r["elapsed"] for r in rs)
        burns = sorted(r["out"] / r["elapsed"] for r in rs
                       if r["out"] is not None and r["elapsed"] > 0)
        if not nc or not burns:
            continue
        # confidence rises with sample count (heuristic; manual ccusage pass can override)
        conf = round(min(0.85, 0.25 + 0.6 * (n / (n + 8))), 2)
        stats[tg] = {
            "n": n,
            "tokens": f"{tl.pctl(nc, 0.25) / 1000:.0f} – {tl.pctl(nc, 0.75) / 1000:.0f}",
            "time": f"{tl.human_time(tl.pctl(ts, 0.25))} – {tl.human_time(tl.pctl(ts, 0.75))}",
            "burn": f"{statistics.median(burns):.0f}",
            "conf": conf,
        }
    return stats


# ---- 4. rewrite the live priors table -------------------------------------
def rewrite_priors(stats, dry):
    try:
        src = open(tl.PRIORS).read()
    except Exception as e:
        print(f"cannot read priors {tl.PRIORS}: {e}")
        return
    lines = src.splitlines()

    # strip the EXAMPLE-TEMPLATE preamble: replace everything before the first content
    # paragraph ("Beliefs about cost...") with a clean live-ledger header
    try:
        bi = next(i for i, l in enumerate(lines)
                  if l.strip().startswith("Beliefs about cost per task-type"))
        header = [
            "# token-priors.md — calibrated (tokens + time + burn)",
            "",
            f"> Live calibration ledger — auto-seeded from durations.log by backfill.py "
            f"on {datetime.now().date()}.",
            "> One row per task-type; re-run backfill.py to re-distill from new tagged turns.",
            "",
        ]
        lines = header + lines[bi:]
    except StopIteration:
        pass  # already stripped or unexpected shape — just refresh the rows

    res, changed, diff = [], 0, []
    for l in lines:
        s = l.strip()
        if s.startswith("|") and "task-type" not in s and not set(s) <= set("|-: "):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 9:
                tag = tl.to_tag(cells[0])
                st = stats.get(tag)
                if st:
                    diff.append(f"  {tag}: tokens '{cells[2]}' -> '{st['tokens']}' "
                                f"(n {cells[6]} -> {st['n']})")
                    cells[2], cells[3], cells[4] = st["tokens"], st["time"], st["burn"]
                    cells[5], cells[6] = str(st["conf"]), str(st["n"])
                    cells[7] = "backfill"
                    cells[8] = (re.sub(r";?\s*backfilled.*$", "", cells[8]).strip()
                                + f"; backfilled n={st['n']}").lstrip("; ")
                    changed += 1
                    l = "| " + " | ".join(cells) + " |"
        res.append(l)

    print(f"priors rows calibrated: {changed}")
    for d in diff:
        print(d)
    if dry:
        print(f"[dry-run] {tl.PRIORS} left unchanged")
    else:
        open(tl.PRIORS, "w").write("\n".join(res) + "\n")
        print(f"wrote {tl.PRIORS}")


def main():
    ap = argparse.ArgumentParser(description="Backfill calibration priors from logged turns.")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    a = ap.parse_args()

    vocab = tl.load_task_types()
    hits = scan_predicts(vocab)
    print(f"scanned {len(hits)} tagged PREDICT lines across transcripts")
    changed, rows = retag_log(hits, a.dry_run)
    print(f"durations.log: {changed} rows re-tagged "
          f"({sum(1 for r in rows if r['tag'] != 'untagged')}/{len(rows)} now tagged)"
          + (" [dry-run]" if a.dry_run else ""))
    stats = compute_stats(rows)
    if not stats:
        print("no task-type reached n>=3 yet — priors left as seeds.")
        return
    print("per-task-type bands:")
    for tg in sorted(stats):
        st = stats[tg]
        print(f"  {tg}: n={st['n']} tokens={st['tokens']}k time={st['time']} "
              f"burn={st['burn']} tok/s conf={st['conf']}")
    rewrite_priors(stats, a.dry_run)


if __name__ == "__main__":
    main()
