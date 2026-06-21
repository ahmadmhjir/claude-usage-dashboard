import { ref, computed } from 'vue'
import type { CalibrationData } from './types'

const EMPTY: CalibrationData = {
  passes: [], turns: [], priors: [], anchors: [], blocks: [],
  derived: {
    rolling_mape: [], on_budget_share: [], convergence_score: 0,
    burn_median: 0, burn_iqr: [0, 0], gen_rate_p90: 0,
    counts: { passes: 0, turns: 0, unreadable: 0, outliers: 0 },
    live_pct: 0, week_pct: 0,
  },
  generated_at: '',
}

export function useCalibration() {
  const data = ref<CalibrationData>(EMPTY)
  const sourceLabel = ref('')
  const error = ref<string | null>(null)

  async function loadUrl(url: string, label: string): Promise<boolean> {
    try {
      const res = await fetch(url)
      if (!res.ok) return false
      const json = (await res.json()) as CalibrationData
      if (!json || !Array.isArray(json.passes)) return false
      data.value = json
      sourceLabel.value = label
      error.value = null
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    }
  }

  async function load() {
    const base = import.meta.env.BASE_URL
    const real = await loadUrl(base + 'calibration.json', 'calibration.json')
    if (!real) await loadUrl(base + 'demo_calibration.json', 'demo data')
  }

  const hasData = computed(() => data.value.passes.length > 0 || data.value.turns.length > 0)
  return { data, sourceLabel, error, hasData, load }
}
