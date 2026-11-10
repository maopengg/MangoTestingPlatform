import type { ManualCaseBinding, ManualCaseDetail } from '@/api/functional-test/types'
import { suiteSelectionId } from './editor-form'

interface Person {
  id: number
  name: string
  username: string
}
interface NamedRelation {
  id: number
  name: string
}
interface Product extends NamedRelation {
  project: NamedRelation | null
}
interface Module extends NamedRelation {
  full_path: string
  level: number | null
}
export interface SuiteListRow {
  id: number
  requirement_name: string
  version_no: number
  requirement: (NamedRelation & { requirement_key: string }) | null
  project_product: Product | null
  module: Module | null
  owner: Person | null
  development_owner: Person | null
  update_user: Person | null
  iteration_ref: NamedRelation | null
  iteration: string
  priority: number | null
  status: number | null
  planned_start_date: string | null
  planned_submit_date: string | null
  case_count: number
  automated_case_count: number
  automation_coverage_percent: number
  open_defect_count: number
  sync_status: number | null
  last_sync_time: string | null
  update_time: string
  test_metrics: { total: number; executed: number; progress: number; pass_rate: number }
}
export type CaseListRow = Omit<ManualCaseDetail, 'priority'> & {
  priority: number | null
  version_no: number | null
  suite: {
    id: number
    requirement_name: string
    iteration_ref: NamedRelation | null
    iteration: string
  } | null
  project_product: Product | null
  module: Module | null
  owner: Person | null
  test_types: number[]
  scenario_layer: number | null
  scenario_type: number | null
  scenario_tags: string[]
}
export interface UserOption {
  key: number
  title: string
}
const object = (value: unknown): Record<string, unknown> =>
  value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
const text = (value: unknown) => (typeof value === 'string' ? value : '')
const number = (value: unknown) =>
  typeof value === 'number' && Number.isFinite(value) ? value : null
const count = (value: unknown) => number(value) ?? 0
const date = (value: unknown) => text(value) || null
const id = (value: unknown) => {
  const valid = suiteSelectionId(
    typeof value === 'number' || typeof value === 'string' ? value : null
  )
  if (valid === null) throw Error('Invalid related ID')
  return valid
}
function named(value: unknown): NamedRelation | null {
  if (value == null) return null
  const row = object(value)
  return { id: id(typeof value === 'object' ? row.id : value), name: text(row.name) }
}
function person(value: unknown): Person | null {
  const result = named(value)
  return result ? { ...result, username: text(object(value).username) } : null
}
function product(value: unknown): Product | null {
  const result = named(value)
  return result ? { ...result, project: named(object(value).project) } : null
}
function module(value: unknown): Module | null {
  const result = named(value),
    row = object(value)
  return result ? { ...result, full_path: text(row.full_path), level: number(row.level) } : null
}
export function parseSuiteListRow(value: unknown): SuiteListRow {
  const row = object(value),
    requirement = named(row.requirement),
    metrics = object(row.test_metrics)
  return {
    id: id(row.id),
    requirement_name: text(row.requirement_name),
    version_no: count(row.version_no),
    requirement: requirement
      ? { ...requirement, requirement_key: text(object(row.requirement).requirement_key) }
      : null,
    project_product: product(row.project_product),
    module: module(row.module),
    owner: person(row.owner),
    development_owner: person(row.development_owner),
    update_user: person(row.update_user),
    iteration_ref: named(row.iteration_ref),
    iteration: text(row.iteration),
    priority: number(row.priority),
    status: number(row.status),
    planned_start_date: date(row.planned_start_date),
    planned_submit_date: date(row.planned_submit_date),
    case_count: count(row.case_count),
    automated_case_count: count(row.automated_case_count),
    automation_coverage_percent: count(row.automation_coverage_percent),
    open_defect_count: count(row.open_defect_count),
    sync_status: number(row.sync_status),
    last_sync_time: date(row.last_sync_time),
    update_time: text(row.update_time),
    test_metrics: {
      total: count(metrics.total),
      executed: count(metrics.executed),
      progress: count(metrics.progress),
      pass_rate: count(metrics.pass_rate),
    },
  }
}
export function parseCaseListRow(value: unknown): CaseListRow {
  const row = object(value),
    suite = named(row.suite),
    source = object(row.suite)
  const numbers = (value: unknown) => {
    if (value == null) return []
    if (
      !Array.isArray(value) ||
      !value.every((item) => typeof item === 'number' && Number.isFinite(item))
    )
      throw Error('Invalid test types')
    return [...value] as number[]
  }
  const tags = row.scenario_tags ?? []
  if (!Array.isArray(tags) || !tags.every((item) => typeof item === 'string'))
    throw Error('Invalid scenario tags')
  const bindings = row.bindings ?? []
  if (!Array.isArray(bindings)) throw Error('Invalid case bindings')
  return {
    id: id(row.id),
    version_no: number(row.version_no),
    case_no: text(row.case_no),
    title: text(row.title),
    priority: number(row.priority),
    test_types: numbers(row.test_types),
    scenario_layer: number(row.scenario_layer),
    scenario_type: number(row.scenario_type),
    scenario_tags: [...tags],
    project_product: product(row.project_product),
    module: module(row.module),
    owner: person(row.owner),
    suite: suite
      ? {
          id: suite.id,
          requirement_name: text(source.requirement_name),
          iteration_ref: named(source.iteration_ref),
          iteration: text(source.iteration),
        }
      : null,
    precondition: date(row.precondition),
    test_point: text(row.test_point),
    test_data: date(row.test_data),
    remark: date(row.remark),
    source_text: date(row.source_text),
    change_status: count(row.change_status),
    automation_impact_status: count(row.automation_impact_status),
    bindings: bindings.map((value): ManualCaseBinding => {
      const binding = object(value)
      return {
        id: id(binding.id),
        automation_type: count(binding.automation_type),
        automation_case_id: id(binding.automation_case_id),
        api_case: named(binding.api_case)?.id ?? null,
        ui_case: named(binding.ui_case)?.id ?? null,
        automation_case_name: date(binding.automation_case_name),
        optimize_status: count(binding.optimize_status),
      }
    }),
  }
}
export function parseUserOptions(value: unknown): UserOption[] {
  if (!Array.isArray(value)) throw Error('Invalid users')
  return value.map((value) => {
    const row = object(value)
    if (typeof row.title !== 'string') throw Error('Invalid user label')
    return { key: id(row.key), title: row.title }
  })
}
