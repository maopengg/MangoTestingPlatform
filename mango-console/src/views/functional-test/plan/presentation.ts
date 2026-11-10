import { formatAutomationBindings } from '../case-library/config'
import type { PlanCaseRow, PlanDetail } from './types'

export function planObject(value: unknown): Readonly<Record<string, unknown>> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('计划数据格式错误')
  return value as Readonly<Record<string, unknown>>
}
export function planList(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw Error('计划列表格式错误')
  return value
}
export function planIdValue(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value <= 0)
    throw Error('计划 ID 无效')
  return value
}
const text = (value: unknown) => (typeof value === 'string' ? value : '')
const count = (value: unknown) => (typeof value === 'number' && Number.isFinite(value) ? value : 0)
const relation = (value: unknown) => (value == null ? null : planIdValue(value))
export function parsePlanCase(value: unknown): PlanCaseRow {
  const row = planObject(value)
  const defects = planList(row.defects ?? []).map((value) => {
    const defect = planObject(value)
    return {
      id: planIdValue(defect.id),
      defect_no: text(defect.defect_no),
      title: text(defect.title),
      status: count(defect.status),
    }
  })
  return {
    id: planIdValue(row.id),
    plan: planIdValue(row.plan),
    case_no: text(row.case_no),
    title: text(row.title),
    priority: count(row.priority),
    category_level_1: text(row.category_level_1),
    category_level_2: text(row.category_level_2),
    category_level_3: text(row.category_level_3),
    project_product_id: relation(row.project_product_id),
    module_id: relation(row.module_id),
    owner_id: relation(row.owner_id),
    project_product_path: text(row.project_product_path),
    module_path: text(row.module_path),
    owner_name: text(row.owner_name),
    automation_status: text(row.automation_status),
    automation_bindings: formatAutomationBindings(row.automation_bindings),
    precondition: text(row.precondition),
    test_point: text(row.test_point),
    expected_result: text(row.expected_result),
    acceptance_source: text(row.acceptance_source),
    test_data: text(row.test_data),
    remark: text(row.remark),
    test_steps: planList(row.test_steps ?? []).map((value) => {
      const step = planObject(value)
      return { action: text(step.action), expected: text(step.expected) }
    }),
    test_types: planList(row.test_types ?? []).map(count),
    story_refs: planList(row.story_refs ?? []).map(text),
    scenario_layer: count(row.scenario_layer),
    scenario_type: count(row.scenario_type),
    scenario_tags: planList(row.scenario_tags ?? []).map(text),
    result: count(row.result),
    actual_result: text(row.actual_result),
    execution_note: text(row.execution_note),
    defects,
    defect_summary: defects.map((item) => `${item.defect_no} ${item.title}`).join('、') || '-',
    open_defect_count: count(row.open_defect_count),
  }
}
export function parsePlanDetail(value: unknown, id: number): PlanDetail {
  const row = planObject(value)
  if (planIdValue(row.id) !== id || typeof row.status !== 'number') throw Error('计划范围无效')
  const product = row.project_product ? planObject(row.project_product) : null
  const version = row.requirement_version ? planObject(row.requirement_version) : null
  const requirement = version?.requirement ? planObject(version.requirement) : null
  const iteration = row.iteration ? planObject(row.iteration) : null
  const stats = planObject(row.execution_stats)
  const cases = planList(row.cases).map(parsePlanCase)
  if (cases.some((item) => item.plan !== id)) throw Error('计划用例范围无效')
  return {
    id,
    name: text(row.name),
    status: row.status,
    scope_type: count(row.scope_type),
    scope_ref: text(row.scope_ref),
    project_product: product ? { id: planIdValue(product.id), name: text(product.name) } : null,
    requirement_version: version
      ? {
          requirement_name: text(version.requirement_name),
          version_no: count(version.version_no),
          requirement: requirement ? { name: text(requirement.name) } : null,
        }
      : null,
    iteration: iteration ? { name: text(iteration.name) } : null,
    environment: text(row.environment),
    build_version: text(row.build_version),
    started_at: text(row.started_at),
    finished_at: text(row.finished_at),
    defect_count: count(row.defect_count),
    open_defect_count: count(row.open_defect_count),
    unlinked_failed_count: count(row.unlinked_failed_count),
    execution_stats: {
      executed: count(stats.executed),
      total: count(stats.total),
      pass_rate: count(stats.pass_rate),
    },
    cases,
  }
}
