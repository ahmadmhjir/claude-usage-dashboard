<script setup lang="ts">
import { computed } from 'vue'
import { clamp } from '../format'

const props = withDefaults(defineProps<{
  pct: number
  label: string
  caption?: string
  warn?: number
}>(), { warn: 80 })

const w = computed(() => clamp(props.pct, 0, 100))
const color = computed(() => (props.pct >= props.warn ? '#f87171' : props.pct >= props.warn * 0.75 ? '#fbbf24' : '#34d399'))
</script>

<template>
  <div class="gauge">
    <div class="row"><span class="label">{{ label }}</span><span class="val">{{ Math.round(pct) }}%</span></div>
    <div class="track"><div class="fill" :style="{ width: w + '%', background: color }" /></div>
    <div v-if="caption" class="cap">{{ caption }}</div>
  </div>
</template>

<style scoped>
.gauge { display: flex; flex-direction: column; gap: 4px; }
.row { display: flex; justify-content: space-between; font-size: 12px; }
.label { color: var(--muted); }
.val { color: var(--text); font-weight: 600; }
.track { height: 10px; background: var(--track); border-radius: 6px; overflow: hidden; }
.fill { height: 100%; border-radius: 6px; transition: width 0.2s; }
.cap { font-size: 10px; color: var(--muted); }
</style>
