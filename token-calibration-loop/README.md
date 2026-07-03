# Token Calibration Loop

> Part of the **[calibration loop](../calibration-loop.md)** (tokens · time · burn). This
> is the **tokens** probe (manual `ccusage` pass). Its sibling
> [`time-calibration-loop`](../time-calibration-loop/) is the automatic per-turn probe.
> Both feed the same core: `~/.claude/calibration/token-priors.md`.

Learns how many tokens your task-types actually cost, so you can budget against the 5-hr
rolling limit instead of hitting it blind. `ccusage` and the dashboard alone are a
treadmill — they report spend but carry no belief that changes. This loop wraps them:
predict cost *before* the work, score it *after*, and the priors table gets less wrong
over time.

## Files

| File | Role |
|------|------|
| `RUN-A-PASS.md` | **The runbook** — seven moves, snapshot command, rules, proof-of-learning |
| `token-priors.md` | Seed/example template only. The live core is `~/.claude/calibration/token-priors.md` |
| `token-scorecard.example.jsonl` | Example scorecard rows. Live: `~/.claude/calibration/scorecard.jsonl` |
| `install.sh` | Installs the Claude Code SessionStart hook |

## Install

```bash
npm i -g ccusage        # the VERDICT instrument (token snapshots)
bash install.sh         # idempotent; merges into ~/.claude/settings.json
# custom paths: CLAUDE_SETTINGS=... PRIORS_FILE=... bash install.sh
# then open /hooks in Claude Code once, or restart
```

The hook injects the current priors + a run-a-pass nudge at every session start. It never
blocks (`2>/dev/null || true`, 10s timeout) and replaces its own prior entry rather than
stacking.

## Use

Say **"run a token-calibration pass"** and follow [RUN-A-PASS.md](RUN-A-PASS.md).
