<script setup lang="ts">
import { computed, ref } from 'vue'
import type { CalibrationData, ScatterPoint } from '../types'
import DistributionBar from '../charts/DistributionBar.vue'
import Scatter from '../charts/Scatter.vue'

const props = defineProps<{ data: CalibrationData }>()
const showOutliers = ref(false)
const d = computed(() => props.data.derived)

const clean = computed(() => props.data.turns.filter((t) => !t.unreadable && (showOutliers.value || !t.outlier)))
const burns = computed(() => clean.value.filter((t) => t.elapsed_s > 0).map((t) => t.out / t.elapsed_s))
const minB = computed(() => (burns.value.length ? Math.min(...burns.value) : 0))
const maxB = computed(() => (burns.value.length ? Math.max(...burns.value) : 1))

// time (x) vs output (y); isolines are burn rates (tok/s) -> y = burn * x
const points = computed<ScatterPoint[]>(() => clean.value.map((t) => ({
  x: t.elapsed_s, y: t.out,
  color: t.outlier ? '#f87171' : '#60a5fa',
  label: `${t.tag} · ${t.out} tok / ${t.elapsed_s}s = ${Math.round(t.out / Math.max(1, t.elapsed_s))} tok/s`,
})))
</script>

<template>
  <section class="panel">
    <h2>Burn rate — central tendency, not min/max</h2>
    <DistributionBar :median="d.burn_median" :iqr-lo="d.burn_iqr[0]" :iqr-hi="d.burn_iqr[1]"
      :min="minB" :max="maxB" :markers="[{ value: d.gen_rate_p90, label: 'gen-rate p90', color: '#c084fc' }]" />
    <p class="cap">median {{ d.burn_median }} tok/s · IQR {{ d.burn_iqr[0] }}–{{ d.burn_iqr[1] }} · gen-rate p90 {{ d.gen_rate_p90 }}</p>

    <header class="sh">
      <h3>Time vs output (burn isolines)</h3>
      <label class="tog"><input type="checkbox" v-model="showOutliers" /> show outliers</label>
    </header>
    <Scatter :points="points" :isolines="[50, 124, 195]" x-label="elapsed (s)" y-label="output tokens" :width="340" :height="280" />
    <p class="src">source: durations.log · {{ d.counts.turns }} turns · {{ d.counts.outliers }} outlier(s) excluded from burn · isolines 50/124/195 tok/s</p>
  </section>
</template>

<style scoped>
.cap { font-size: 11px; color: var(--muted); margin: 6px 0 14px; }
.sh { display: flex; justify-content: space-between; align-items: center; }
h3 { font-size: 12px; color: var(--muted); margin: 0; font-weight: 500; }
.tog { font-size: 11px; color: var(--muted); display: flex; gap: 4px; align-items: center; }
.src { font-size: 10px; color: var(--muted); margin: 6px 0 0; }
</style>
