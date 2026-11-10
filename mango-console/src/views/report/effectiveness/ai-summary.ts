import { aiInsightKeys, chartInsightKeys, componentInsightKeys } from './config'

export type InsightKey = typeof aiInsightKeys[number]
export type InsightMap = Partial<Record<InsightKey, string>>
export interface EffectivenessAiSummary {
  headline: string
  executive_summary: string
  quality_trend: { status: 'improving' | 'stable' | 'declining' | 'unknown'; label: string; analysis: string }
  benefits: Array<{ title: string; detail: string; evidence: string }>
  risks: Array<{ title: string; detail: string; severity: string }>
  recommendations: Array<{ title: string; detail: string; priority: string; target_type: string; target_value: string }>
  chart_insights: InsightMap
  component_insights: InsightMap
}
export interface EffectivenessAiState {
  available: boolean | null
  reason: string
  model: string
  generated_at: string
  summary: EffectivenessAiSummary | null
}
export const effectivenessObject = (value: unknown): Record<string, unknown> | null => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
const text = (value: unknown): string => typeof value === 'string' ? value.trim() : ''
const rows = (value: unknown): Record<string, unknown>[] => Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => effectivenessObject(item) !== null) : []
export const createEmptyAiState = (): EffectivenessAiState => ({ available: null, reason: '', model: '', generated_at: '', summary: null })
export function effectivenessPayload(response: unknown): Record<string, unknown> {
  const envelope = effectivenessObject(response), payload = effectivenessObject(envelope?.data)
  if (envelope?.code !== 200 || !payload) throw new Error('无效的质量效能响应')
  return payload
}
function insightMap(value: unknown, keys: readonly InsightKey[]): InsightMap {
  const source = effectivenessObject(value), result: InsightMap = {}
  for (const key of keys) { const value = text(source?.[key]); if (value) result[key] = value }
  return result
}
export function parseEffectivenessAiState(response: unknown): EffectivenessAiState {
  const payload = effectivenessPayload(response)
  if (typeof payload.available !== 'boolean') throw new Error('缺少 AI 可用状态')
  const state = { available: payload.available, reason: text(payload.reason), model: text(payload.model), generated_at: text(payload.generated_at), summary: null as EffectivenessAiSummary | null }
  if (!state.available) return state
  const summary = effectivenessObject(payload.summary)
  if (!summary || !text(summary.executive_summary)) throw new Error('AI 总结内容为空')
  const trend = effectivenessObject(summary.quality_trend), status = text(trend?.status)
  state.summary = {
    headline: text(summary.headline), executive_summary: text(summary.executive_summary),
    quality_trend: { status: status === 'improving' || status === 'stable' || status === 'declining' ? status : 'unknown', label: text(trend?.label), analysis: text(trend?.analysis) },
    benefits: rows(summary.benefits).map(item => ({ title: text(item.title), detail: text(item.detail), evidence: text(item.evidence) })).filter(item => item.title),
    risks: rows(summary.risks).map(item => ({ title: text(item.title), detail: text(item.detail), severity: text(item.severity) })).filter(item => item.title),
    recommendations: rows(summary.recommendations).map(item => ({ title: text(item.title), detail: text(item.detail), priority: text(item.priority), target_type: text(item.target_type), target_value: text(item.target_value) })).filter(item => item.title),
    chart_insights: insightMap(summary.chart_insights, chartInsightKeys), component_insights: insightMap(summary.component_insights, componentInsightKeys),
  }
  return state
}
export function missingAiInsightKeys(summary: EffectivenessAiSummary | null): InsightKey[] {
  return aiInsightKeys.filter(key => !(summary?.component_insights[key] || summary?.chart_insights[key]))
}
export function parseEffectivenessInsights(response: unknown): { available: boolean; insights: InsightMap } {
  const payload = effectivenessPayload(response)
  if (typeof payload.available !== 'boolean') throw new Error('缺少 AI 解读状态')
  return { available: payload.available, insights: payload.available ? insightMap(payload.insights, aiInsightKeys) : {} }
}
