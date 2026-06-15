<script setup lang="ts">
import { computed } from 'vue'
import type { ScatterPoint } from '../types'
import { scaleLinear, niceTicks } from '../format'

const props = withDefaults(defineProps<{
  points: ScatterPoint[]
  width?: number
  height?: number
  diagonal?: boolean
  isolines?: number[]
  xLabel?: string
  yLabel?: string
}>(), { width: 320, height: 300, diagonal: false, isolines: () => [] })

const M = { l: 40, r: 12, t: 10, b: 26 }
const iw = computed(() => props.width - M.l - M.r)
const ih = computed(() => props.height - M.t - M.b)
const xs = computed(() => props.points.map((p) => p.x))
const ys = computed(() => props.points.map((p) => p.y))
const xMax = computed(() => Math.max(1, ...xs.value))
const yMax = computed(() => Math.max(1, ...ys.value))
const lim = computed(() => Math.max(xMax.value, yMax.value))
const sx = computed(() => scaleLinear([0, props.diagonal ? lim.value : xMax.value], [M.l, M.l + iw.value]))
const sy = computed(() => scaleLinear([0, props.diagonal ? lim.value : yMax.value], [M.t + ih.value, M.t]))

const dots = computed(() => props.points.map((p) => ({
  cx: sx.value(p.x), cy: sy.value(p.y), color: p.color, label: p.label,
})))
const diag = computed(() => ({
  x1: sx.value(0), y1: sy.value(0), x2: sx.value(lim.value), y2: sy.value(lim.value),
}))
const isos = computed(() => props.isolines.map((slope) => {
  const xr = xMax.value
  return { slope, x1: sx.value(0), y1: sy.value(0), x2: sx.value(xr), y2: sy.value(slope * xr) }
}))
const xTicks = computed(() => niceTicks(0, props.diagonal ? lim.value : xMax.value, 4).map((t) => ({ x: sx.value(t), label: String(Math.round(t)) })))
const yTicks = computed(() => niceTicks(0, props.diagonal ? lim.value : yMax.value, 4).map((t) => ({ y: sy.value(t), label: String(Math.round(t)) })))
</script>

<template>
  <svg :viewBox="`0 0 ${width} ${height}`" class="scatter">
    <line v-for="t in yTicks" :key="'g' + t.label" :x1="M.l" :x2="width - M.r" :y1="t.y" :y2="t.y" class="grid" />
    <line v-if="diagonal" :x1="diag.x1" :y1="diag.y1" :x2="diag.x2" :y2="diag.y2" class="diag" />
    <line v-for="iso in isos" :key="'iso' + iso.slope" :x1="iso.x1" :y1="iso.y1" :x2="iso.x2" :y2="iso.y2" class="iso" />
    <circle v-for="(d, i) in dots" :key="i" :cx="d.cx" :cy="d.cy" r="3.5" :fill="d.color" class="dot">
      <title v-if="d.label">{{ d.label }}</title>
    </circle>
    <text v-for="t in xTicks" :key="'x' + t.label" :x="t.x" :y="height - 8" class="xlabel">{{ t.label }}</text>
    <text v-for="t in yTicks" :key="'y' + t.label" :x="M.l - 5" :y="t.y + 3" class="ylabel">{{ t.label }}</text>
    <text v-if="xLabel" :x="M.l + iw / 2" :y="height + 0" class="axis">{{ xLabel }}</text>
    <text v-if="yLabel" :x="10" :y="M.t + ih / 2" class="axis" :transform="`rotate(-90 10 ${M.t + ih / 2})`">{{ yLabel }}</text>
  </svg>
</template>

<style scoped>
.scatter { width: 100%; height: auto; }
.grid { stroke: var(--border); opacity: 0.4; }
.diag { stroke: var(--muted); stroke-dasharray: 4 3; stroke-width: 1; }
.iso { stroke: var(--border); stroke-dasharray: 2 2; }
.dot { opacity: 0.85; }
.xlabel, .ylabel { fill: var(--muted); font-size: 9px; }
.xlabel { text-anchor: middle; }
.ylabel { text-anchor: end; }
.axis { fill: var(--muted); font-size: 10px; text-anchor: middle; }
</style>
