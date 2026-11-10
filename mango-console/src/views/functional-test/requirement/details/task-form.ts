import type { RequirementTaskForm, RequirementTaskRecord } from './types'

export const positiveTaskId = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value > 0

export function createTaskForm(source?: RequirementTaskForm): RequirementTaskForm {
  return {
    name: source?.name ?? '新建子任务',
    task_type: source?.task_type ?? 8,
    status: source?.status ?? 0,
    owner: source?.owner ?? null,
    planned_start_date: source?.planned_start_date ?? null,
    planned_end_date: source?.planned_end_date ?? null,
    estimated_person_days: source?.estimated_person_days ?? null,
    actual_person_days: source?.actual_person_days ?? null,
    self_test_status: source?.self_test_status ?? 0,
    sort_order: source?.sort_order ?? 0,
  }
}

export function parseRequirementTask(value: unknown, requirementId: number): RequirementTaskRecord {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('子任务格式错误')
  const row = value as Readonly<Record<string, unknown>>
  if (!positiveTaskId(row.id) || row.requirement_version !== requirementId)
    throw Error('子任务归属错误')
  const integer = (key: string) => {
    const item = row[key]
    if (typeof item !== 'number' || !Number.isSafeInteger(item)) throw Error('子任务枚举格式错误')
    return item
  }
  const date = (key: string) => {
    const item = row[key]
    if (item === null || item === undefined || item === '') return null
    if (typeof item !== 'string') throw Error('子任务日期格式错误')
    return item
  }
  const decimal = (key: string) => {
    const item = row[key]
    if (item === null || item === undefined || item === '') return null
    if ((typeof item !== 'number' && typeof item !== 'string') || !Number.isFinite(Number(item)))
      throw Error('子任务人天格式错误')
    return Number(item)
  }
  let owner: number | null = null,
    ownerName = ''
  if (row.owner !== null && row.owner !== undefined) {
    if (typeof row.owner !== 'object' || Array.isArray(row.owner))
      throw Error('子任务负责人格式错误')
    const id: unknown = Reflect.get(row.owner, 'id'),
      name: unknown = Reflect.get(row.owner, 'name')
    if (!positiveTaskId(id)) throw Error('子任务负责人 ID 无效')
    owner = id
    ownerName = typeof name === 'string' ? name : ''
  }
  if (typeof row.name !== 'string') throw Error('子任务名称格式错误')
  return {
    id: row.id,
    requirement_version: requirementId,
    owner_name: ownerName,
    name: row.name,
    task_type: integer('task_type'),
    status: integer('status'),
    self_test_status: integer('self_test_status'),
    sort_order: integer('sort_order'),
    owner,
    planned_start_date: date('planned_start_date'),
    planned_end_date: date('planned_end_date'),
    estimated_person_days: decimal('estimated_person_days'),
    actual_person_days: decimal('actual_person_days'),
  }
}

export function taskPayload(form: RequirementTaskForm, id: number | null, requirementId: number) {
  return {
    ...(id === null ? {} : { id }),
    requirement_version: requirementId,
    ...createTaskForm(form),
    owner: form.owner ?? null,
    planned_start_date: form.planned_start_date || null,
    planned_end_date: form.planned_end_date || null,
  }
}

export function sameTaskForm(a: RequirementTaskForm, b: RequirementTaskForm) {
  return JSON.stringify(createTaskForm(a)) === JSON.stringify(createTaskForm(b))
}
