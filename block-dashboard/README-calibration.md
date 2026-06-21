# Calibration Dashboard (inside block-dashboard)

Visual twin of `claude-usage-dashboard/token-calibration-loop/reports/calibration-loop-report-2026-06-15.md`.

## Regenerate data
```bash
python aggregate.py --out public/calibration.json   # uses canonical loop sources by default
```
Then `npm run dev` and open the **Calibration** tab. The app loads `public/calibration.json`,
falling back to the committed `public/demo_calibration.json`.

## Sources per panel
- Convergence / Calibration scatter / Feed → `token-scorecard.jsonl` (passes)
- Burn distribution / time-vs-output → `~/.claude/time-loop/durations.log` (turns)
- Belief table → `indodax-bot/docs/loop/token-priors.md`
- Limit → `~/.claude/time-loop/usage-cal.log` (anchors, per-block slope)

All token charts use the **non-cache** basis; only the limit panel uses cache-inclusive totals (the quota basis).
