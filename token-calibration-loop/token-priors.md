# token-priors.md — EXAMPLE TEMPLATE (tokens + time + burn)

> This is the **example/template** shipped with the calibration-loop feature. The live,
> per-user priors that the SessionStart hook injects live elsewhere (e.g.
> `indodax-bot/docs/loop/token-priors.md`). Copy this file to your working repo, point the
> hook at that copy, and let the loop calibrate it. Do not put real calibration data here.

Beliefs about cost per task-type. One row = one belief. RECALL reads this; DISTILL
updates exactly one row per pass. This is the shared core of the **calibration loop**
(see `../calibration-loop.md`) — two probes feed it:

- **tokens (k)** — non-cache cost band (`inputTokens+outputTokens`, in thousands).
  Measured by the manual `ccusage` pass (`RUN-A-PASS.md`). Calibrate on the *delta*;
  totalTokens is 80-95% cache overhead and must NOT be used.
- **time band / burn** — wall-clock duration and output-token burn rate. Measured
  **automatically per turn** by `../time-calibration-loop/` (Stop hook reads the
  transcript for tokens + elapsed). `durations.log` is the raw feed.

Bridge identity: **time ≈ output_tokens / burn_rate**. Burn rate is the invariant that
ties the two probes together — given any two, predict the third.

**Generation rate (headline):** pure output generation is ~constant per model; we
estimate gen_rate as the p90 of observed output/sec (turns with little tool-wait).
*Effective* burn = output/wall-clock is diluted by tool-wait, so it is lower on
tool-heavy turns. Per-task-type effective burn is the practical predictor. gen_rate is
unknown until the time loop logs ~10 turns; the prompt hook surfaces the live estimate.

**Output-prediction seed (TBA cross-check):** the ECC `token-budget-advisor` skill predicts
`output ≈ input_tokens × mult`, with complexity multipliers Simple 3-8×, Medium 8-20×,
Code+ctx 10-25×, Complex 15-40×, Creative 10-30×. When non-cache *input* is tiny (context is
cached), non-cache tokens ≈ output tokens — the multiplier predicts the whole band given the
prompt's fresh input size. **Caveat:** the multiplier is output-only; tool-bound rows
(explore/backtest/debug) undershoot it because tool-result tokens aren't in the formula. Seed
rows (n=0) are anchored to the TBA class below; calibrated rows (n>0) keep their measured band.

| task-type          | TBA class (mult)   | tokens (k) | time band | burn (tok/s) | conf | n | last verdict | note |
|--------------------|--------------------|------------|-----------|--------------|------|---|--------------|------|
| read+answer        | Simple–Med (3-20×) | 2 – 6      | —         | —            | 0.30 | 0 | —            | seed=TBA; generation-bound (high burn) |
| single-file edit   | Code+ctx (10-25×)  | 4 – 10     | —         | —            | 0.30 | 0 | —            | seed=TBA |
| multi-file feature | Complex (15-40×)   | 15 – 40    | —         | —            | 0.20 | 0 | —            | seed=TBA |
| codebase explore   | tool-bound (n/a)   | 15 – 50    | —         | —            | 0.20 | 0 | —            | TBA undershoots; tool-result tokens off-formula |
| backtest/study run | tool-bound (n/a)   | 10 – 40    | —         | —            | 0.20 | 0 | —            | TBA undershoots; tool-heavy (low burn) |
| design/doc write   | Complex/Creative   | 7 – 14     | —         | —            | 0.20 | 0 | —            | seed=TBA |
| debug loop         | Complex (15-40×)   | 10 – 40    | —         | —            | 0.15 | 0 | —            | seed≈TBA; high variance |

Rules:
- After each pass, move the matching band ~30% toward the actual, then set confidence by
  recent ON_BUDGET share. Same rule applies to the time/burn columns once populated.
- A BLIND verdict (>60% off) → add `FLAG` to note; if it repeats, split the row into
  finer task-types (the loop's "informative" move).
- **Burn sanity check:** if a row's tokens(k) and time band imply a burn far from the
  gen_rate envelope, the turn was tool-bound — that's signal (low effective burn), not
  error. Tool-bound rows widen the time band without widening tokens.

## Static-overhead audit (context-budget twin) — optional companion check

The dynamic loop above measures *per-turn* cost; the ECC `context-budget` skill audits the
*fixed* per-session input (the constant that inflates every turn's `inputTokens`, mostly
cached). Run it occasionally and record the breakdown: MCP tool schemas (~500 tok/tool —
deferring tools via ToolSearch zeroes this), CLAUDE.md chain, skills list, memory index,
this priors file. Biggest lever is usually MCP eager-load; second is pruning a stale memory
index.
