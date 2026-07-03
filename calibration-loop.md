# Calibration Loop — one loop, two probes (tokens · time · burn)

The umbrella over [`token-calibration-loop/`](token-calibration-loop/) and
[`time-calibration-loop/`](time-calibration-loop/). Same discipline (PREDICT before peek,
score the model not the work), one shared core, joined by **task-type**.

## The model

A turn costs **tokens** and takes **time**. They are linked by a rate:

```
time  ≈  output_tokens / burn_rate
```

- **gen_rate** (pure generation, output tok/s while the model is actually generating) is
  roughly **constant per model**. This is the kernel of truth in "Claude has a constant
  token/sec rate."
- **wall-clock** of a turn is `generation_time + tool_wait` (builds, network, file reads —
  zero tokens produced). So the **effective burn** you observe, `output_tokens /
  wall_clock`, is *diluted* by tool-wait and is **lower on tool-heavy turns**.
- Therefore effective burn is not one global constant — but it **is stable per task-type**
  (each task-type has a characteristic tool-wait profile). `codebase explore` and
  `backtest/study run` are tool-bound (low burn); `design/doc write` and `read+answer` are
  generation-bound (burn ≈ gen_rate).

Given any two of {tokens, time, burn} you predict the third. That is what merges the two
loops: predict tokens → derive time; or measure time → infer tokens; burn_rate is the join.

## The two probes

| Probe | Cadence | Instrument | Measures | Feeds |
|-------|---------|-----------|----------|-------|
| **tokens** | manual pass, output-heavy sessions | `ccusage` snapshots (delta) | non-cache `inputTokens+outputTokens` | priors `tokens (k)` column |
| **time + burn** | **automatic, every turn** | `time-calibration-loop` hooks | wall-clock elapsed + transcript `output_tokens` | priors `time band` / `burn` + `durations.log` |

Both measure the **same per-turn token usage** — the manual pass reads it from `ccusage`
blocks, the automatic Stop hook reads it from the transcript's `message.usage`. A third
calibrated quantity, the **session limit cap**, comes from manual `/usage` pastes
(`usagecal` — see the [time-loop README](time-calibration-loop/README.md)).

## The files (live state vs repo)

Live state lives under `~/.claude/`, **outside this repo**, so pulls and re-installs never
clobber it. The repo ships code, docs, and seeds only.

| Path | Role |
|------|------|
| `~/.claude/calibration/token-priors.md` | **The core.** One row per task-type: `tokens (k) · time band · burn · conf · n · note`. `tokens` moved by manual passes; `time band`/`burn` by the automatic feed. Same 30%-toward-actual distill rule for every column. |
| `~/.claude/calibration/scorecard.jsonl` | Append-only scored predict-vs-actual rows, one per turn (auto) or per pass (manual). The proof-of-learning feed. |
| `~/.claude/time-loop/durations.log` | Per-turn actuals: `iso · elapsed_s · out_tok · noncache_tok · total_tok · tag`. |
| `token-calibration-loop/token-priors.md` (repo) | Seed/example template only — never holds real data. |

## Each turn (automatic) and each pass (manual)

- **Turn:** the `UserPromptSubmit` hook injects `now` + the unified prior, scores the
  previous turn's prediction in-band, and asks for a one-line prediction. The `Stop` hook
  logs actuals and appends the scored row. No effort required; the prior sharpens.
- **Pass:** say "run a token-calibration pass" to reconcile the `tokens (k)` band against
  `ccusage` per [RUN-A-PASS.md](token-calibration-loop/RUN-A-PASS.md).
- **Distill:** `python3 time-calibration-loop/backfill.py` re-derives the whole priors
  table from `durations.log` (preview with `--dry-run`); a manual pass moves one row.

## Install both

```bash
bash token-calibration-loop/install.sh   # SessionStart: inject priors + nudge
bash time-calibration-loop/install.sh    # UserPromptSubmit + Stop: time/token/burn per turn
# then open /hooks once (or restart)
```
