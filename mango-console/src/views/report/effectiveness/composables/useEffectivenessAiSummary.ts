
import { reportLoadError } from '@/utils/load-error'
import { reactive, ref, watch, onBeforeUnmount, onDeactivated } from 'vue'
import { postAutomationEffectivenessAiSummary, type EffectivenessAiContext } from '@/api/system/automation-effectiveness'
import { createEmptyAiState, effectivenessObject, missingAiInsightKeys, parseEffectivenessAiState, parseEffectivenessInsights, type EffectivenessAiState, type InsightMap } from '../ai-summary'

interface AiSnapshot { overview: Record<string, unknown>; context: EffectivenessAiContext }
interface Options {
  scopeKey: () => number
  available: () => boolean
  snapshot: () => AiSnapshot | null
}
export function useEffectivenessAiSummary(options: Options) {
  const state: EffectivenessAiState = reactive(createEmptyAiState())
  const insightState: { available: boolean | null; insights: InsightMap } = reactive({ available: null, insights: {} })
  const loading = ref(false), error = ref(''), insightError = ref('')
  let version = 0, disposed = false
  let pending: { version: number; promise: Promise<void> } | null = null
  function invalidate() {
    version++
    loading.value = false
    error.value = ''; insightError.value = ''
    Object.assign(state, createEmptyAiState())
    Object.assign(insightState, { available: null, insights: {} })
  }
  function load(force = false): Promise<void> {
    if (disposed || !options.available()) return Promise.resolve()
    if (pending?.version === version) return pending.promise
    const snapshot = options.snapshot()
    if (!snapshot) return Promise.resolve()
    let overview: Record<string, unknown> | null
    try { overview = effectivenessObject(JSON.parse(JSON.stringify(snapshot.overview))) }
    catch (loadFailure0) { (reportLoadError(loadFailure0, "加载失败，请重试", false), error.value = '统计快照无法读取，请重新查询后重试'); return Promise.resolve() }
    if (!overview) { error.value = '统计快照无法读取，请重新查询后重试'; return Promise.resolve() }
    const requestVersion = version, scope = options.scopeKey()
    const current = () => !disposed && options.available() && requestVersion === version && scope === options.scopeKey()
    const context = { ...snapshot.context }
    const payload = { overview, context, force }
    loading.value = true; error.value = ''; insightError.value = ''
    Object.assign(state, createEmptyAiState())
    Object.assign(insightState, { available: null, insights: {} })
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const response: unknown = await postAutomationEffectivenessAiSummary(payload)
        if (!current()) return
        Object.assign(state, parseEffectivenessAiState(response))
        const missing = state.available ? missingAiInsightKeys(state.summary) : []
        if (!missing.length) { insightState.available = state.available; return }
        try {
          const response: unknown = await postAutomationEffectivenessAiSummary({ ...payload, mode: 'insights', insight_keys: missing })
          if (current()) Object.assign(insightState, parseEffectivenessInsights(response))
        } catch (loadFailure0) {
          if (current()) { insightState.available = false; (reportLoadError(loadFailure0, "部分图表解读加载失败，可重新总结后重试", false), insightError.value = '部分图表解读加载失败，可重新总结后重试') }
        }
      } catch (loadFailure1) {
        if (current()) { (reportLoadError(loadFailure1, "AI 总结加载失败，请重试", false), error.value = 'AI 总结加载失败，请重试'); Object.assign(state, createEmptyAiState()) }
      } finally {
        if (current()) loading.value = false
        if (pending?.promise === promise) pending = null
      }
    })
    pending = { version, promise }
    return promise
  }
  watch(options.scopeKey, invalidate, { flush: 'sync' })
  onDeactivated(invalidate)
  onBeforeUnmount(() => { disposed = true; invalidate() })
  return { state, insightState, loading, error, insightError, load, invalidate }
}
