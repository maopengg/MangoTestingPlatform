import type { RunComparisonMetric, RunRequestSummary, RunValidityResult } from './types'

export function finiteRunNumber(value: unknown): number | null {
  if (typeof value !== 'number' && typeof value !== 'string') return null
  if (typeof value === 'string' && !value.trim()) return null
  const result = Number(value)
  return Number.isFinite(result) ? result : null
}

export function formatRunNumber(value: unknown, digits = 0): string {
  const result = finiteRunNumber(value)
  return result === null ? '-' : new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(result)
}

export function requestErrorRate(record: RunRequestSummary): string {
  const total = finiteRunNumber(record.request_count), failures = finiteRunNumber(record.failure_count)
  if (total === null || failures === null) return '-'
  return `${(total ? failures / total * 100 : 0).toFixed(2)}%`
}

export function comparisonValue(metric: string, input: unknown): string {
  const result = formatRunNumber(input, metric.endsWith('_ms') || metric === 'rps' ? 2 : 0)
  return result === '-' ? result : metric.endsWith('_ms') ? `${result} ms` : result
}

export function comparisonTone(item: RunComparisonMetric): string {
  const delta = finiteRunNumber(item.delta)
  if (delta === null || delta === 0) return ''
  const lowerIsBetter = ['failure_count', 'avg_ms', 'p95_ms', 'p99_ms'].includes(item.metric)
  return (lowerIsBetter ? delta < 0 : delta > 0) ? 'mango-perf-success-text' : 'mango-perf-danger-text'
}

export function comparisonDelta(item: RunComparisonMetric): string {
  const delta = finiteRunNumber(item.delta)
  return delta === null ? '-' : `${delta > 0 ? '+' : ''}${comparisonValue(item.metric, delta)}`
}

export function comparisonPercent(input: unknown): string {
  const value = finiteRunNumber(input)
  return value === null ? '-' : `${value.toFixed(2)}%`
}

function gateValue(key: string, input: unknown): string {
  const value = finiteRunNumber(input)
  if (value === null) return '-'
  if (key === 'generator_cpu') return `${formatRunNumber(value, 2)}%`
  if (key === 'clock_offset') return `${formatRunNumber(value)} ms`
  if (['metric_coverage', 'dropped_iterations'].includes(key)) return `${(value * 100).toFixed(2)}%`
  return formatRunNumber(value, 3)
}

export const validityActual = (item: RunValidityResult) => gateValue(item.gate_key, item.actual_value)
export function validityRequired(item: RunValidityResult): string {
  const value = gateValue(item.gate_key, item.required_value)
  if (value === '-') return value
  if (item.gate_key === 'metric_coverage') return `≥ ${value}`
  if (['generator_cpu', 'clock_offset', 'dropped_iterations'].includes(item.gate_key)) return `≤ ${value}`
  return value
}
