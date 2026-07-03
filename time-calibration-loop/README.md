# Time Calibration Loop — the automatic probe (time · tokens · burn)

> Part of the **[calibration loop](../calibration-loop.md)**. This is the **automatic
> per-turn probe**; its sibling [`token-calibration-loop`](../token-calibration-loop/) is
> the manual scored `ccusage` pass. Both feed the same core:
> `~/.claude/calibration/token-priors.md`.

Makes Claude Code time-conscious every turn and trains it to predict, per turn, its
output **tokens**, **wall-clock time**, and therefore **burn rate** (output tok/s) — the
`time ≈ tokens / burn` model lives in the [umbrella doc](../calibration-loop.md). Fully
automatic: each turn's actuals are measured for free from the hook payload + transcript.

## How it loops

| Hook | Fires | Does |
|------|-------|------|
| `UserPromptSubmit` | every prompt | injects `Wall-clock now: …` + the unified prior (per-task-type bands over recent turns), **scores the previous turn** (`Last turn scored, predicted: … -> actual … [err tok/time]`), records the turn's start epoch, and asks for a one-line prediction {task-type, output tokens, time} consistent with `time ≈ tokens / burn` |
| `Stop` | turn end | measures elapsed, sums the turn's `output_tokens` + non-cache tokens from the transcript (`message.usage`), appends one row to `durations.log`, extracts the turn's PREDICT line, and appends the scored predict-vs-actual pair to `scorecard.jsonl` |

Scoring degrades gracefully: no PREDICT line or unparseable numbers → actuals-only row,
fail-silent. A `>1.6x` token miss is the BLIND signal to re-anchor a priors row. DISTILL
(updating the priors table) stays manual: `python3 backfill.py` re-derives the whole table
from `durations.log` (preview with `--dry-run`).

## Limit calibration (usagecal)

The authoritative 5h-session limit % lives only in the interactive `/usage` panel, which
the model can't poll. `usagecal.py` turns each manual `/usage` paste into a self-correcting
cap prior:

```bash
# when you paste /usage, anchor it (reads ccusage once, back-computes the cap):
python3 usagecal.py record 12 --week 36 --reset "Jun 15 2:50am"
python3 usagecal.py status          # cap + current % (authoritative ccusage read)
```

`cap ≈ total_tokens / (session_pct/100)`; the stored cap is the median over all pasted
pairs. **Basis = total tokens** (incl cache), not non-cache: measured 2026-06-14, across
two `/usage` reads non-cache barely moved (+11k) while total grew +2.5M — cache-hit ~97%,
so the quota follows total/cost. Between pastes, the `UserPromptSubmit` hook
**extrapolates** the current % from the per-turn totals in `durations.log` — local reads
only, no ccusage call, no added latency. Each new paste re-anchors. It is a **proxy**
(`/usage` is cost-weighted) and is labelled as such in the injected line.

## Install (this or any workspace)

```bash
bash time-calibration-loop/install.sh
```

Then open `/hooks` in Claude Code once (or restart). The installer is **idempotent** —
re-run it after `git pull` or in a new clone; it bakes this package's absolute path into
the hook commands. Override the target with `CLAUDE_SETTINGS=/path/to/settings.json`.
Requires `python3` only (`jq` not needed).

## Files

- `time-loop.py` — the hook (modes: `prompt`, `stop`)
- `backfill.py` — re-derive the whole priors table from `durations.log` (re-tags history
  by joining rows to transcript PREDICT lines); `--dry-run` reports without writing
- `usagecal.py` — `/usage` → cap calibration CLI (`record`, `status`)
- `install.sh` — idempotent merge of the two hooks into `~/.claude/settings.json`
- State (created at runtime, never committed):
  - `~/.claude/time-loop/durations.log` — tab-separated
    `<iso>\t<elapsed_s>\t<out_tok>\t<noncache_tok>\t<total_tok>\t<tag>`, rolling, global
    (older 4/5-field rows still read). `<tag>` is the task-type, parsed automatically
    from the turn's PREDICT line — no manual tagging
  - `~/.claude/time-loop/start-<sid>` / `pair-<sid>.json` — transient per-session state
    (consumed on the next hook fire; stale files reaped after ~12h)
  - `~/.claude/time-loop/usage-cal.log` / `usage-state.json` — `/usage` anchors + cap estimate
  - `~/.claude/calibration/token-priors.md` + `scorecard.jsonl` — the learned table and
    the per-turn scored feed (the proof-of-learning substrate)

## Inspect / reset / disable

- Recent actuals: `tail ~/.claude/time-loop/durations.log`
- Reset the prior: `rm ~/.claude/time-loop/durations.log`
- Re-distill priors from the log: `python3 backfill.py` (preview with `--dry-run`)
- Disable: remove the `UserPromptSubmit` + `Stop` blocks from `~/.claude/settings.json`,
  or toggle via `/hooks`. Config is global — applies to every project.
