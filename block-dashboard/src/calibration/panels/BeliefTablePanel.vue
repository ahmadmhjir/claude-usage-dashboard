<script setup lang="ts">
import { computed } from 'vue'
import type { CalibrationData } from '../types'
import { fmtSecs } from '../format'

const props = defineProps<{ data: CalibrationData }>()
const rows = computed(() => props.data.priors)
const band = (lo: number | null, hi: number | null, suffix = '') =>
  lo == null || hi == null ? '—' : `${lo}–${hi}${suffix}`
const timeBand = (lo: number | null, hi: number | null) =>
  lo == null || hi == null ? '—' : `${fmtSecs(lo)}–${fmtSecs(hi)}`
</script>

<template>
  <section class="panel">
    <h2>Belief table (current priors)</h2>
    <table>
      <thead>
        <tr><th>profile</th><th>tokens (k)</th><th>time</th><th>burn</th><th>conf</th><th>n</th><th>last</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.profile" :class="{ seed: r.seed, low: !r.seed && r.conf < 0.4 }">
          <td class="prof">{{ r.profile }}<span v-if="r.seed" class="tag">seed</span></td>
          <td>{{ band(r.tok_lo, r.tok_hi) }}</td>
          <td>{{ timeBand(r.time_lo, r.time_hi) }}</td>
          <td>{{ band(r.burn_lo, r.burn_hi) }}</td>
          <td>{{ r.conf.toFixed(2) }}</td>
          <td>{{ r.n }}</td>
          <td class="v">{{ r.last_verdict }}</td>
        </tr>
      </tbody>
    </table>
    <p class="src">source: token-priors.md · {{ rows.length }} profiles · grey = seed (n=0), amber = low confidence</p>
  </section>
</template>

<style scoped>
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 500; }
.prof { font-weight: 600; }
.tag { font-size: 9px; background: var(--track); color: var(--muted); padding: 1px 5px; border-radius: 4px; margin-left: 6px; }
tr.seed { opacity: 0.55; }
tr.low td { background: rgba(251, 191, 36, 0.08); }
.v { color: var(--muted); }
.src { font-size: 10px; color: var(--muted); margin: 8px 0 0; }
</style>
