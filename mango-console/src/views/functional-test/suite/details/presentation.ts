import type { SuiteCaseForm } from './case-form'
import type { SuiteResource } from './resource-form'
import { objectValue, resourceId } from './resource-form'

export interface SuiteRelation {
  id: number
  name: string
  full_path: string
  project: { name: string } | null
}
export interface SuiteSummary {
  id: number
  requirement_name: string
  version_no: number
  status: number
  requirement: SuiteRelation | null
  project_product: SuiteRelation | null
  module: SuiteRelation | null
  owner: SuiteRelation | null
  development_owner: SuiteRelation | null
  iteration_ref: SuiteRelation | null
  planned_start_date: string
  planned_submit_date: string
  update_time: string
  case_count: number
  plan_count: number
  open_defect_count: number
  test_metrics: { total: number; executed: number; progress: number; pass_rate: number }
}
export type SuiteCaseRow = Omit<SuiteCaseForm, 'id' | 'project_product' | 'module' | 'owner'> & {
  id: number
  suite: SuiteRelation
  project_product: SuiteRelation | null
  module: SuiteRelation | null
  owner: SuiteRelation | null
  change_status: number
  automation_impact_status: number
  bindings: Array<{
    id: number
    automation_type: number
    automation_case_id: number
    api_case: number | null
    ui_case: number | null
  }>
}
export interface SuitePlan {
  id: number
  name: string
  status: number
  owner: SuiteRelation | null
  update_time: string
  open_defect_count: number
  execution_stats: { total: number; executed: number; pass_rate: number }
}
export interface SuiteDefect {
  id: number
  defect_no: string
  title: string
  status: number
  severity: number
  assignee: SuiteRelation | null
  update_time: string
}
export const text = (value: unknown) => (typeof value === 'string' ? value : '')
const number = (value: unknown) => (typeof value === 'number' && Number.isFinite(value) ? value : 0)
export function requiredId(value: unknown): number {
  const id = resourceId(value)
  if (id === null) throw Error('Invalid ID')
  return id
}
export function list<T>(value: unknown, parse: (row: unknown) => T): T[] {
  if (!Array.isArray(value)) throw Error('Invalid list')
  return value.map(parse)
}
export function relation(value: unknown): SuiteRelation | null {
  if (value === null || value === undefined) return null
  const row = objectValue(value)
  return {
    id: requiredId(typeof value === 'object' ? row.id : value),
    name: text(row.name),
    full_path: text(row.full_path),
    project: row.project ? { name: text(objectValue(row.project).name) } : null,
  }
}
export function summary(value: unknown, expectedId: number): SuiteSummary {
  const row = objectValue(value),
    stats = objectValue(row.test_metrics)
  if (requiredId(row.id) !== expectedId) throw Error('Invalid suite owner')
  return {
    id: expectedId,
    requirement_name: text(row.requirement_name),
    version_no: number(row.version_no),
    status: number(row.status),
    requirement: relation(row.requirement),
    project_product: relation(row.project_product),
    module: relation(row.module),
    owner: relation(row.owner),
    development_owner: relation(row.development_owner),
    iteration_ref: relation(row.iteration_ref),
    planned_start_date: text(row.planned_start_date),
    planned_submit_date: text(row.planned_submit_date),
    update_time: text(row.update_time),
    case_count: number(row.case_count),
    plan_count: number(row.plan_count),
    open_defect_count: number(row.open_defect_count),
    test_metrics: {
      total: number(stats.total),
      executed: number(stats.executed),
      progress: number(stats.progress),
      pass_rate: number(stats.pass_rate),
    },
  }
}
export function caseRow(value: unknown, expectedSuite: number): SuiteCaseRow {
  const row = objectValue(value),
    suite = relation(row.suite)
  if (suite?.id !== expectedSuite) throw Error('Invalid case owner')
  return {
    id: requiredId(row.id),
    suite,
    version_no: resourceId(row.version_no),
    case_no: text(row.case_no),
    title: text(row.title),
    project_product: relation(row.project_product),
    module: relation(row.module),
    owner: relation(row.owner),
    priority: typeof row.priority === 'number' ? row.priority : null,
    test_types: list(row.test_types ?? [], number),
    scenario_layer: typeof row.scenario_layer === 'number' ? row.scenario_layer : null,
    scenario_type: typeof row.scenario_type === 'number' ? row.scenario_type : null,
    scenario_tags: list(row.scenario_tags ?? [], text),
    precondition: text(row.precondition),
    test_point: text(row.test_point),
    test_data: text(row.test_data),
    remark: text(row.remark),
    change_status: number(row.change_status),
    automation_impact_status: number(row.automation_impact_status),
    bindings: list(row.bindings ?? [], (item) => {
      const binding = objectValue(item)
      return {
        id: requiredId(binding.id),
        automation_type: number(binding.automation_type),
        automation_case_id: requiredId(binding.automation_case_id),
        api_case: resourceId(binding.api_case),
        ui_case: resourceId(binding.ui_case),
      }
    }),
  }
}
export function resourceRow(value: unknown, expectedSuite: number): SuiteResource {
  const row = objectValue(value)
  if (requiredId(row.suite) !== expectedSuite) throw Error('Invalid resource owner')
  return {
    id: requiredId(row.id),
    suite: expectedSuite,
    context_key: number(row.context_key),
    content_type: number(row.content_type),
    url_type: number(row.url_type),
    title: text(row.title),
    content: text(row.content),
    extracted_text: text(row.extracted_text),
    enabled: row.enabled === true,
    file: resourceId(row.file),
    file_name: text(row.file_name),
    file_path: text(row.file_path),
    mime_type: text(row.mime_type),
    file_size: typeof row.file_size === 'number' ? row.file_size : null,
  }
}
export function planRow(value: unknown): SuitePlan {
  const row = objectValue(value),
    stats = objectValue(row.execution_stats)
  return {
    id: requiredId(row.id),
    name: text(row.name),
    status: number(row.status),
    owner: relation(row.owner),
    update_time: text(row.update_time),
    open_defect_count: number(row.open_defect_count),
    execution_stats: {
      total: number(stats.total),
      executed: number(stats.executed),
      pass_rate: number(stats.pass_rate),
    },
  }
}
export function defectRow(value: unknown): SuiteDefect {
  const row = objectValue(value)
  return {
    id: requiredId(row.id),
    defect_no: text(row.defect_no),
    title: text(row.title),
    status: number(row.status),
    severity: number(row.severity),
    assignee: relation(row.assignee),
    update_time: text(row.update_time),
  }
}
export interface SuiteFilters {
  test_type: number | null
  scenario_layer: number | null
  scenario_type: number | null
  scenario_tag: string | null
  change_status: number | null
  automation_impact_status: number | null
}
export function createSuiteFilters(): SuiteFilters {
  return {
    test_type: null,
    scenario_layer: null,
    scenario_type: null,
    scenario_tag: null,
    change_status: null,
    automation_impact_status: null,
  }
}
export function filterPayload(filters: SuiteFilters) {
  return Object.fromEntries(
    Object.entries(filters).filter(
      ([, value]) => value !== '' && value !== null && value !== undefined
    )
  )
}
