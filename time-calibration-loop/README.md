# Time Calibration Loop

Wall-clock analog of the [token-calibration-loop](../token-calibration-loop/). Makes
Claude Code time-conscious every turn and trains it to predict how long a task takes,
using the same PREDICT-before-peek discipline as the token loop.

## How it loops

| Hook | Fires | Does |
|------|-------|------|
| `UserPromptSubmit` | every prompt | injects `Wall-clock now: …` + a task-duration prior (median + range of the last 20 turns), records the turn's start epoch, and asks Claude to predict this turn's duration |
| `Stop` | turn end | measures elapsed since start and appends the actual to `durations.log` |

Each turn: predict from prior → work → measure actual → prior sharpens.

## Install (this or any workspace)

```bash
bash time-calibration-loop/install.sh
```

Then open `/hooks` in Claude Code once (or restart) so the hooks load this session.
The installer is **idempotent** — re-run it after `git pull` in a new workspace. It
bakes this package's absolute path into the hook commands, so it works wherever the
repo is cloned. Override the target with `CLAUDE_SETTINGS=/path/to/settings.json`.

Requires `python3` (used to parse the hook payload — `jq` is **not** needed).

## Files

- `time-loop.py` — the hook (modes: `prompt`, `stop`)
- `install.sh` — idempotent merge into `~/.claude/settings.json`
- State (created at runtime, not committed): `~/.claude/time-loop/`
  - `durations.log` — tab-separated `<iso-timestamp>\t<seconds>`, rolling, global
  - `start-<session_id>` — transient per-session start epoch (auto-removed on Stop)

## Inspect / reset / disable

- Recent actuals: `tail ~/.claude/time-loop/durations.log`
- Reset the prior: `rm ~/.claude/time-loop/durations.log`
- Disable: remove the `UserPromptSubmit` + `Stop` blocks from `~/.claude/settings.json`,
  or toggle via `/hooks`. Config is global, so it applies to every project.
