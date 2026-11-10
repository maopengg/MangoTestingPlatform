import type { ExecutorCandidate, ExecutorPreflight, ScenarioExecutionDraft } from './types'

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('执行响应格式不正确')
  return value as Record<string, unknown>
}

function responseData(value: unknown): Record<string, unknown> {
  const response = object(value)
  if (response.code !== 200) throw new Error('执行请求未成功')
  return object(response.data)
}

function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('执行器信息格式不正确')
  return value
}

function number(value: unknown): number {
  const result = typeof value === 'number' ? value : typeof value === 'string' && value.trim() ? Number(value) : NaN
  if (!Number.isFinite(result) || result < 0) throw new Error('执行容量格式不正确')
  return result
}

function boolean(value: unknown): boolean {
  if (typeof value !== 'boolean') throw new Error('执行状态格式不正确')
  return value
}

function candidates(value: unknown): ExecutorCandidate[] {
  if (!Array.isArray(value)) throw new Error('执行器列表格式不正确')
  const result = value.map(item => {
    const row = object(item), fingerprint = text(row.fingerprint)
    if (!fingerprint.trim()) throw new Error('执行器标识为空')
    return { fingerprint, executor_name: text(row.executor_name), available: number(row.available), calibrated: boolean(row.calibrated) }
  })
  if (new Set(result.map(item => item.fingerprint)).size !== result.length) throw new Error('执行器标识重复')
  return result
}

export function readExecutorPreflight(value: unknown): ExecutorPreflight {
  const data = responseData(value)
  if (data.capacity_type !== 'vu' && data.capacity_type !== 'rps') throw new Error('容量类型不正确')
  const count = number(data.requested_node_count)
  if (!Number.isSafeInteger(count) || count < 1) throw new Error('执行器数量不正确')
  return {
    can_run: boolean(data.can_run), capacity_type: data.capacity_type,
    required_per_node: number(data.required_per_node), requested_node_count: count,
    candidates: candidates(data.candidates), selected: candidates(data.selected),
  }
}

export function readExecutionRunId(value: unknown): number {
  const id = number(responseData(value).run_id)
  if (!Number.isSafeInteger(id) || id < 1) throw new Error('运行 ID 不正确')
  return id
}

export function executionSelectionReady(
  draft: ScenarioExecutionDraft, preflight: ExecutorPreflight | null, count: number
): boolean {
  const ids = draft.selected_executor_fingerprints
  return !!preflight?.can_run && preflight.requested_node_count === count && ids.length === count &&
    new Set(ids).size === count && preflight.selected.length === count &&
    ids.every(id => preflight.selected.some(item => item.fingerprint === id && item.available >= preflight.required_per_node))
}

export function executionDraftError(draft: ScenarioExecutionDraft, count: number): string {
  if (typeof draft.test_env !== 'number' || !Number.isSafeInteger(draft.test_env) || draft.test_env < 0)
    return '请选择测试环境'
  if (!Number.isSafeInteger(count) || count < 1 || draft.selected_executor_fingerprints.length !== count ||
    new Set(draft.selected_executor_fingerprints).size !== count ||
    draft.selected_executor_fingerprints.some(id => typeof id !== 'string' || !id.trim()))
    return `必须选择 ${count} 个容量充足的执行器`
  if (draft.test_env === 2 && draft.production_load_confirmed !== true) return '请确认已获得生产环境发压授权'
  if (typeof draft.remark !== 'string' || draft.remark.length > 512) return '运行备注不能超过 512 字'
  if (typeof draft.capture_request !== 'boolean' || typeof draft.capture_response !== 'boolean') return '请求记录配置不正确'
  return ''
}

export function executionPayload(draft: ScenarioExecutionDraft) {
  return {
    test_env: draft.test_env,
    selected_executor_fingerprints: [...draft.selected_executor_fingerprints],
    remark: draft.remark, production_load_confirmed: draft.production_load_confirmed,
    capture_request: draft.capture_request, capture_response: draft.capture_response,
  }
}
