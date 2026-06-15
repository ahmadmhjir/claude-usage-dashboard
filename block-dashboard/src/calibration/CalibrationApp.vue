<script setup lang="ts">
import { onMounted } from 'vue'
import { useCalibration } from './useCalibration'
import ConvergencePanel from './panels/ConvergencePanel.vue'
import CalibrationScatterPanel from './panels/CalibrationScatterPanel.vue'
import BeliefTablePanel from './panels/BeliefTablePanel.vue'
import BurnPanel from './panels/BurnPanel.vue'
import LimitPanel from './panels/LimitPanel.vue'
import FeedPanel from './panels/FeedPanel.vue'

const { data, sourceLabel, hasData, load } = useCalibration()
onMounted(load)
</script>

<template>
  <div class="cal">
    <header class="chead">
      <div>
        <h1>Calibration Dashboard</h1>
        <p class="sub">Is the calibration loop actually learning? Convergence first; the rest is the proof.</p>
      </div>
      <span v-if="sourceLabel" class="source">source: {{ sourceLabel }}</span>
    </header>

    <template v-if="hasData">
      <ConvergencePanel :data="data" />
      <div class="grid">
        <CalibrationScatterPanel :data="data" />
        <BeliefTablePanel :data="data" />
        <BurnPanel :data="data" />
        <LimitPanel :data="data" />
      </div>
      <FeedPanel :data="data" />
    </template>
    <section v-else class="empty">
      <h2>No calibration data</h2>
      <p>Run <code>python aggregate.py --out public/calibration.json</code> (uses canonical loop sources), or rely on the bundled demo.</p>
    </section>
  </div>
</template>

<style scoped>
.cal { display: flex; flex-direction: column; gap: 18px; }
.chead { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; }
h1 { margin: 0; font-size: 22px; }
.sub { margin: 6px 0 0; color: var(--muted); max-width: 560px; }
.source { font-size: 12px; color: var(--muted); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.empty { background: var(--panel); border: 1px dashed var(--border); border-radius: 12px; padding: 40px; text-align: center; }
:deep(.panel) { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
:deep(.panel h2) { font-size: 15px; margin: 0 0 10px; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
</style>
