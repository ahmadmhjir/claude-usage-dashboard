<script setup lang="ts">
import { computed, ref } from 'vue'
import type { CalibrationData, ScatterPoint } from '../types'
import Scatter from '../charts/Scatter.vue'
import { VERDICT_COLORS } from '../format'

const props = defineProps<{ data: CalibrationData }>()
type Win = 'all' | 'first' | 'second'
const win = ref<Win>('all')

const scored = computed(() => props.data.passes.filter((p) => p.actual_k != null && p.pred_k != null))
const windowed = computed(() => {
  const s = scored.value
  if (win.value === 'all') return s
  const half = Math.ceil(s.length / 2)
  return win.value === 'first' ? s.slice(0, half) : s.slice(half)
})
const points = computed<ScatterPoint[]>(() => windowed.value.map((p) => ({
  x: p.pred_k as number, y: p.actual_k as number,
  color: VERDICT_COLORS[p.verdict] ?? '#94a3b8',
  label: `pass ${p.pass ?? '?'} ${p.type}: pred ${p.pred_k}k → actual ${p.actual_k}k (${p.verdict})`,
})))
</script>

<template>
  <section class="panel">
    <header class="ph">
      <h2>Predicted vs actual (non-cache k)</h2>
      <div class="seg">
        <button v-for="w in (['all','first','second'] as const)" :key="w"
          :class="{ on: win === w }" @click="win = w">{{ w }}</button>
      </div>
    </header>
    <Scatter :points="points" :diagonal="true" x-label="predicted k" y-label="actual k" :width="340" :height="320" />
    <div class="legend">
      <span><i style="background:#34d399" />ON_BUDGET</span>
      <span><i style="background:#fbbf24" />DRIFT</span>
      <span><i style="background:#f87171" />BLIND</span>
      <span class="diag-key">dashed = perfect prediction</span>
    </div>
    <p class="src">source: passes[] (non-cache basis) · n={{ points.length }} of {{ scored.length }}</p>
  </section>
</template>

<style scoped>
.ph { display: flex; justify-content: space-between; align-items: center; }
.seg { display: flex; gap: 0; }
.seg button { background: var(--track); border: 1px solid var(--border); color: var(--muted); font-size: 11px; padding: 3px 9px; cursor: pointer; }
.seg button.on { background: var(--accent); color: #0b1020; }
.legend { display: flex; gap: 14px; flex-wrap: wrap; font-size: 11px; color: var(--muted); margin-top: 8px; align-items: center; }
.legend i { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 4px; }
.diag-key { font-style: italic; }
.src { font-size: 10px; color: var(--muted); margin: 6px 0 0; }
</style>
