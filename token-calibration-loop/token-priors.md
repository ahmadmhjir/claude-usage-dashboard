# token-priors.md — the carried-forward core (unified: tokens + time + burn)

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

| task-type          | tokens (k) | time band  | burn (tok/s) | conf | n | last verdict | note |
|--------------------|------------|------------|--------------|------|---|--------------|------|
| read+answer        | 2 – 6      | —          | —            | 0.30 | 0 | —            | seed guess; generation-bound (high burn) |
| single-file edit   | 4 – 10     | —          | —            | 0.30 | 0 | —            | seed guess |
| multi-file feature | 20 – 60    | —          | —            | 0.20 | 0 | —            | seed guess |
| codebase explore   | 15 – 50    | —          | —            | 0.20 | 0 | —            | wide, fan-out; tool-bound (low burn) |
| backtest/study run | 10 – 40    | —          | —            | 0.20 | 0 | —            | tool-heavy; tool-bound (low burn) |
| design/doc write   | 7 – 14     | —          | —            | 0.55 | 2 | ON_BUDGET    | actual 11.0k non-cache (pass2); +74.9k delta was 90% cache overhead; generation-bound |
| debug loop         | 10 – 40    | —          | —            | 0.15 | 0 | —            | high variance |

Rules:
- After each pass, move the matching band ~30% toward the actual, then set confidence by
  recent ON_BUDGET share. Same rule applies to the time/burn columns once populated.
- A BLIND verdict (>60% off) → add `FLAG` to note; if it repeats, split the row into
  finer task-types (the loop's "informative" move).
- **Burn sanity check:** if a row's tokens(k) and time band imply a burn far from the
  gen_rate envelope, the turn was tool-bound — that's signal (low effective burn), not
  error. Tool-bound rows widen the time band without widening tokens.
