// src/calibration/types.ts
export type Verdict = 'ON_BUDGET' | 'DRIFT' | 'BLIND' | 'BAND_HELD'

export interface PassRow {
  ts: string
  pass: number | null
  type: string
  phase: 'SCORE' | 'RESCORE' | 'OBSERVE'
  pred_k: number | null      // midpoint if source was a range
  actual_k: number | null    // null when source actual was non-numeric
  err: number | null         // |pred-actual|/actual
  verdict: Verdict
  lesson: string             // lesson|note|reason, '' if none
}

export interface TurnRow {
  ts: string
  elapsed_s: number
  out: number
  noncache: number
  total: number | null       // absent on early durations.log rows
  tag: string
  pred_out: number | null
  pred_secs: number | null
  outlier: boolean           // out beyond IQR fence
  unreadable: boolean        // the -1 rows
}

export interface PriorRow {
  profile: string
  burn_lo: number | null
  burn_hi: number | null
  tok_lo: number | null
  tok_hi: number | null
  time_lo: number | null     // seconds
  time_hi: number | null     // seconds
  conf: number
  n: number
  last_verdict: string
  seed: boolean              // n === 0
}

export interface Anchor { ts: string; pct: number; total: number; block_id: number }
export interface BlockFit {
  block_id: number
  slope_tok_per_pp: number | null   // null when <2 anchors
  eff_cap: number | null            // slope * 100
  cache_hit: number | null
  points: Anchor[]
}

export interface Derived {
  rolling_mape: { pass: number; value: number }[]
  on_budget_share: { pass: number; value: number }[]
  convergence_score: number          // 1 - last rolling_mape, clamped >=0
  burn_median: number
  burn_iqr: [number, number]
  gen_rate_p90: number
  counts: { passes: number; turns: number; unreadable: number; outliers: number }
  live_pct: number
  week_pct: number
}

export interface CalibrationData {
  passes: PassRow[]
  turns: TurnRow[]
  priors: PriorRow[]
  anchors: Anchor[]
  blocks: BlockFit[]
  derived: Derived
  generated_at: string
}

// Generic chart inputs (used by all charts/panels)
export interface SeriesPoint { x: number; y: number }
export interface Series { name: string; color: string; points: SeriesPoint[] }
export interface ScatterPoint { x: number; y: number; color: string; label?: string }
