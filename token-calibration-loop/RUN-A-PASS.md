# Run a pass

Trigger: say **"run a token-calibration pass"**. This is the **manual tokens probe** of the
[calibration loop](../calibration-loop.md) — worth running on output-heavy sessions to
reconcile the priors' `tokens (k)` column against ground truth. (Per-turn time/burn scoring
is already automatic via the time-loop hooks; this pass is the ccusage cross-check.)

State touched: priors `~/.claude/calibration/token-priors.md`, scorecard
`~/.claude/calibration/scorecard.jsonl`. Both live outside the repo.

## The seven moves

```
0 POP      pick task-type from the priors table (or tag a new one)
1 RECALL   read that row's band + confidence
2 PREDICT  append {phase:PREDICT, pred_k, conf} to scorecard.jsonl   <-- BEFORE work
3 RUN      START snapshot -> do the task -> END snapshot
4 VERDICT  actual_k = (END - START) / 1000     (delta only; absolute is useless)
5 SCORE    err = |pred-actual|/actual -> ON_BUDGET(<=.2) / DRIFT(.2-.6) / BLIND(>.6)
6 DISTILL  move that one row's band ~30% toward actual; n+1; set confidence by
           recent ON_BUDGET share
```

A pass is done when the scorecard holds both the PREDICT row and the scored row, and
exactly one priors row changed.

## Snapshot command (START and END)

Measure **non-cache** tokens (inputTokens+outputTokens). totalTokens is 80-95% cache
read/create = fixed per-turn context overhead, NOT task work (lesson from pass 2).

```bash
ccusage blocks --json | python3 -c "import sys,json;d=json.load(sys.stdin);b=[x for x in d['blocks'] if x.get('isActive')];c=(b[0] if b else d['blocks'][-1])['tokenCounts'];print(c['inputTokens']+c['outputTokens'])"
```

Save START to a scratch file, run END the same way after the task, subtract. Track cache
overhead separately if you care about the 5-hr rolling budget (it counts there), but
calibrate task bands on the non-cache delta only.

## Two non-negotiables

- **Rule A — predict before peek.** The PREDICT line lands in the scorecard before the
  START snapshot. Otherwise the scorecard is a mirror and proves nothing.
- **Rule B — score the model, not the work.** Grade whether the band was right, not
  whether the task was good. Block-cumulative totals are noise; only the delta is signal
  (the lesson pass 1 paid for with a BLIND).

## Proof it's learning, not a treadmill

After 5+ passes of a type: rolling MAPE must trend down and ON_BUDGET share up. Flat MAPE
→ split the task-type into finer rows, or pull the `token-efficient` lever to shrink the
per-task cost. A repeated BLIND on one row → add `FLAG` to its note and split it.

HALT before any pass whose predicted band would blow the remaining 5-hr rolling budget —
defer the task or shrink it first. This is the loop paying rent.
