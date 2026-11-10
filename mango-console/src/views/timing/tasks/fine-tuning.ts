export interface TaskFineTuning {
  api_concurrency_limit: number | null
  case_people: number | string | null
  report_retention_policy: string
}
export interface FineTuningTask {
  id: number | string
  name: string
  task_group_name: string
  case_types: number[]
  owner_name: string
}
export interface FineTuningOption { key: number | string; title: string }

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid task fine tuning object')
  return value as Record<string, unknown>
}
function id(value: unknown): number | string {
  if (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) return value
  if (typeof value === 'string' && /^\d+$/.test(value)) return value
  throw Error('Invalid task fine tuning ID')
}
function text(value: unknown, fallback = ''): string {
  if (value == null || value === '') return fallback
  if (typeof value !== 'string') throw Error('Invalid task fine tuning text')
  return value
}
export function readFineTuning(value: unknown): TaskFineTuning {
  const record = object(value)
  const concurrency = record.api_concurrency_limit
  if (concurrency != null && (typeof concurrency !== 'number' || !Number.isFinite(concurrency))) throw Error('Invalid task API concurrency')
  const owner = record.case_people
  return {
    api_concurrency_limit: concurrency ?? null,
    case_people: owner == null ? null : id(typeof owner === 'object' ? object(owner).id : owner),
    report_retention_policy: text(record.report_retention_policy, 'all'),
  }
}
export function readFineTuningTask(value: unknown): FineTuningTask {
  const record = object(value), owner = record.case_people
  if (record.case_types != null && !Array.isArray(record.case_types)) throw Error('Invalid task case types')
  return { id: id(record.id), name: text(record.name), task_group_name: text(record.task_group_name),
    owner_name: typeof owner === 'object' && owner !== null ? text(object(owner).name) : '',
    case_types: (record.case_types ?? []).map((value: unknown) => {
      if (typeof value !== 'number' || !Number.isInteger(value) || value < 0) throw Error('Invalid task case type')
      return value
    }) }
}
export function validateFineTuning(form: TaskFineTuning, platformLimit: number, validateConcurrency = true): string {
  if (form.case_people === null || form.case_people === '') return '请选择负责人'
  if (validateConcurrency && form.api_concurrency_limit !== null && (!Number.isInteger(form.api_concurrency_limit) || form.api_concurrency_limit < 1 || form.api_concurrency_limit > platformLimit)) return `API 执行并发必须在 1 到 ${platformLimit} 之间`
  return ''
}
export function assertFineTuningSaved(value: unknown): void {
  if (object(value).code !== 200) throw Error('Task fine tuning save failed')
}
export function fineTuningPatch(original: TaskFineTuning, current: TaskFineTuning): Partial<TaskFineTuning> {
  const normalized = readFineTuning(current)
  const patch: Partial<TaskFineTuning> = {}
  if (normalized.api_concurrency_limit !== original.api_concurrency_limit) patch.api_concurrency_limit = normalized.api_concurrency_limit
  if (normalized.case_people !== original.case_people) patch.case_people = normalized.case_people
  if (normalized.report_retention_policy !== original.report_retention_policy) patch.report_retention_policy = normalized.report_retention_policy
  return patch
}
