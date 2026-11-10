import type { MetricCounterKey, RunMetricPoint, RunMetricWindow, RunSummary, TimingBreakdown, TimingKey } from './types'
import { timingKeys } from './records'

const counters: MetricCounterKey[] = [
  'request_count', 'failure_count', 'iteration_count', 'dropped_count', 'response_time_sum_ms',
  'bytes_sent', 'bytes_received', 'connection_count', 'connect_error_count',
]
const maximum = (left: number | null, right: number | null) => left === null ? right : right === null ? left : Math.max(left, right)
const minimum = (left: number | null, right: number | null) => left === null ? right : right === null ? left : Math.min(left, right)
const sum = (left: number | null, right: number | null) => left === null && right === null ? null : (left ?? 0) + (right ?? 0)

function cloneWindow(point: RunMetricPoint): RunMetricWindow {
  return {
    ...point, target_load: { ...point.target_load }, actual_load: { ...point.actual_load },
    generator_metrics: { ...point.generator_metrics }, timing_breakdown: { ...point.timing_breakdown },
    _nodes: new Set([point.node_id]),
    _timingWeights: Object.fromEntries(timingKeys.filter(key => point.timing_breakdown[key] != null).map(key => [key, point.request_count])),
  }
}

export function mergeRunMetricPoints(existing: RunMetricWindow[], incoming: RunMetricPoint[], limit = 600): RunMetricWindow[] {
  const windows = new Map(existing.map(row => [row.window_start, {
    ...cloneWindow(row), _nodes: new Set(row._nodes), _timingWeights: { ...row._timingWeights },
  }]))
  for (const point of incoming) {
    const target = windows.get(point.window_start)
    if (!target) { windows.set(point.window_start, cloneWindow(point)); continue }
    if (target._nodes.has(point.node_id)) continue
    target._nodes.add(point.node_id)
    for (const key of counters) target[key] += point[key]
    target.min_response_time_ms = minimum(target.min_response_time_ms, point.min_response_time_ms)
    target.max_response_time_ms = maximum(target.max_response_time_ms, point.max_response_time_ms)
    target.actual_load.users = sum(target.actual_load.users, point.actual_load.users)
    target.target_load.users = sum(target.target_load.users, point.target_load.users)
    target.generator_metrics.cpu_percent = maximum(target.generator_metrics.cpu_percent, point.generator_metrics.cpu_percent)
    target.generator_metrics.memory_bytes = sum(target.generator_metrics.memory_bytes, point.generator_metrics.memory_bytes)
    target.generator_metrics.event_loop_lag_ms = maximum(target.generator_metrics.event_loop_lag_ms, point.generator_metrics.event_loop_lag_ms)
    for (const key of timingKeys) {
      const value = point.timing_breakdown[key]
      if (value == null || !point.request_count) continue
      // Missing timings from one node must not dilute timings collected by another node.
      const oldWeight = target._timingWeights[key] ?? 0, weight = oldWeight + point.request_count
      target.timing_breakdown[key] = ((target.timing_breakdown[key] ?? 0) * oldWeight + value * point.request_count) / weight
      target._timingWeights[key] = weight
    }
  }
  return [...windows.values()].sort((a, b) => a.window_start.localeCompare(b.window_start)).slice(-limit)
}

export function summarizeRunMetrics(points: RunMetricWindow[]): RunSummary {
  if (!points.length) return {}
  let count = 0, responseSum = 0, duration = 0
  const result: RunSummary = {}, timingSums: Partial<Record<TimingKey, number>> = {}, weights: Partial<Record<TimingKey, number>> = {}
  for (const point of points) {
    count += point.request_count; responseSum += point.response_time_sum_ms; duration += point.window_seconds
    for (const key of counters) result[key] = Number(result[key] ?? 0) + point[key]
    result.min_ms = minimum(typeof result.min_ms === 'number' ? result.min_ms : null, point.min_response_time_ms)
    result.max_ms = maximum(typeof result.max_ms === 'number' ? result.max_ms : null, point.max_response_time_ms)
    result.max_rps = Math.max(Number(result.max_rps ?? 0), point.request_count / point.window_seconds)
    if (point.actual_load.users !== null) result.actual_peak_concurrency = Math.max(Number(result.actual_peak_concurrency ?? 0), point.actual_load.users)
    for (const [field, value] of [
      ['peak_generator_cpu_percent', point.generator_metrics.cpu_percent],
      ['peak_generator_memory_bytes', point.generator_metrics.memory_bytes],
      ['peak_event_loop_lag_ms', point.generator_metrics.event_loop_lag_ms],
    ] as const) {
      if (value !== null) result[field] = Math.max(Number(result[field] ?? 0), value)
    }
    for (const key of timingKeys) {
      const value = point.timing_breakdown[key], weight = point._timingWeights[key] ?? 0
      if (value == null || !weight) continue
      timingSums[key] = (timingSums[key] ?? 0) + value * weight
      weights[key] = (weights[key] ?? 0) + weight
    }
  }
  const timing: TimingBreakdown = {}
  for (const key of timingKeys) if (weights[key]) timing[key] = (timingSums[key] ?? 0) / weights[key]!
  result.avg_ms = count ? responseSum / count : null
  result.rps = duration ? count / duration : null
  result.timing_breakdown = timing
  return result
}
