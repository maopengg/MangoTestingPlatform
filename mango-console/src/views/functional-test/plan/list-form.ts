import { planIdValue, planObject } from './presentation'
import type { PlanEditorDefaults, PlanEditorForm, PlanListRow } from './types'

export function planSelectionId(value: unknown): number | null {
  const leaf = Array.isArray(value) ? value[value.length - 1] : value
  if (
    (typeof leaf !== 'number' && typeof leaf !== 'string') ||
    (typeof leaf === 'string' && !/^\d+$/.test(leaf))
  )
    return null
  const id = Number(leaf)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
const text = (value: unknown) => (typeof value === 'string' ? value : '')
const count = (value: unknown) => (typeof value === 'number' && Number.isFinite(value) ? value : 0)
export function parsePlanListRow(value: unknown): PlanListRow {
  const row = planObject(value)
  const product = row.project_product ? planObject(row.project_product) : null
  const project = product?.project ? planObject(product.project) : null
  const owner = row.owner ? planObject(row.owner) : null
  const requirement = row.requirement_version ? planObject(row.requirement_version) : null
  const requirementParent = requirement?.requirement ? planObject(requirement.requirement) : null
  const iteration = row.iteration ? planObject(row.iteration) : null
  const stats = planObject(row.execution_stats)
  if (typeof row.status !== 'number' || typeof row.scope_type !== 'number')
    throw Error('计划状态格式错误')
  return {
    id: planIdValue(row.id),
    name: text(row.name),
    status: row.status,
    scope_type: row.scope_type,
    scope_ref: text(row.scope_ref),
    project_product: product
      ? {
          id: planIdValue(product.id),
          name: text(product.name),
          project: project ? { id: planIdValue(project.id), name: text(project.name) } : null,
        }
      : null,
    owner: owner
      ? { id: planIdValue(owner.id), name: text(owner.name) || text(owner.username) }
      : null,
    requirement_version: requirement
      ? {
          id: planIdValue(requirement.id),
          requirement_name: text(requirement.requirement_name),
          version_no: count(requirement.version_no),
          requirement: requirementParent ? { name: text(requirementParent.name) } : null,
        }
      : null,
    iteration: iteration
      ? {
          id: planIdValue(iteration.id),
          name: text(iteration.name),
          iteration_no: text(iteration.iteration_no),
        }
      : null,
    environment: text(row.environment),
    build_version: text(row.build_version),
    remark: text(row.remark),
    planned_start_time: text(row.planned_start_time) || null,
    planned_end_time: text(row.planned_end_time) || null,
    case_count: count(row.case_count),
    open_defect_count: count(row.open_defect_count),
    unlinked_failed_count: count(row.unlinked_failed_count),
    update_time: text(row.update_time),
    execution_stats: {
      executed: count(stats.executed),
      total: count(stats.total),
      passed: count(stats.passed),
      failed: count(stats.failed),
      blocked: count(stats.blocked),
      skipped: count(stats.skipped),
      progress: count(stats.progress),
      pass_rate: count(stats.pass_rate),
    },
  }
}
export function createPlanEditorForm(
  record: PlanListRow | null = null,
  defaults?: PlanEditorDefaults
): PlanEditorForm {
  return {
    name: record?.name ?? '',
    project_product: record?.project_product?.id ?? defaults?.productId ?? null,
    scope_type: record?.scope_type ?? 0,
    requirement_version: record?.requirement_version?.id ?? defaults?.requirementId ?? null,
    iteration: record?.iteration?.id ?? null,
    scope_ref: record?.scope_ref ?? '',
    owner: record?.owner?.id ?? null,
    environment: record?.environment ?? '',
    build_version: record?.build_version ?? '',
    planned_start_time: record?.planned_start_time ?? null,
    planned_end_time: record?.planned_end_time ?? null,
    remark: record?.remark ?? '',
  }
}
export function planEditorPayload(form: PlanEditorForm, id: number | null) {
  return {
    ...(id === null ? {} : { id }),
    name: form.name.trim(),
    project_product: planSelectionId(form.project_product),
    scope_type: form.scope_type,
    requirement_version: form.scope_type === 0 ? planSelectionId(form.requirement_version) : null,
    iteration: form.scope_type === 1 ? planSelectionId(form.iteration) : null,
    scope_ref: form.scope_ref,
    owner: planSelectionId(form.owner),
    environment: form.environment,
    build_version: form.build_version,
    planned_start_time: form.planned_start_time || null,
    planned_end_time: form.planned_end_time || null,
    remark: form.remark,
  }
}
