<script setup lang="ts">
import { computed } from 'vue'
import type { CalibrationData, Series } from '../types'
import LineChart from '../charts/LineChart.vue'
import { fmtPct } from '../format'

const props = defineProps<{ data: CalibrationData }>()
const d = computed(() => props.data.derived)

const mapeSeries = computed<Series[]>(() => [{
  name: 'rolling MAPE', color: '#f87171',
  points: d.value.rolling_mape.map((r) => ({ x: r.pass, y: r.value })),
}])
const shareSeries = computed<Series[]>(() => [{
  name: 'ON_BUDGET share', color: '#34d399',
  points: d.value.on_budget_share.map((r) => ({ x: r.pass, y: r.value })),
}])
const trend = computed(() => {
  const m = d.value.rolling_mape
  if (m.length < 2) return 'not enough passes yet'
  return m[m.length - 1].value < m[0].value ? 'error trending down — learning' : 'error flat/up — treadmill signal'
})
</script>

<template>
  <section class="panel hero">
    <div class="score">
      <div class="big">{{ fmtPct(d.convergence_score) }}</div>
      <div class="lbl">convergence score<br /><span>1 − rolling MAPE</span></div>
      <div class="verdict" :class="{ good: trend.includes('learning') }">{{ trend }}</div>
    </div>
    <div class="charts">
      <div>
        <h3>Rolling prediction error (MAPE) ↓ proves learning</h3>
        <LineChart :series="mapeSeries" :y-min="0" :y-fmt="(v:number)=>fmtPct(v)" />
      </div>
      <div>
        <h3>ON_BUDGET share ↑</h3>
        <LineChart :series="shareSeries" :y-min="0" :y-max="1" :y-fmt="(v:number)=>fmtPct(v)" />
      </div>
    </div>
    <p class="src">source: derived from passes[] · {{ d.counts.passes }} scored passes</p>
  </section>
</template>

<style scoped>
.hero { display: grid; grid-template-columns: 200px 1fr; gap: 20px; align-items: center; }
.score { text-align: center; }
.big { font-size: 56px; font-weight: 700; color: var(--accent); line-height: 1; }
.lbl { color: var(--muted); font-size: 12px; margin-top: 6px; }
.verdict { margin-top: 10px; font-size: 12px; color: #f87171; }
.verdict.good { color: #34d399; }
.charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
h3 { font-size: 12px; color: var(--muted); margin: 0 0 6px; font-weight: 500; }
.src { grid-column: 1 / -1; font-size: 10px; color: var(--muted); margin: 4px 0 0; }
@media (max-width: 820px) { .hero, .charts { grid-template-columns: 1fr; } }
</style>
