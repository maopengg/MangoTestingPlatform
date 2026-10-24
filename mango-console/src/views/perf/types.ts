export interface PerfScenarioRecord {
  id: number
  name: string
  project_product: number | { id: number; name: string }
  module: number | { id: number; name: string; full_path?: string }
  module_full_path?: string
  engine: 'k6'
  load_type: 'concurrency' | 'arrival_rate' | 'iteration_rate'
  duration_seconds: number
  target_users?: number
  target_rate?: number
  rate_time_unit?: 'second' | 'minute'
  default_executor_count: number
  status: number
  step_count?: number
  update_time: string
}

export interface PerfRunRecord {
  id: number
  name: string
  status: string
  verdict: string
  engine: string
  requested_node_count: number
  actual_node_count: number
  peak_target_users: number
  duration_seconds: number
  create_time: string
  started_at?: string
  finished_at?: string
}

export const activeRunStatuses = new Set([
  'created',
  'prechecking',
  'waiting_executor',
  'queued',
  'starting',
  'running',
  'stopping',
  'aggregating',
])

export const runStatusTitle: Record<string, string> = {
  created: '已创建',
  prechecking: '预检中',
  waiting_executor: '等待执行器',
  queued: '排队中',
  starting: '启动中',
  running: '运行中',
  stopping: '停止中',
  aggregating: '汇总中',
  completed: '已完成',
  partial: '部分完成',
  failed: '执行失败',
  stopped: '已停止',
  cancelled: '已取消',
  timeout: '已超时',
}

export const verdictTitle: Record<string, string> = {
  not_evaluated: '未判定',
  passed: '通过',
  failed: '不通过',
  invalid: '结果无效',
}

export function runStatusColor(value: string) {
  if (value === 'running') return 'blue'
  if (value === 'completed') return 'green'
  if (['failed', 'timeout'].includes(value)) return 'red'
  if (['stopping', 'partial'].includes(value)) return 'orange'
  return 'gray'
}

export function runVerdictColor(value: string) {
  if (value === 'passed') return 'green'
  if (value === 'failed') return 'red'
  if (value === 'invalid') return 'orange'
  return 'gray'
}
