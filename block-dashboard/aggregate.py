#!/usr/bin/env python3
"""Aggregate the calibration loop's raw logs into a single calibration.json.

Single seam between the loop's append-only logs and the dashboard UI. Pure stdlib.
Run with --defaults to use the canonical on-disk source paths, or pass explicit
--scorecard/--durations/--priors/--usage for tests. Missing sources degrade to
empty sections (the dashboard renders a 'no data yet' panel state).
"""
import argparse, json, os, re, statistics, sys
from datetime import datetime, timezone

# ---- canonical source paths (relative to repo root: trading-bot/) ----
HOME = os.path.expanduser("~")
DEFAULTS = {
    "scorecard": "indodax-bot/docs/loop/token-scorecard.jsonl",
    "durations": os.path.join(HOME, ".claude/time-loop/durations.log"),
    "priors":    "indodax-bot/docs/loop/token-priors.md",
    "usage":     os.path.join(HOME, ".claude/time-loop/usage-cal.log"),
}
ROLLING_WINDOW = 5
ON_BUDGET_MAX, DRIFT_MAX = 0.2, 0.6


def _num(x):
    """Coerce a scalar to float, or None. Strings like '6-15'/'~15-25'/'unknown' -> None."""
    if isinstance(x, (int, float)):
        return float(x)
    return None


def _range_mid(x):
    """Midpoint of a numeric or 'a-b'/'a – b' range; None if non-numeric."""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        m = re.findall(r"\d+\.?\d*", x.replace("–", "-"))
        nums = [float(n) for n in m]
        if len(nums) >= 2:
            return (nums[0] + nums[1]) / 2
        if len(nums) == 1 and not re.search(r"[a-zA-Z~]", x):
            return nums[0]
    return None


def _verdict(err):
    if err is None:
        return None
    if err <= ON_BUDGET_MAX:
        return "ON_BUDGET"
    if err <= DRIFT_MAX:
        return "DRIFT"
    return "BLIND"


def load_passes(path):
    if not os.path.exists(path):
        return []
    by_pass = {}   # pass -> chosen metric row (RESCORE supersedes SCORE)
    order = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        phase = r.get("phase")
        if phase not in ("SCORE", "RESCORE", "OBSERVE"):
            continue  # skip PREDICT-only rows
        actual = _num(r.get("actual_k"))
        pred = _range_mid(r.get("pred_k"))
        err = _num(r.get("err"))
        if err is None and actual not in (None, 0) and pred is not None:
            err = abs(pred - actual) / actual
        verdict = r.get("verdict") or _verdict(err) or "BLIND"
        row = {
            "ts": r.get("ts", ""),
            "pass": r.get("pass"),
            "type": r.get("type", ""),
            "phase": phase,
            "pred_k": pred,
            "actual_k": actual,
            "err": err if actual is not None else None,
            "verdict": verdict,
            "lesson": r.get("lesson") or r.get("note") or r.get("reason") or "",
        }
        key = r.get("pass")
        if key is None:
            order.append(("_seq", len(order)))
            by_pass[("_seq", len(order))] = row
        else:
            prev = by_pass.get(key)
            # RESCORE supersedes SCORE; OBSERVE only if nothing else
            if prev is None or phase == "RESCORE" or (phase == "SCORE" and prev["phase"] == "OBSERVE"):
                if key not in by_pass:
                    order.append(key)
                # When RESCORE overrides SCORE, merge to preserve pred_k from SCORE if not in RESCORE
                if prev is not None and phase == "RESCORE" and prev["phase"] == "SCORE":
                    if row["pred_k"] is None and prev["pred_k"] is not None:
                        row["pred_k"] = prev["pred_k"]
                by_pass[key] = row
    return [by_pass[k] for k in order]


def load_turns(path):
    if not os.path.exists(path):
        return [], {}
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        ts, tag = parts[0], parts[-1]
        nums = parts[1:-1]
        try:
            ivals = [int(float(n)) for n in nums]
        except ValueError:
            continue
        # layouts: [elapsed,out,noncache] or [elapsed,out,noncache,total]
        elapsed = ivals[0]
        out = ivals[1] if len(ivals) > 1 else 0
        noncache = ivals[2] if len(ivals) > 2 else out
        total = ivals[3] if len(ivals) > 3 else None
        unreadable = (out < 0 or elapsed < 0)
        rows.append({"ts": ts, "elapsed_s": elapsed, "out": out, "noncache": noncache,
                     "total": total, "tag": tag, "pred_out": None, "pred_secs": None,
                     "outlier": False, "unreadable": unreadable})
    # IQR fence on `out` over readable rows
    outs = sorted(t["out"] for t in rows if not t["unreadable"])
    burn = []
    if len(outs) >= 4:
        q1 = statistics.quantiles(outs, n=3)[0]
        q3 = statistics.quantiles(outs, n=3)[1]
        fence = q3 + 1.5 * (q3 - q1)
        for t in rows:
            if not t["unreadable"] and t["out"] > fence:
                t["outlier"] = True
    for t in rows:
        if not t["unreadable"] and not t["outlier"] and t["elapsed_s"] > 0:
            burn.append(t["out"] / t["elapsed_s"])
    burn_stats = {}
    if burn:
        burn_stats["median"] = statistics.median(burn)
        if len(burn) >= 4:
            qs = statistics.quantiles(burn, n=4)
            burn_stats["iqr"] = [qs[0], qs[2]]
        else:
            burn_stats["iqr"] = [min(burn), max(burn)]
        burn_stats["p90"] = sorted(burn)[max(0, int(len(burn) * 0.9) - 1)]
    return rows, burn_stats


def load_priors(path):
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding="utf-8"):
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            continue
        if cells[0].lower().startswith("task-type") or set(cells[0]) <= set("-: "):
            continue  # header / separator

        def rng(s, unit_secs=False):
            txt = s.replace("–", "-")
            nums = re.findall(r"\d+\.?\d*", txt)
            if len(nums) < 2:
                return None, None
            lo, hi = float(nums[0]), float(nums[1])
            if unit_secs and "m" in txt:   # minutes -> seconds
                lo, hi = lo * 60, hi * 60
            return lo, hi

        tok_lo, tok_hi = rng(cells[2])
        time_lo, time_hi = rng(cells[3], unit_secs=True)
        burn_lo, burn_hi = rng(cells[4])
        try:
            conf = float(cells[5])
        except ValueError:
            conf = 0.0
        try:
            n = int(re.findall(r"\d+", cells[6])[0])
        except (ValueError, IndexError):
            n = 0
        out.append({"profile": cells[0], "burn_lo": burn_lo, "burn_hi": burn_hi,
                    "tok_lo": tok_lo, "tok_hi": tok_hi, "time_lo": time_lo, "time_hi": time_hi,
                    "conf": conf, "n": n, "last_verdict": cells[7], "seed": n == 0})
    return out


def load_anchors(path):
    if not os.path.exists(path):
        return [], []
    anchors = []
    block_id = 0
    prev_total = None
    for line in open(path, encoding="utf-8"):
        parts = line.strip().split("\t")
        if len(parts) < 3:
            continue
        try:
            ts, pct, total = parts[0], float(parts[1]), float(parts[2])
        except ValueError:
            continue
        if prev_total is not None and total < prev_total:
            block_id += 1   # a reset dropped the total -> new block
        prev_total = total
        anchors.append({"ts": ts, "pct": pct, "total": total, "block_id": block_id})
    # group + least-squares slope per block
    blocks = []
    for bid in sorted({a["block_id"] for a in anchors}):
        pts = [a for a in anchors if a["block_id"] == bid]
        slope = eff_cap = None
        if len(pts) >= 2:
            xs = [p["pct"] for p in pts]
            ys = [p["total"] for p in pts]
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            denom = sum((x - mx) ** 2 for x in xs)
            if denom > 0:
                slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
                eff_cap = slope * 100
        blocks.append({"block_id": bid, "slope_tok_per_pp": slope, "eff_cap": eff_cap,
                       "cache_hit": None, "points": pts})
    return anchors, blocks


def derive(passes, turns, burn_stats):
    scored = [p for p in passes if p["err"] is not None]
    rolling, share = [], []
    for i, p in enumerate(scored):
        window = scored[max(0, i - ROLLING_WINDOW + 1): i + 1]
        errs = [w["err"] for w in window]
        rolling.append({"pass": p["pass"] if p["pass"] is not None else i,
                        "value": round(sum(errs) / len(errs), 4)})
        ob = sum(1 for w in window if w["verdict"] == "ON_BUDGET")
        share.append({"pass": p["pass"] if p["pass"] is not None else i,
                      "value": round(ob / len(window), 4)})
    conv = max(0.0, 1 - rolling[-1]["value"]) if rolling else 0.0
    return {
        "rolling_mape": rolling,
        "on_budget_share": share,
        "convergence_score": round(conv, 4),
        "burn_median": round(burn_stats.get("median", 0), 1),
        "burn_iqr": [round(v, 1) for v in burn_stats.get("iqr", [0, 0])],
        "gen_rate_p90": round(burn_stats.get("p90", 0), 1),
        "counts": {
            "passes": len(scored),
            "turns": sum(1 for t in turns if not t["unreadable"]),
            "unreadable": sum(1 for t in turns if t["unreadable"]),
            "outliers": sum(1 for t in turns if t["outlier"]),
        },
        "live_pct": 0,
        "week_pct": 0,
    }


def main():
    ap = argparse.ArgumentParser()
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k}", default=v)
    ap.add_argument("--out", default="public/calibration.json")
    a = ap.parse_args()
    passes = load_passes(a.scorecard)
    turns, burn_stats = load_turns(a.durations)
    priors = load_priors(a.priors)
    anchors, blocks = load_anchors(a.usage)
    data = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "passes": passes, "turns": turns, "priors": priors,
        "anchors": anchors, "blocks": blocks,
        "derived": derive(passes, turns, burn_stats),
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {a.out}: {len(passes)} passes, {len(turns)} turns, {len(blocks)} blocks")


if __name__ == "__main__":
    main()
