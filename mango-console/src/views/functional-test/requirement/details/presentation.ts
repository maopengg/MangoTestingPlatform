import type {
  RequirementCaseRow,
  RequirementDefect,
  RequirementForm,
  RequirementPlan,
  RequirementRecord,
  RequirementResource,
  RequirementVersion,
  RequirementVersionField,
  RequirementVersionForm,
} from './types'

export function requirementObject(value: unknown): Readonly<Record<string, unknown>> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('需求数据格式错误')
  return value as Readonly<Record<string, unknown>>
}
export function requirementList(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw Error('列表格式错误')
  return value
}
export function requirementId(value: unknown): number | null {
  if (
    (typeof value !== 'string' && typeof value !== 'number') ||
    (typeof value === 'string' && !/^\d+$/.test(value))
  )
    return null
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
const id = (value: unknown) => {
  const parsed = requirementId(value)
  if (parsed === null) throw Error('ID 格式错误')
  return parsed
}
const text = (value: unknown) => (typeof value === 'string' ? value : '')
const numeric = (value: unknown) =>
  typeof value === 'number' && Number.isFinite(value) ? value : 0
const relatedId = (value: unknown) =>
  value === null || value === undefined
    ? null
    : id(typeof value === 'object' ? requirementObject(value).id : value)
const relatedName = (value: unknown) =>
  value && typeof value === 'object' ? text(requirementObject(value).name) : ''
const integer = (value: unknown) => {
  if (typeof value !== 'number' || !Number.isSafeInteger(value)) throw Error('状态格式错误')
  return value
}
export function createRequirementForm(source?: RequirementForm): RequirementForm {
  return {
    owner: source?.owner ?? null,
    issue_type: source?.issue_type ?? 0,
    requirement_category: source?.requirement_category ?? 0,
  }
}
export function createVersionForm(source?: RequirementVersionForm): RequirementVersionForm {
  return {
    requirement_name: source?.requirement_name ?? '',
    description: source?.description ?? '',
    owner: source?.owner ?? null,
    development_owner: source?.development_owner ?? null,
    delivery_team: source?.delivery_team ?? null,
    iteration_ref: source?.iteration_ref ?? null,
    test_required: source?.test_required ?? false,
    automation_recommended: source?.automation_recommended ?? false,
    effect_test_required: source?.effect_test_required ?? false,
    planned_start_date: source?.planned_start_date ?? null,
    planned_submit_date: source?.planned_submit_date ?? null,
    planned_release_date: source?.planned_release_date ?? null,
    customer_deadline_date: source?.customer_deadline_date ?? null,
    committed_release_date: source?.committed_release_date ?? null,
    customer_ref: source?.customer_ref ?? '',
  }
}
export function versionFormFrom(value: unknown): RequirementVersionForm {
  const row = requirementObject(value)
  return {
    requirement_name: text(row.requirement_name),
    description: text(row.description),
    owner: relatedId(row.owner),
    development_owner: relatedId(row.development_owner),
    delivery_team: relatedId(row.delivery_team),
    iteration_ref: relatedId(row.iteration_ref),
    test_required: row.test_required === true,
    automation_recommended: row.automation_recommended === true,
    effect_test_required: row.effect_test_required === true,
    planned_start_date: text(row.planned_start_date) || null,
    planned_submit_date: text(row.planned_submit_date) || null,
    planned_release_date: text(row.planned_release_date) || null,
    customer_deadline_date: text(row.customer_deadline_date) || null,
    committed_release_date: text(row.committed_release_date) || null,
    customer_ref: text(row.customer_ref),
  }
}
export function parseRequirement(value: unknown): RequirementRecord {
  const row = requirementObject(value)
  return {
    id: id(row.id),
    name: text(row.name),
    requirement_key: text(row.requirement_key),
    form: {
      owner: relatedId(row.owner),
      issue_type: integer(row.issue_type),
      requirement_category: integer(row.requirement_category),
    },
  }
}
export function parseRequirementVersion(value: unknown, expectedId: number): RequirementVersion {
  const row = requirementObject(value)
  if (id(row.id) !== expectedId) throw Error('需求版本归属错误')
  const product = row.project_product ? requirementObject(row.project_product) : null
  return {
    id: expectedId,
    status: integer(row.status),
    update_time: text(row.update_time),
    version_no: numeric(row.version_no),
    product: product ? { id: id(product.id), name: text(product.name) } : null,
    requirement: row.requirement ? parseRequirement(row.requirement) : null,
    form: versionFormFrom(row),
    ownerName: relatedName(row.owner),
    developerName: relatedName(row.development_owner),
    teamName: relatedName(row.delivery_team),
    iterationName: relatedName(row.iteration_ref),
  }
}
export function versionFieldPayload(
  field: RequirementVersionField,
  value: RequirementVersionForm[RequirementVersionField],
  expectedId: number
) {
  if (!Object.prototype.hasOwnProperty.call(createVersionForm(), field)) throw Error('非可编辑字段')
  const normalized = field.endsWith('_date') ? value || null : value === undefined ? null : value
  return { id: expectedId, [field]: normalized }
}
export function parseRequirementCase(value: unknown): RequirementCaseRow {
  const row = requirementObject(value)
  return {
    id: id(row.id),
    case_no: text(row.case_no),
    title: text(row.title),
    priority: typeof row.priority === 'number' ? row.priority : null,
    owner: row.owner ? { name: relatedName(row.owner) } : null,
  }
}
export function parseRequirementPlan(value: unknown): RequirementPlan {
  const row = requirementObject(value),
    stats = requirementObject(row.execution_stats)
  return {
    id: id(row.id),
    name: text(row.name),
    status: integer(row.status),
    owner: row.owner ? { name: relatedName(row.owner) } : null,
    execution_stats: { progress: numeric(stats.progress), pass_rate: numeric(stats.pass_rate) },
  }
}
export function parseRequirementDefect(value: unknown): RequirementDefect {
  const row = requirementObject(value)
  return {
    id: id(row.id),
    defect_no: text(row.defect_no),
    title: text(row.title),
    status: integer(row.status),
    severity: integer(row.severity),
    assignee: row.assignee ? { name: relatedName(row.assignee) } : null,
  }
}
export function parseRequirementResource(value: unknown): RequirementResource {
  const row = requirementObject(value)
  return {
    id: id(row.id),
    title: text(row.title),
    context_key: text(row.context_key),
    content: text(row.content),
    file_name: text(row.file_name),
    update_time: text(row.update_time),
  }
}
