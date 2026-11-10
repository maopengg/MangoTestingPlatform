import { effectivenessObject } from './ai-summary'
import { effectivenessChartIndex, effectivenessText } from './overview'

export function chartPoint(value: unknown) {
  const row = effectivenessObject(value)
  if (!row) return null
  return {
    dataIndex: effectivenessChartIndex(row), name: effectivenessText(row.name),
    axisValueLabel: effectivenessText(row.axisValueLabel), seriesName: effectivenessText(row.seriesName),
    value: row.value, data: effectivenessObject(row.data),
  }
}
export function chartPoints(value: unknown) {
  return (Array.isArray(value) ? value : [value]).flatMap(item => { const point = chartPoint(item); return point ? [point] : [] })
}
export function chartHtml(value: unknown): string {
  const text = typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value)) ? String(value) : '-'
  const replacements: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
  return text.replace(/[&<>"']/g, character => replacements[character])
}

export function resolveChartOption(value: unknown, readToken: (key: string) => string): Record<string, unknown> {
  const ancestors = new WeakSet<object>()
  function resolve(value: unknown): unknown {
    if (typeof value === 'string') {
      const token = value.match(/^var\((--m-[^)]+)\)$/)?.[1]
      return token ? readToken(token).trim() || value : value
    }
    if (!value || typeof value !== 'object') return value
    if (ancestors.has(value)) throw new Error('循环图表配置')
    ancestors.add(value)
    try {
      return Array.isArray(value) ? value.map(resolve) : Object.fromEntries(Object.entries(value).map(([key, item]) => [key, resolve(item)]))
    } finally { ancestors.delete(value) }
  }
  if (!effectivenessObject(value)) throw new Error('无效图表配置')
  const result = effectivenessObject(resolve(value))
  if (!result) throw new Error('无效图表配置')
  return result
}
