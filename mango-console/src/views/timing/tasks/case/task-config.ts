export type TaskCaseId = number | string

interface TaskCaseRelation {
  id: TaskCaseId
  name: string
}

export interface TaskCaseConfig {
  id: TaskCaseId
  name: string
  execution_scope: string
  case_types: number[]
  execution_scenes: string[]
  project_product: (TaskCaseRelation & { project: TaskCaseRelation | null }) | null
  module: (TaskCaseRelation & { full_path: string }) | null
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid task configuration')
  return value as Record<string, unknown>
}

function id(value: unknown): TaskCaseId {
  if (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) return value
  if (typeof value === 'string' && /^\d+$/.test(value)) return value
  throw Error('Invalid task configuration ID')
}

function text(value: unknown, optional = false): string {
  if (optional && value == null) return ''
  if (typeof value !== 'string') throw Error('Invalid task configuration text')
  return value
}

function relation(value: unknown): TaskCaseRelation | null {
  if (value == null) return null
  if (typeof value !== 'object') return { id: id(value), name: '' }
  const row = object(value)
  return { id: id(row.id), name: text(row.name, true) }
}

export function parseTaskCaseConfig(response: unknown, taskId: TaskCaseId): TaskCaseConfig | null {
  const envelope = object(response)
  if (envelope.code !== 200) throw Error('Task configuration request failed')
  const data = envelope.data
  const records = Array.isArray(data) ? data : object(data).items
  if (Array.isArray(records) && records.length === 0) return null
  const row = object(Array.isArray(records) ? records[0] : data)
  const taskKey = id(row.id)
  if (String(taskKey) !== String(taskId)) throw Error('Task configuration ID mismatch')
  if (!Array.isArray(row.case_types) || !Array.isArray(row.execution_scenes)) throw Error('Invalid task configuration filters')
  const caseTypes = row.case_types.map(value => {
    if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw Error('Invalid task case type')
    return value
  })
  const product = relation(row.project_product), module = relation(row.module)
  return {
    id: taskKey,
    name: text(row.name),
    execution_scope: text(row.execution_scope),
    case_types: caseTypes,
    execution_scenes: row.execution_scenes.map(value => text(value)),
    project_product: product ? { ...product, project: typeof row.project_product === 'object' ? relation(object(row.project_product).project) : null } : null,
    module: module ? { ...module, full_path: typeof row.module === 'object' ? text(object(row.module).full_path, true) : '' } : null,
  }
}
