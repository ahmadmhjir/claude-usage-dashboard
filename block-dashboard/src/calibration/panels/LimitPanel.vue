<script setup lang="ts">
import { computed } from 'vue'
import type { CalibrationData, ScatterPoint } from '../types'
import Scatter from '../charts/Scatter.vue'
import Gauge from '../charts/Gauge.vue'
import { fmtTokens } from '../../format'

const props = defineProps<{ data: CalibrationData }>()
const d = computed(() => props.data.derived)
const BLOCK_COLORS = ['#60a5fa', '#c084fc', '#34d399', '#fbbf24', '#f87171']

// one scatter per block so each carries its own slope label (no global line)
const points = computed<ScatterPoint[]>(() =>
  props.data.anchors.map((a) => ({
    x: a.pct, y: a.total, color: BLOCK_COLORS[a.block_id % BLOCK_COLORS.length],
    label: `block ${a.block_id}: ${a.pct}% → ${fmtTokens(a.total)}`,
  })))
const fits = computed(() => props.data.blocks.map((b) => ({
  id: b.block_id, color: BLOCK_COLORS[b.block_id % BLOCK_COLORS.length],
  slope: b.slope_tok_per_pp, eff_cap: b.eff_cap, cache: b.cache_hit,
})))
</script>

<template>
  <section class="panel">
    <h2>Limit — no global cap (slope varies with cache mix)</h2>
    <Scatter :points="points" x-label="session %" y-label="cumulative tokens" :width="360" :height="280" />
    <ul class="blocks">
      <li v-for="f in fits" :key="f.id">
        <span class="dot" :style="{ background: f.color }" />
        block {{ f.id }}:
        <strong v-if="f.slope != null">{{ fmtTokens(f.slope) }}/pp</strong><strong v-else>n/a (1 anchor)</strong>
        <span v-if="f.eff_cap != null"> → eff cap {{ fmtTokens(f.eff_cap) }}</span>
        <span v-if="f.cache != null" class="cache">cache {{ Math.round(f.cache * 100) }}%</span>
      </li>
    </ul>
    <div class="gauges">
      <Gauge :pct="d.live_pct" label="session (live proxy)" caption="resets each 5h block" />
      <Gauge :pct="d.week_pct" label="weekly ceiling" caption="the binding constraint" :warn="85" />
    </div>
    <p class="src">source: usage-cal.log · per-block least-squares slope · within-block slope is the only stable cap</p>
  </section>
</template>

<style scoped>
.blocks { list-style: none; padding: 0; margin: 10px 0; font-size: 12px; color: var(--muted); display: flex; flex-direction: column; gap: 5px; }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; }
strong { color: var(--text); }
.cache { margin-left: 8px; font-style: italic; }
.gauges { display: flex; flex-direction: column; gap: 12px; margin: 14px 0; }
.src { font-size: 10px; color: var(--muted); margin: 6px 0 0; }
</style>
