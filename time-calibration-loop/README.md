# Time Calibration Loop — the automatic probe (time · tokens · burn)

> Part of the **[calibration loop](../calibration-loop.md)**. This is the **automatic
> per-turn probe**; its sibling [`token-calibration-loop`](../token-calibration-loop/) is
> the manual scored `ccusage` token pass. Both feed the same core, `token-priors.md`.

Makes Claude Code time-conscious every turn and trains it to predict, per turn, how many
**tokens** it will produce, how long it will take, and therefore the **burn rate**
(output tok/s). Same PREDICT-before-peek discipline as the token loop — but fully
automatic, because each turn's actuals are measured for free.

## How it loops

| Hook | Fires | Does |
|------|-------|------|
| `UserPromptSubmit` | every prompt | injects `Wall-clock now: …` + the unified prior (time band, output-token band, effective burn, gen-rate p90 over the last 20 turns), **scores the previous turn** (`Last turn scored, predicted: … -> actual … [err tok/time]`), records the turn's start epoch, and asks Claude to predict {task-type, output tokens, wall-clock time} consistent with `time ≈ tokens / burn` |
| `Stop` | turn end | measures elapsed since start **and reads the transcript** (`message.usage`) to sum this turn's `output_tokens` and non-cache tokens, appends one row to `durations.log`, **and stashes this turn's `PREDICT` line + actuals to `pair-<sid>.json`** for the next prompt to score |

Each turn: predict from prior → work → auto-measure tokens + time → **see the predict-vs-actual
error in-band next turn** → prior sharpens. No manual snapshot needed; the transcript already
carries both the PREDICT line and per-message token usage.

### Predict-vs-actual scoring (closed loop)

The PREDICT half and the actual half used to live apart: the model predicted, the actuals
were logged silently, and nothing paired them. Now `Stop` extracts the turn's `PREDICT`
line from the transcript and stores it with the measured `output`/`elapsed`; the next
`UserPromptSubmit` reads that pair, best-effort parses the predicted token (`3.5k`) and
time (`50s`/`2m30s`) figures, and prints the error ratio (`actual / predicted`). The pair
file is consumed once, fails silent, and degrades to actuals-only when no PREDICT line is
found or the numbers aren't parseable. DISTILL (updating `token-priors.md`) stays manual,
but the per-turn error is now visible every turn — a `>1.6x` miss is the BLIND signal to
re-anchor a row.

## Why burn rate

`time ≈ output_tokens / burn_rate`. Pure generation rate is ~constant per model, but a
turn's wall-clock also includes tool-wait (builds, network) where no tokens are produced,
so observed *effective* burn is lower on tool-heavy turns. The loop reports both: median
effective burn and a gen-rate estimate (p90 of output/sec). See
[`../calibration-loop.md`](../calibration-loop.md) for the full model.

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
pairs. **Basis = total tokens** (incl cache), not non-cache: measured 2026-06-14, across two
`/usage` reads (12%→18%) non-cache barely moved (+11k) while total grew +2.5M — cache-hit
~97%, so the quota follows total/cost. Between pastes, the `UserPromptSubmit` hook
**extrapolates** the current % by adding the per-turn total tokens logged in `durations.log`
since the anchor — local-file reads only, no ccusage call, so it adds no per-turn latency.
Each new paste re-anchors and removes drift. It is a **proxy** (`/usage` is cost-weighted;
total is raw cache-inclusive tokens) and is labelled as such in the injected line.

## Install (this or any workspace)

```bash
bash time-calibration-loop/install.sh
```

Then open `/hooks` in Claude Code once (or restart) so the hooks load this session.
The installer is **idempotent** — re-run it after `git pull` in a new workspace. It
bakes this package's absolute path into the hook commands, so it works wherever the
repo is cloned. Override the target with `CLAUDE_SETTINGS=/path/to/settings.json`.

Requires `python3` (parses the hook payload + transcript — `jq` is **not** needed).

## Files

- `time-loop.py` — the hook (modes: `prompt`, `stop`)
- `usagecal.py` — `/usage` → cap calibration CLI (`record`, `status`)
- `install.sh` — idempotent merge of the two hooks into `~/.claude/settings.json`
- State (created at runtime, not committed): `~/.claude/time-loop/`
  - `durations.log` — tab-separated
    `<iso>\t<elapsed_s>\t<out_tok>\t<noncache_tok>\t<total_tok>\t<tag>`, rolling, global
    (older 4/5-field rows still read; missing columns skipped)
  - `start-<session_id>` — transient per-session start epoch (auto-removed on Stop)
  - `tag-<session_id>` — optional task-type tag for the next Stop (write to enrich the
    join with `token-priors.md`; defaults to `untagged`)
  - `usage-cal.log` / `usage-state.json` — `/usage` anchor pairs + the current cap estimate

## Inspect / reset / disable

- Recent actuals (time + tokens + burn): `tail ~/.claude/time-loop/durations.log`
- Reset the prior: `rm ~/.claude/time-loop/durations.log`
- Tag a turn's task-type: `echo "multi-file feature" > ~/.claude/time-loop/tag-<session_id>`
- Disable: remove the `UserPromptSubmit` + `Stop` blocks from `~/.claude/settings.json`,
  or toggle via `/hooks`. Config is global, so it applies to every project.
