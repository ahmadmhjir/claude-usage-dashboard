<script setup lang="ts">
import { computed } from 'vue'
import type { Series } from '../types'
import { scaleLinear, linePath, niceTicks } from '../format'

const props = withDefaults(defineProps<{
  series: Series[]
  width?: number
  height?: number
  yMin?: number
  yMax?: number
  yFmt?: (v: number) => string
}>(), { width: 520, height: 200 })

const M = { l: 38, r: 12, t: 10, b: 22 }
const iw = computed(() => props.width - M.l - M.r)
const ih = computed(() => props.height - M.t - M.b)

const allX = computed(() => props.series.flatMap((s) => s.points.map((p) => p.x)))
const allY = computed(() => props.series.flatMap((s) => s.points.map((p) => p.y)))
const xDom = computed<[number, number]>(() =>
  allX.value.length ? [Math.min(...allX.value), Math.max(...allX.value)] : [0, 1])
const yDom = computed<[number, number]>(() => {
  const lo = props.yMin ?? (allY.value.length ? Math.min(...allY.value) : 0)
  const hi = props.yMax ?? (allY.value.length ? Math.max(...allY.value) : 1)
  return [lo, hi === lo ? lo + 1 : hi]
})
const sx = computed(() => scaleLinear(xDom.value, [M.l, M.l + iw.value]))
const sy = computed(() => scaleLinear(yDom.value, [M.t + ih.value, M.t]))

const paths = computed(() => props.series.map((s) => ({
  color: s.color, name: s.name,
  d: linePath(s.points.map((p) => ({ x: sx.value(p.x), y: sy.value(p.y) }))),
  pts: s.points.map((p) => ({ cx: sx.value(p.x), cy: sy.value(p.y) })),
})))
const yTicks = computed(() => niceTicks(yDom.value[0], yDom.value[1], 4).map((t) => ({
  v: t, y: sy.value(t), label: props.yFmt ? props.yFmt(t) : String(t),
})))
const xTicks = computed(() => niceTicks(xDom.value[0], xDom.value[1], 5).map((t) => ({
  x: sx.value(t), label: String(Math.round(t)),
})))
</script>

<template>
  <svg :viewBox="`0 0 ${width} ${height}`" class="linechart">
    <line v-for="t in yTicks" :key="'g' + t.v" :x1="M.l" :x2="width - M.r" :y1="t.y" :y2="t.y" class="grid" />
    <text v-for="t in yTicks" :key="'yl' + t.v" :x="M.l - 5" :y="t.y + 3" class="ylabel">{{ t.label }}</text>
    <text v-for="(t, i) in xTicks" :key="'xl' + i" :x="t.x" :y="height - 6" class="xlabel">{{ t.label }}</text>
    <path v-for="p in paths" :key="p.name" :d="p.d" :stroke="p.color" class="line" />
    <g v-for="p in paths" :key="p.name + 'pts'">
      <circle v-for="(c, i) in p.pts" :key="i" :cx="c.cx" :cy="c.cy" r="2.5" :fill="p.color" />
    </g>
  </svg>
</template>

<style scoped>
.linechart { width: 100%; height: auto; }
.grid { stroke: var(--border); opacity: 0.5; }
.line { fill: none; stroke-width: 2; }
.ylabel { fill: var(--muted); font-size: 9px; text-anchor: end; }
.xlabel { fill: var(--muted); font-size: 9px; text-anchor: middle; }
</style>
