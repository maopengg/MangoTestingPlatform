import type {
  RunComparison, RunError, RunMetricPage, RunMetricPoint, RunNode, RunOverview, RunRequestSummary,
  RunStage, RunSummary, RunThreshold, RunValidityResult, SummaryKey, TimingBreakdown, TimingKey,
} from './types'

export const timingKeys: TimingKey[] = ['dns_ms', 'connect_ms', 'tls_ms', 'ttfb_ms', 'download_ms']
export function readRunRouteId(value: unknown): string | null {
  if (typeof value !== 'string' || !/^\d+$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? String(id) : null
}
export async function validateRunExport(blob: Blob, expectedId: string): Promise<void> {
  const report = runObject(JSON.parse(await blob.text()))
  const run = runObject(report.run)
  if (report.schema_version !== 1 || String(integer(run.id)) !== expectedId) throw new Error('Invalid run export')
}
export const summaryKeys: SummaryKey[] = [
  'request_count', 'failure_count', 'response_time_sum_ms', 'iteration_count', 'dropped_count', 'bytes_sent',
  'bytes_received', 'connection_count', 'connect_error_count', 'min_ms', 'max_ms', 'avg_ms', 'p50_ms',
  'p90_ms', 'p95_ms', 'p99_ms', 'rps', 'max_rps', 'actual_peak_rps', 'actual_peak_concurrency',
  'peak_generator_cpu_percent', 'peak_generator_memory_bytes', 'peak_event_loop_lag_ms',
]
export function runObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid run response')
  return value as Record<string, unknown>
}
export function runData(value: unknown): unknown {
  const response = runObject(value)
  if (response.code !== 200) throw new Error('Run request failed')
  return response.data
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid run text')
  return value
}
function optionalText(value: unknown): string | null { return value == null ? null : text(value) }
function number(value: unknown): number {
  if ((typeof value !== 'number' && typeof value !== 'string') || (typeof value === 'string' && !value.trim())) throw new Error('Invalid run number')
  const result = Number(value)
  if (!Number.isFinite(result)) throw new Error('Invalid run number')
  return result
}
function optionalNumber(value: unknown): number | null { return value == null ? null : number(value) }
function integer(value: unknown): number {
  const result = number(value)
  if (!Number.isSafeInteger(result) || result < 0) throw new Error('Invalid run ID or count')
  return result
}
function boolean(value: unknown): boolean {
  if (typeof value !== 'boolean') throw new Error('Invalid run boolean')
  return value
}
function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new Error('Invalid run rows')
  return value
}
function timing(value: unknown): TimingBreakdown {
  const row = runObject(value ?? {}), result: TimingBreakdown = {}
  for (const key of timingKeys) if (row[key] !== undefined) result[key] = optionalNumber(row[key])
  return result
}
function summary(value: unknown): RunSummary {
  const row = runObject(value ?? {}), result: RunSummary = {}
  for (const key of summaryKeys) if (row[key] !== undefined) result[key] = optionalNumber(row[key])
  if (row.timing_breakdown !== undefined) result.timing_breakdown = timing(row.timing_breakdown)
  return result
}
export function readRunOverview(value: unknown, expectedId: string): RunOverview {
  const row = runObject(runData(value)), id = integer(row.id)
  if (String(id) !== expectedId) throw new Error('Run identity mismatch')
  return {
    id, name: text(row.name), status: text(row.status), verdict: text(row.verdict),
    scenario_id: row.scenario_id == null ? null : integer(row.scenario_id), summary: summary(row.summary),
    test_env: optionalNumber(row.test_env), test_env_title: optionalText(row.test_env_title),
    engine: text(row.engine), engine_version: optionalText(row.engine_version),
    requested_node_count: optionalNumber(row.requested_node_count), actual_node_count: optionalNumber(row.actual_node_count),
    peak_target_users: optionalNumber(row.peak_target_users), started_at: optionalText(row.started_at),
    finished_at: optionalText(row.finished_at), error_code: optionalText(row.error_code), error_message: optionalText(row.error_message),
  }
}
export function readRunRequests(value: unknown): RunRequestSummary[] {
  return array(runData(value)).map(value => {
    const row = runObject(value)
    return {
      ...summary(row), id: integer(row.id), step_key: text(row.step_key), request_name: text(row.request_name),
      method: text(row.method), url_path: text(row.url_path), request_count: optionalNumber(row.request_count),
      failure_count: optionalNumber(row.failure_count), avg_ms: optionalNumber(row.avg_ms), p50_ms: optionalNumber(row.p50_ms),
      p95_ms: optionalNumber(row.p95_ms), p99_ms: optionalNumber(row.p99_ms), rps: optionalNumber(row.rps), max_rps: optionalNumber(row.max_rps),
    }
  })
}
export function readRunComparison(value: unknown): RunComparison {
  const row = runObject(runData(value))
  return {
    available: boolean(row.available), same_snapshot: row.same_snapshot == null ? null : boolean(row.same_snapshot),
    metrics: array(row.metrics).map(value => {
      const item = runObject(value)
      return { metric: text(item.metric), current: optionalNumber(item.current), baseline: optionalNumber(item.baseline), delta: optionalNumber(item.delta), delta_percent: optionalNumber(item.delta_percent) }
    }),
  }
}
export function readRunValidity(value: unknown): RunValidityResult[] {
  return array(runData(value)).map(value => {
    const row = runObject(value)
    return { gate_key: text(row.gate_key), name: text(row.name), status: text(row.status), actual_value: optionalNumber(row.actual_value), required_value: optionalNumber(row.required_value) }
  })
}
export function readRunThresholds(value: unknown): RunThreshold[] {
  return array(runData(value)).map(value => {
    const row = runObject(value)
    return { metric: text(row.metric), operator: text(row.operator), actual_value: optionalNumber(row.actual_value), threshold_value: optionalNumber(row.threshold_value), passed: boolean(row.passed) }
  })
}
export function readRunStages(value: unknown): RunStage[] {
  return array(runData(value)).map(value => {
    const row = runObject(value)
    return {
      stage_key: text(row.stage_key), stage_name: text(row.stage_name), duration_seconds: optionalNumber(row.duration_seconds),
      target_load: { users: optionalNumber(runObject(row.target_load ?? {}).users) },
      actual_load: { users: optionalNumber(runObject(row.actual_load ?? {}).users) },
      rps: optionalNumber(row.rps), p95_ms: optionalNumber(row.p95_ms), failure_count: optionalNumber(row.failure_count),
    }
  })
}
export function readRunNodes(value: unknown): RunNode[] {
  return array(runData(value)).map(value => {
    const row = runObject(value), capture = runObject(row.capture ?? {})
    return {
      id: integer(row.id), shard_index: integer(row.shard_index), executor_fingerprint: optionalText(row.executor_fingerprint),
      status: text(row.status), engine_version: optionalText(row.engine_version), last_metric_at: optionalText(row.last_metric_at),
      error_message: optionalText(row.error_message),
      capture: { status: optionalText(capture.status), message: optionalText(capture.message), bytes: optionalNumber(capture.bytes) },
    }
  })
}
export function readRunErrors(value: unknown): RunError[] {
  return array(runData(value)).map(value => {
    const row = runObject(value)
    return {
      id: integer(row.id), error_type: text(row.error_type), count: integer(row.count), node_count: integer(row.node_count),
      message_template: text(row.message_template), samples: array(row.samples ?? []).map(value => {
        const sample = runObject(value)
        return { response_status: optionalNumber(sample.response_status), response_excerpt: optionalText(sample.response_excerpt) }
      }),
    }
  })
}
export function readRunMetricPage(value: unknown, expectedId: string): RunMetricPage {
  const row = runObject(runData(value))
  if (String(integer(row.run_id)) !== expectedId) throw new Error('Metric run identity mismatch')
  return {
    cursor: text(row.cursor), has_more: boolean(row.has_more), run_status: text(row.run_status), verdict: text(row.verdict),
    points: array(row.points).map(value => {
      const item = runObject(value), generator = runObject(item.generator_metrics ?? {})
      const seconds = integer(item.window_seconds)
      if (!seconds) throw new Error('Invalid metric window')
      const result: RunMetricPoint = {
        node_id: integer(item.node_id), window_start: text(item.window_start), window_seconds: seconds,
        request_count: integer(item.request_count), failure_count: integer(item.failure_count),
        iteration_count: integer(item.iteration_count), dropped_count: integer(item.dropped_count),
        response_time_sum_ms: number(item.response_time_sum_ms), bytes_sent: integer(item.bytes_sent), bytes_received: integer(item.bytes_received),
        connection_count: integer(item.connection_count), connect_error_count: integer(item.connect_error_count),
        min_response_time_ms: optionalNumber(item.min_response_time_ms), max_response_time_ms: optionalNumber(item.max_response_time_ms),
        target_load: { users: optionalNumber(runObject(item.target_load ?? {}).users) },
        actual_load: { users: optionalNumber(runObject(item.actual_load ?? {}).users) },
        generator_metrics: { cpu_percent: optionalNumber(generator.cpu_percent), memory_bytes: optionalNumber(generator.memory_bytes), event_loop_lag_ms: optionalNumber(generator.event_loop_lag_ms) },
        timing_breakdown: timing(item.timing_breakdown),
      }
      return result
    }),
  }
}
