export type TaskEditorId = number | string
export interface TaskEditorOption { key: TaskEditorId; title: string; disabled?: boolean }
export interface TaskEditorDraft {
  name: string
  project_product: TaskEditorId | null
  module: TaskEditorId | null
  timing_strategies: TaskEditorId[]
  test_envs: number[]
  case_types: number[]
  execution_scenes: string[]
  execution_scope: string
  case_people: TaskEditorId | null
  api_concurrency_limit: number | null
  notice_group: TaskEditorId | null
  report_retention_policy: string
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid task data')
  return value as Record<string, unknown>
}
export function taskEditorId(value: unknown): TaskEditorId | null {
  if (Array.isArray(value)) return taskEditorId(value[value.length - 1])
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'object') return taskEditorId(object(value).id)
  if (typeof value === 'string') return value
  if (typeof value === 'number' && Number.isSafeInteger(value)) return value
  throw Error('Invalid task ID')
}
function ids(value: unknown): TaskEditorId[] {
  if (value === null || value === undefined) return []
  if (!Array.isArray(value)) throw Error('Invalid task selection')
  return value.map(taskEditorId).filter((id): id is TaskEditorId => id !== null)
}
function numbers(value: unknown): number[] {
  return ids(value).map(id => {
    const number = Number(id)
    if (!Number.isSafeInteger(number)) throw Error('Invalid task enum')
    return number
  })
}
export function createTaskEditorDraft(): TaskEditorDraft {
  return { name: '', project_product: null, module: null, timing_strategies: [], test_envs: [], case_types: [],
    execution_scenes: [], execution_scope: 'manual', case_people: null, api_concurrency_limit: null,
    notice_group: null, report_retention_policy: 'all' }
}
export function readTaskEditorDraft(value: unknown): TaskEditorDraft {
  const row = object(value)
  const concurrency = row.api_concurrency_limit
  if (concurrency != null && (typeof concurrency !== 'number' || !Number.isFinite(concurrency))) throw Error('Invalid concurrency')
  return {
    name: typeof row.name === 'string' ? row.name : '', project_product: taskEditorId(row.project_product), module: taskEditorId(row.module),
    timing_strategies: ids(row.timing_strategies), test_envs: numbers(row.test_envs), case_types: numbers(row.case_types),
    execution_scenes: ids(row.execution_scenes).map(String), execution_scope: typeof row.execution_scope === 'string' ? row.execution_scope : '',
    case_people: taskEditorId(row.case_people), api_concurrency_limit: concurrency == null ? null : concurrency,
    notice_group: taskEditorId(row.notice_group), report_retention_policy: typeof row.report_retention_policy === 'string' ? row.report_retention_policy : 'all',
  }
}
export function taskEditorPayload(form: TaskEditorDraft, id: TaskEditorId | null) {
  const draft = readTaskEditorDraft(form)
  return id === null ? { ...draft, status: 0, is_notice: 0 } : { ...draft, id }
}
export function validateTaskEditor(form: TaskEditorDraft, platformLimit: number): string {
  if (form.project_product === null) return '请选择项目名称'
  if (!form.name) return '请输入任务名称'
  if (!form.timing_strategies.length) return '请选择定时器策略'
  if (!form.test_envs.length) return '请选择执行环境'
  if (!form.execution_scenes.length) return '请选择执行场景'
  if (!form.execution_scope || form.execution_scope === 'unclassified') return '请选择执行范围'
  if (form.case_people === null) return '请选择定时任务负责人'
  if (form.execution_scope === 'module' && form.module === null) return '执行范围选择“模块全量”时必须选择模块'
  if (form.execution_scope === 'full_product' && form.module !== null) return '执行范围选择“产品全量”时不能同时选择模块'
  if (form.api_concurrency_limit !== null && (!Number.isInteger(form.api_concurrency_limit) || form.api_concurrency_limit < 1 || form.api_concurrency_limit > platformLimit)) return `API 执行并发必须在 1 到 ${platformLimit} 之间`
  return ''
}
export function taskEditorResponse(value: unknown): unknown {
  const response = object(value)
  if (response.code !== 200) throw Error('Task request failed')
  return response.data
}
export function readTaskEditorOptions(value: unknown): TaskEditorOption[] {
  if (!Array.isArray(value)) throw Error('Invalid task options')
  return value.map(entry => {
    const row = object(entry), key = taskEditorId(row.key ?? row.value ?? row.id)
    const title = row.title ?? row.label ?? row.name
    if (key === null || typeof title !== 'string') throw Error('Invalid task option')
    return { key, title, ...(typeof row.disabled === 'boolean' ? { disabled: row.disabled } : {}) }
  })
}
export function readTaskEditorCapacity(value: unknown): number {
  const limit = object(value).api_platform_limit
  if (typeof limit !== 'number' || !Number.isInteger(limit) || limit < 1) throw Error('Invalid task capacity')
  return limit
}
export function taskEditorSelectedOptions(options: TaskEditorOption[], selected: TaskEditorId[], fallback: TaskEditorOption[] = []) {
  const result = options.map(option => ({ ...option, key: selected.find(id => String(id) === String(option.key)) ?? option.key }))
  for (const id of selected) if (!result.some(option => String(option.key) === String(id))) {
    result.push({ key: id, title: fallback.find(option => String(option.key) === String(id))?.title || `ID ${id}` })
  }
  return result
}
export function taskEditorRecordOptions(value: unknown, field: 'case_people' | 'notice_group' | 'timing_strategies'): TaskEditorOption[] {
  const selection = object(value)[field]
  const values = Array.isArray(selection) ? selection : [selection]
  return values.flatMap(entry => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) return []
    const row = object(entry), key = taskEditorId(row.id), title = row.name ?? row.title ?? row.label
    return key !== null && typeof title === 'string' ? [{ key, title }] : []
  })
}
const productionScenes = ['stability_monitoring', 'production_inspection', 'production_regression']
export function taskEditorScenes(options: TaskEditorOption[], form: Pick<TaskEditorDraft, 'test_envs' | 'execution_scope'>) {
  const eligible = options.filter(option => !['unclassified', 'effectiveness_test'].includes(String(option.key)))
  const envs = form.test_envs, productionOnly = envs.length > 0 && envs.every(env => env === 2)
  if (form.execution_scope === 'manual') return eligible.filter(option => option.key !== 'stability_monitoring' || productionOnly)
  if (!envs.length || (envs.includes(2) && envs.some(env => env !== 2))) return eligible
  return eligible.filter(option => envs.includes(2) ? productionScenes.includes(String(option.key)) : option.key !== 'stability_monitoring')
}
export function taskEditorScopes(options: TaskEditorOption[], form: Pick<TaskEditorDraft, 'test_envs' | 'execution_scenes'>) {
  const productionOnly = form.test_envs.length > 0 && form.test_envs.every(env => env === 2)
  const productionAllowed = form.execution_scenes.length > 0 && form.execution_scenes.every(scene => productionScenes.includes(scene))
  return options.filter(option => ['manual', 'full_product', 'module'].includes(String(option.key))).map(option => ({ ...option,
    title: option.key === 'module' ? `${option.title}（请前往任务组创建）` : option.title,
    disabled: option.key === 'module' || (productionOnly && option.key !== 'manual' && !productionAllowed),
  }))
}
