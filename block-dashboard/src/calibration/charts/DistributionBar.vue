<script setup lang="ts">
import { computed } from 'vue'
import { scaleLinear } from '../format'

const props = withDefaults(defineProps<{
  median: number
  iqrLo: number
  iqrHi: number
  min: number
  max: number
  markers?: { value: number; label: string; color?: string }[]
}>(), { markers: () => [] })

const W = 480, H = 60, PAD = 12
const dom = computed<[number, number]>(() => {
  const vals = [props.min, props.max, props.iqrLo, props.iqrHi, props.median,
    ...props.markers.map((m) => m.value)]
  return [Math.min(...vals), Math.max(...vals)]
})
const sx = computed(() => scaleLinear(dom.value, [PAD, W - PAD]))
const box = computed(() => ({ x: sx.value(props.iqrLo), w: sx.value(props.iqrHi) - sx.value(props.iqrLo) }))
const mtick = computed(() => sx.value(props.median))
</script>

<template>
  <svg :viewBox="`0 0 ${W} ${H}`" class="dist">
    <line :x1="sx(min)" :x2="sx(max)" :y1="H / 2" :y2="H / 2" class="whisker" />
    <line :x1="sx(min)" :x2="sx(min)" :y1="H / 2 - 6" :y2="H / 2 + 6" class="cap" />
    <line :x1="sx(max)" :x2="sx(max)" :y1="H / 2 - 6" :y2="H / 2 + 6" class="cap" />
    <rect :x="box.x" :y="H / 2 - 11" :width="box.w" height="22" class="iqr" rx="3" />
    <line :x1="mtick" :x2="mtick" :y1="H / 2 - 13" :y2="H / 2 + 13" class="median" />
    <g v-for="m in markers" :key="m.label">
      <line :x1="sx(m.value)" :x2="sx(m.value)" :y1="6" :y2="H - 6" :stroke="m.color || '#c084fc'" class="marker" />
      <text :x="sx(m.value)" :y="4" class="mlabel" :fill="m.color || '#c084fc'">{{ m.label }}</text>
    </g>
  </svg>
</template>

<style scoped>
.dist { width: 100%; height: auto; }
.whisker { stroke: var(--muted); stroke-width: 1.5; }
.cap { stroke: var(--muted); stroke-width: 1.5; }
.iqr { fill: rgba(96, 165, 250, 0.25); stroke: #60a5fa; }
.median { stroke: var(--text); stroke-width: 2; }
.marker { stroke-dasharray: 3 2; }
.mlabel { font-size: 9px; text-anchor: middle; }
</style>
