import { describe, it, expect } from 'vitest'
import { linePath, scaleLinear, clamp, fmtPct, fmtSecs, niceTicks } from './format'

describe('scaleLinear', () => {
  it('maps domain to range', () => {
    const s = scaleLinear([0, 10], [0, 100])
    expect(s(0)).toBe(0)
    expect(s(5)).toBe(50)
    expect(s(10)).toBe(100)
  })
  it('handles zero-width domain without NaN', () => {
    const s = scaleLinear([5, 5], [0, 100])
    expect(Number.isFinite(s(5))).toBe(true)
  })
})

describe('linePath', () => {
  it('builds an SVG M/L path from points', () => {
    const d = linePath([{ x: 0, y: 0 }, { x: 1, y: 1 }])
    expect(d.startsWith('M')).toBe(true)
    expect(d).toContain('L')
  })
  it('returns empty string for no points', () => {
    expect(linePath([])).toBe('')
  })
})

describe('clamp', () => {
  it('clamps below/within/above', () => {
    expect(clamp(-1, 0, 1)).toBe(0)
    expect(clamp(0.5, 0, 1)).toBe(0.5)
    expect(clamp(2, 0, 1)).toBe(1)
  })
})

describe('fmtPct', () => {
  it('formats a 0..1 fraction as a percent', () => {
    expect(fmtPct(0.123)).toBe('12%')
    expect(fmtPct(1)).toBe('100%')
  })
})

describe('fmtSecs', () => {
  it('formats seconds as compact m/s', () => {
    expect(fmtSecs(45)).toBe('45s')
    expect(fmtSecs(150)).toBe('2m30s')
  })
})

describe('niceTicks', () => {
  it('returns ascending ticks spanning the range', () => {
    const t = niceTicks(0, 100, 5)
    expect(t[0]).toBeLessThanOrEqual(0)
    expect(t[t.length - 1]).toBeGreaterThanOrEqual(100)
  })
})
