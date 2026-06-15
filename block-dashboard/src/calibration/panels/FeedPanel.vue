<script setup lang="ts">
import { computed } from 'vue'
import type { CalibrationData } from '../types'
import { VERDICT_COLORS, linePath, scaleLinear } from '../format'

const props = defineProps<{ data: CalibrationData }>()
const counts = computed(() => props.data.derived.counts)
const feed = computed(() => [...props.data.passes].reverse())

// per-profile MAPE sparkline paths (40x14 viewbox)
const sparks = computed(() => {
  const byType = new Map<string, number[]>()
  for (const p of props.data.passes) {
    if (p.err == null) continue
    const arr = byType.get(p.type) ?? []
    arr.push(p.err)
    byType.set(p.type, arr)
  }
  const out: { type: string; d: string; last: number }[] = []
  for (const [type, errs] of byType) {
    if (errs.length < 2) { out.push({ type, d: '', last: errs[errs.length - 1] }); continue }
    const sx = scaleLinear([0, errs.length - 1], [1, 39])
    const sy = scaleLinear([0, Math.max(...errs)], [13, 1])
    out.push({ type, d: linePath(errs.map((e, i) => ({ x: sx(i), y: sy(e) }))), last: errs[errs.length - 1] })
  }
  return out
})
</script>

<template>
  <section class="panel">
    <h2>Pass feed &amp; data quality</h2>
    <div class="counts">
      <span><b>{{ counts.passes }}</b> passes</span>
      <span><b>{{ counts.turns }}</b> turns</span>
      <span class="warn"><b>{{ counts.unreadable }}</b> unreadable (−1)</span>
      <span><b>{{ counts.outliers }}</b> outliers</span>
    </div>

    <h3>Per-profile error trend</h3>
    <ul class="sparks">
      <li v-for="s in sparks" :key="s.type">
        <span class="st">{{ s.type }}</span>
        <svg viewBox="0 0 40 14" class="spark"><path :d="s.d" /></svg>
        <span class="sl">{{ (s.last * 100).toFixed(0) }}%</span>
      </li>
    </ul>

    <h3>Narrative</h3>
    <ul class="feed">
      <li v-for="(p, i) in feed" :key="i">
        <span class="badge" :style="{ background: VERDICT_COLORS[p.verdict] || '#94a3b8' }">{{ p.verdict }}</span>
        <span class="meta">#{{ p.pass ?? '—' }} {{ p.type }} · pred {{ p.pred_k ?? '?' }}k → actual {{ p.actual_k ?? '?' }}k</span>
        <span v-if="p.lesson" class="lesson">{{ p.lesson }}</span>
      </li>
    </ul>
    <p class="src">source: token-scorecard.jsonl · −1 rate {{ counts.turns + counts.unreadable ? Math.round(counts.unreadable / (counts.turns + counts.unreadable) * 100) : 0 }}% of turns</p>
  </section>
</template>

<style scoped>
.counts { display: flex; gap: 16px; font-size: 12px; color: var(--muted); margin-bottom: 14px; flex-wrap: wrap; }
.counts b { color: var(--text); font-size: 15px; }
.counts .warn b { color: #f87171; }
h3 { font-size: 12px; color: var(--muted); margin: 12px 0 6px; font-weight: 500; }
.sparks { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 4px; }
.sparks li { display: grid; grid-template-columns: 1fr 44px 36px; align-items: center; font-size: 11px; color: var(--muted); gap: 8px; }
.spark { width: 44px; height: 14px; }
.spark path { fill: none; stroke: var(--accent); stroke-width: 1.2; }
.sl { text-align: right; }
.feed { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; max-height: 280px; overflow-y: auto; }
.feed li { font-size: 11px; line-height: 1.4; }
.badge { display: inline-block; color: #0b1020; font-weight: 600; padding: 1px 6px; border-radius: 4px; font-size: 9px; margin-right: 6px; }
.meta { color: var(--text); }
.lesson { display: block; color: var(--muted); margin-top: 2px; }
.src { font-size: 10px; color: var(--muted); margin: 10px 0 0; }
</style>
