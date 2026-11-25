export interface ExecutionHistoryItem {
  id: number | string
  title: string
  statusText?: string
  statusColor?: string
  time?: string
  actor?: string
  latest?: boolean
  sourceText?: string
  sourceColor?: string
  context?: string
}

export type HistoryId = number | string

export interface HistoryRecord {
  id: HistoryId
  label: string
  status: number | null
  status_name: string
  status_text: string
  update_time: string
  create_time: string
  trigger_time: string
  trigger_user_name: string
  is_case_latest: boolean | null
  is_latest: boolean | null
  test_suite_id: HistoryId | null
  test_suite: HistoryId | null
  source_type: string
  source_type_name: string
  target_type: string
  target_id: HistoryId | null
  revision_id: HistoryId | null | undefined
  release_id: HistoryId | null
  test_env: HistoryId | null
  test_env_name: string
  trace_id: string | null
}

export interface HistoryDetail extends HistoryRecord {
  error_message: string
  trace_id: string | null
  result_cleaned: boolean
  result_data: unknown
  source_snapshot: unknown
}

export interface HistoryScenario {
  key: string
  label: string
  parameterId: HistoryId | null
  status: number | null
  retryCount: number
  // 场景状态取自有限字段；可扩展的完整证据仅供只读报告消费。
  result: Record<string, unknown>
}

export interface HistoryStep {
  key: string
  label: string
  status: number | null
  total: number
  passed: number
  scenarios: HistoryScenario[]
}

export function historyObject(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
}

export function historyText(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

export function historyId(value: unknown): HistoryId | null {
  return (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) || (typeof value === 'string' && /^\d+$/.test(value)) ? value : null
}

function historyStatus(value: unknown): number | null {
  return typeof value === 'number' && Number.isInteger(value) ? value : null
}

function record(value: unknown): HistoryRecord {
  const row = historyObject(value), id = historyId(row?.id)
  if (!row || id === null) throw new Error('Invalid history record')
  return {
    id, label: historyText(row.label), status: historyStatus(row.status),
    status_name: historyText(row.status_name), status_text: historyText(row.status_text),
    update_time: historyText(row.update_time), create_time: historyText(row.create_time),
    trigger_time: historyText(row.trigger_time), trigger_user_name: historyText(row.trigger_user_name),
    is_case_latest: typeof row.is_case_latest === 'boolean' ? row.is_case_latest : null,
    is_latest: typeof row.is_latest === 'boolean' ? row.is_latest : null,
    test_suite_id: historyId(row.test_suite_id), test_suite: historyId(row.test_suite),
    source_type: historyText(row.source_type), source_type_name: historyText(row.source_type_name),
    target_type: historyText(row.target_type), target_id: historyId(row.target_id),
    revision_id: row.revision_id === undefined ? undefined : historyId(row.revision_id),
    release_id: historyId(row.release_id), test_env: historyId(row.test_env),
    test_env_name: historyText(row.test_env_name), trace_id: historyText(row.trace_id) || null,
  }
}

export function historyVersionText(item: HistoryRecord): string {
  if (item.target_type !== 'api_case') return ''
  if (item.revision_id === undefined) return '版本未记录'
  if (item.revision_id === null) return '编辑态'
  return `修订 #${item.revision_id}${item.release_id !== null ? ` · 发布 #${item.release_id}` : ''}`
}

export function historyEnvironmentText(item: HistoryRecord): string {
  return item.test_env_name && item.test_env_name !== '-'
    ? item.test_env_name : item.test_env !== null ? `环境 #${item.test_env}` : '环境未记录'
}

export function historyResponse(value: unknown): unknown {
  const response = historyObject(value)
  if (!response || response.code !== 200) throw new Error('Invalid history response')
  return response.data
}

export function historyRecords(value: unknown, target?: { target_type: string; target_id?: HistoryId }): HistoryRecord[] {
  const rows = historyResponse(value)
  if (!Array.isArray(rows)) throw new Error('Invalid history list')
  const seen = new Set<string>()
  return rows.map(value => {
    const row = record(value), key = String(row.id)
    if (seen.has(key) || (target && (row.target_type !== target.target_type || (target.target_id !== undefined && String(row.target_id) !== String(target.target_id))))) throw new Error('Invalid history scope')
    seen.add(key)
    return row
  })
}

export function historyDetail(value: unknown, id: HistoryId): HistoryDetail {
  const payload = historyObject(historyResponse(value)), summary = record(payload)
  if (!payload || String(summary.id) !== String(id)) throw new Error('Invalid history detail scope')
  return {
    ...summary,
    error_message: historyText(payload.error_message), trace_id: historyText(payload.trace_id) || null,
    result_cleaned: payload.result_cleaned === true,
    result_data: payload.result_data, source_snapshot: payload.source_snapshot,
  }
}

export function reportHistoryDetail(value: unknown, option: HistoryRecord, preferredParameterId?: HistoryId): HistoryDetail {
  const payload = historyObject(historyResponse(value))
  if (!payload) throw new Error('Invalid report history result')
  const children = Array.isArray(payload.children) ? payload.children.map(historyObject).filter((item): item is Record<string, unknown> => item !== null) : []
  const result = children.find(item => preferredParameterId !== undefined && String(item.parameter_id) === String(preferredParameterId)) || children[0] || payload
  return {
    ...option, status: historyStatus(result.status) ?? option.status,
    status_name: option.status_text || option.status_name,
    error_message: historyText(result.error_message) || historyText(payload.error_message),
    result_data: result, test_suite: option.test_suite_id,
    trace_id: null, result_cleaned: false, source_snapshot: null,
  }
}

function aggregateStatus(items: HistoryScenario[]): number | null {
  if (items.some(item => item.status === 0)) return 0
  if (items.some(item => item.status === 3)) return 3
  if (items.some(item => item.status === 4)) return 4
  if (items.length && items.every(item => item.status === 1)) return 1
  return items.some(item => item.status === null) ? null : 2
}

export function historySteps(raw: unknown): HistoryStep[] {
  if (!Array.isArray(raw)) return []
  const steps = new Map<string, { key: string; label: string; scenarios: Map<string, { key: string; label: string; results: Record<string, unknown>[] }> }>()
  raw.forEach((value, index) => {
    const result = historyObject(value)
    if (!result) return
    const stepId = historyId(result.id) ?? historyId(result.api_info_id)
    const stepKey = String(stepId ?? `step-${index}`)
    let step = steps.get(stepKey)
    if (!step) {
      step = { key: stepKey, label: historyText(result.api_info_name) || `步骤 ${stepId ?? index + 1}`, scenarios: new Map() }
      steps.set(stepKey, step)
    }
    const scenarioKey = String(historyId(result.parameter_id) ?? (historyText(result.name) || `scenario-${index}`))
    let scenario = step.scenarios.get(scenarioKey)
    if (!scenario) {
      scenario = { key: `${stepKey}:${scenarioKey}`, label: historyText(result.name) || historyText(result.api_info_name) || '默认场景', results: [] }
      step.scenarios.set(scenarioKey, scenario)
    }
    scenario.results.push(result)
  })
  return Array.from(steps.values()).map(step => {
    const scenarios = Array.from(step.scenarios.values()).map(scenario => {
      const retry = (value: unknown) => typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : -1
      const result = scenario.results.reduce((latest, item) => retry(item.retry_index) >= retry(latest.retry_index) ? item : latest)
      return {
        key: scenario.key, label: scenario.label, parameterId: historyId(result.parameter_id),
        status: result.status === undefined ? 2 : historyStatus(result.status),
        retryCount: Math.max(scenario.results.length - 1, retry(result.retry_index)), result,
      }
    })
    return { key: step.key, label: step.label, status: aggregateStatus(scenarios), total: scenarios.length, passed: scenarios.filter(item => item.status === 1).length, scenarios }
  })
}
