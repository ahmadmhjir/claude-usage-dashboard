// Pure, framework-free presentation helpers for the calibration charts.
// Mirrors block-dashboard/src/format.ts ethos: no deps, unit-tested in isolation.

export const VERDICT_COLORS: Record<string, string> = {
  ON_BUDGET: '#34d399', // green
  DRIFT: '#fbbf24',     // amber
  BLIND: '#f87171',     // red
  BAND_HELD: '#60a5fa', // blue
}
export const ACCENT = '#c084fc'

export type Domain = [number, number]

// Linear scale domain->range; zero-width domain maps to range midpoint (no NaN).
export function scaleLinear(domain: Domain, range: Domain): (v: number) => number {
  const [d0, d1] = domain
  const [r0, r1] = range
  const span = d1 - d0
  if (span === 0) return () => (r0 + r1) / 2
  const k = (r1 - r0) / span
  return (v: number) => r0 + (v - d0) * k
}

export function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v
}

// SVG path from already-projected pixel points.
export function linePath(points: { x: number; y: number }[]): string {
  if (!points.length) return ''
  return points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(' ')
}

export function fmtPct(frac: number): string {
  return Math.round(frac * 100) + '%'
}

export function fmtSecs(s: number): string {
  if (s < 60) return `${Math.round(s)}s`
  const m = Math.floor(s / 60)
  const rem = Math.round(s % 60)
  return rem ? `${m}m${rem}s` : `${m}m`
}

// Round, evenly-spaced ticks covering [lo,hi]; count is approximate.
export function niceTicks(lo: number, hi: number, count = 5): number[] {
  if (hi <= lo) return [lo]
  const raw = (hi - lo) / count
  const mag = Math.pow(10, Math.floor(Math.log10(raw)))
  const norm = raw / mag
  const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag
  const start = Math.floor(lo / step) * step
  const out: number[] = []
  for (let t = start; t <= hi + step * 0.5; t += step) out.push(Number(t.toFixed(6)))
  return out
}
