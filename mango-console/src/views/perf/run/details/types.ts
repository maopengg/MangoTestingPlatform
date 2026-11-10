// ORM Decimal values can arrive as JSON strings; formatting must preserve null and zero.
export type RunNumber = number | string | null

export interface RunIdentity {
  userId: number
  roleId: number | null
  token: string
  environment: number | null
}
export interface RunContext {
  id: string
  epoch: number
  identity: RunIdentity
  isCurrent: () => boolean
}

export interface RunRequestSummary extends RunSummary {
  id: number
  step_key: string
  request_name: string
  method: string
  url_path: string
  request_count: RunNumber
  failure_count: RunNumber
  avg_ms: RunNumber
  p50_ms: RunNumber
  p95_ms: RunNumber
  p99_ms: RunNumber
  rps: RunNumber
  max_rps: RunNumber
}

export interface RunComparisonMetric {
  metric: string
  current: RunNumber
  baseline: RunNumber
  delta: RunNumber
  delta_percent: RunNumber
}

export interface RunValidityResult {
  gate_key: string
  name: string
  status: string
  actual_value: RunNumber
  required_value: RunNumber
}

export type RequestColumnKey = 'request' | 'error_rate' | 'rps' |
  'request_count' | 'failure_count' | 'avg_ms' | 'p50_ms' | 'p95_ms' | 'p99_ms'

export type TimingKey = 'dns_ms' | 'connect_ms' | 'tls_ms' | 'ttfb_ms' | 'download_ms'
export type TimingBreakdown = Partial<Record<TimingKey, number | null>>
export type SummaryKey = 'request_count' | 'failure_count' | 'response_time_sum_ms' | 'iteration_count' |
  'dropped_count' | 'bytes_sent' | 'bytes_received' | 'connection_count' | 'connect_error_count' |
  'min_ms' | 'max_ms' | 'avg_ms' | 'p50_ms' | 'p90_ms' | 'p95_ms' | 'p99_ms' | 'rps' | 'max_rps' |
  'actual_peak_rps' | 'actual_peak_concurrency' | 'peak_generator_cpu_percent' |
  'peak_generator_memory_bytes' | 'peak_event_loop_lag_ms'
export type RunSummary = Partial<Record<SummaryKey, RunNumber>> & { timing_breakdown?: TimingBreakdown }

export interface RunOverview {
  id: number
  name: string
  status: string
  verdict: string
  scenario_id: number | null
  summary: RunSummary
  test_env: number | null
  test_env_title: string | null
  engine: string
  engine_version: string | null
  requested_node_count: number | null
  actual_node_count: number | null
  peak_target_users: number | null
  started_at: string | null
  finished_at: string | null
  error_code: string | null
  error_message: string | null
}
export interface RunComparison {
  available: boolean
  same_snapshot: boolean | null
  metrics: RunComparisonMetric[]
}
export interface RunStage {
  stage_key: string
  stage_name: string
  duration_seconds: number | null
  target_load: { users: number | null }
  actual_load: { users: number | null }
  rps: number | null
  p95_ms: number | null
  failure_count: number | null
}
export interface RunNode {
  id: number
  shard_index: number
  executor_fingerprint: string | null
  status: string
  engine_version: string | null
  last_metric_at: string | null
  error_message: string | null
  capture: { status: string | null; message: string | null; bytes: number | null }
}
export interface RunThreshold {
  metric: string
  operator: string
  actual_value: number | null
  threshold_value: number | null
  passed: boolean
}
export interface RunError {
  id: number
  error_type: string
  count: number
  node_count: number
  message_template: string
  samples: Array<{ response_status: number | null; response_excerpt: string | null }>
}
export type MetricCounterKey = 'request_count' | 'failure_count' | 'iteration_count' | 'dropped_count' |
  'response_time_sum_ms' | 'bytes_sent' | 'bytes_received' | 'connection_count' | 'connect_error_count'
export type MetricCounters = Record<MetricCounterKey, number>
export interface RunMetricPoint extends MetricCounters {
  node_id: number
  window_start: string
  window_seconds: number
  min_response_time_ms: number | null
  max_response_time_ms: number | null
  actual_load: { users: number | null }
  target_load: { users: number | null }
  generator_metrics: { cpu_percent: number | null; memory_bytes: number | null; event_loop_lag_ms: number | null }
  timing_breakdown: TimingBreakdown
}
export interface RunMetricWindow extends RunMetricPoint {
  _nodes: Set<number>
  _timingWeights: Partial<Record<TimingKey, number>>
}
export interface RunMetricPage {
  cursor: string
  has_more: boolean
  run_status: string
  verdict: string
  points: RunMetricPoint[]
}
