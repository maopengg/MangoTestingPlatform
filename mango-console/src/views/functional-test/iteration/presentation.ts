import { normalizeLibraryCaseRow } from '../case-library/rows'
import type {
  IterationDetail,
  IterationSuite,
  IterationBoardColumn,
  IterationGanttData,
  IterationGanttItem,
  IterationPlan,
  IterationDefect,
  RequirementOverviewSuite,
  RequirementOverviewCase,
  RequirementOverviewResource,
} from './types'

export function iterationObject(value: unknown): Readonly<Record<string, unknown>> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('记录格式错误')
  return value as Readonly<Record<string, unknown>>
}
export function iterationList(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw Error('列表格式错误')
  return value
}
const text = (value: unknown, fallback = '') => (typeof value === 'string' ? value : fallback)
const number = (value: unknown, fallback = 0) =>
  typeof value === 'number' && Number.isFinite(value) ? value : fallback
export function iterationRecordId(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value <= 0)
    throw Error('记录 ID 无效')
  return value
}
const person = (value: unknown) => {
  if (value == null) return null
  const row = iterationObject(value)
  return { id: iterationRecordId(row.id), name: text(row.name, text(row.username)) }
}
const date = (value: unknown) => text(value) || null
export function parseIterationDetail(value: unknown): IterationDetail {
  const row = iterationObject(value)
  return {
    id: iterationRecordId(row.id),
    name: text(row.name),
    status: number(row.status),
    start_date: date(row.start_date),
    end_date: date(row.end_date),
    owner: person(row.owner),
  }
}
export function parseIterationSuite(value: unknown): IterationSuite {
  const row = iterationObject(value),
    requirement = row.requirement ? iterationObject(row.requirement) : null
  if (typeof row.status !== 'number') throw Error('需求状态缺失')
  const metrics = row.test_metrics ? iterationObject(row.test_metrics) : {}
  return {
    id: iterationRecordId(row.id),
    requirement_name: text(row.requirement_name) || text(requirement?.name, '未命名需求'),
    requirement: requirement
      ? {
          id: iterationRecordId(requirement.id),
          name: text(requirement.name),
          requirement_key: text(requirement.requirement_key),
        }
      : null,
    version_no: number(row.version_no),
    development_owner: person(row.development_owner),
    owner: person(row.owner),
    priority: number(row.priority),
    status: row.status,
    planned_start_date: date(row.planned_start_date),
    planned_submit_date: date(row.planned_submit_date),
    actual_submit_at: date(row.actual_submit_at),
    update_time: text(row.update_time),
    case_count: number(row.case_count),
    open_defect_count: number(row.open_defect_count),
    test_metrics: { progress: number(metrics.progress), pass_rate: number(metrics.pass_rate) },
  }
}
export function parseIterationBoard(value: unknown): IterationBoardColumn[] {
  return iterationList(iterationObject(value).columns).map((value) => {
    const row = iterationObject(value)
    if (typeof row.status !== 'number') throw Error('看板状态缺失')
    return {
      status: row.status,
      title: text(row.title),
      items: iterationList(row.items).map(parseIterationSuite),
    }
  })
}
export function emptyIterationGantt(): IterationGanttData {
  return {
    iteration: null,
    today: null,
    groups: [],
    summary: { owner_count: 0, requirement_count: 0, overdue_count: 0, overlap_count: 0 },
  }
}
export function parseIterationGantt(value: unknown): IterationGanttData {
  const row = iterationObject(value),
    period = iterationObject(row.iteration),
    summary = iterationObject(row.summary)
  return {
    iteration: {
      id: iterationRecordId(period.id),
      start_date: date(period.start_date),
      end_date: date(period.end_date),
    },
    today: date(row.today),
    summary: {
      owner_count: number(summary.owner_count),
      requirement_count: number(summary.requirement_count),
      overdue_count: number(summary.overdue_count),
      overlap_count: number(summary.overlap_count),
    },
    groups: iterationList(row.groups).map((value) => {
      const group = iterationObject(value)
      return {
        owner_id: group.owner_id == null ? null : iterationRecordId(group.owner_id),
        owner_name: text(group.owner_name),
        items: iterationList(group.items).map((value): IterationGanttItem => {
          const item = iterationObject(value)
          if (typeof item.id !== 'string' && typeof item.id !== 'number')
            throw Error('排期 ID 缺失')
          return {
            id: item.id,
            suite_id: iterationRecordId(item.suite_id),
            requirement_key: text(item.requirement_key),
            requirement_name: text(item.requirement_name),
            version_no: number(item.version_no),
            status: number(item.status),
            planned_start_date: date(item.planned_start_date),
            planned_submit_date: date(item.planned_submit_date),
            time_progress: number(item.time_progress),
            overlap: item.overlap === true,
            overdue: item.overdue === true,
            overlap_with: Array.isArray(item.overlap_with)
              ? item.overlap_with.map((value) => text(value))
              : [],
          }
        }),
      }
    }),
  }
}
export function parseIterationPlan(value: unknown): IterationPlan {
  const row = iterationObject(value),
    stats = row.execution_stats ? iterationObject(row.execution_stats) : {}
  return {
    id: iterationRecordId(row.id),
    name: text(row.name),
    scope_type: number(row.scope_type),
    status: number(row.status),
    owner: person(row.owner),
    execution_stats: {
      executed: number(stats.executed),
      total: number(stats.total),
      progress: number(stats.progress),
      pass_rate: number(stats.pass_rate),
    },
    open_defect_count: number(row.open_defect_count),
    update_time: text(row.update_time),
  }
}
export function parseIterationDefect(value: unknown): IterationDefect {
  const row = iterationObject(value)
  return {
    id: iterationRecordId(row.id),
    defect_no: text(row.defect_no),
    title: text(row.title),
    status: number(row.status),
    severity: number(row.severity),
    priority: number(row.priority),
    assignee: person(row.assignee),
    update_time: text(row.update_time),
  }
}
export function parseIterationCase(value: unknown) {
  const row = iterationObject(value),
    suite = row.suite ? iterationObject(row.suite) : null,
    requirement = suite?.requirement ? iterationObject(suite.requirement) : null
  return {
    ...normalizeLibraryCaseRow(value),
    source_requirement: suite
      ? `${text(requirement?.requirement_key, 'REQ')} · ${
          text(suite.requirement_name) || text(requirement?.name, '-')
        } V${number(suite.version_no) || '-'}`
      : '-',
    iteration_plan_count: number(row.iteration_plan_count),
    iteration_recent_result: number(row.iteration_recent_result),
    iteration_open_defect_count: number(row.iteration_open_defect_count),
  }
}

export function parseRequirementOverviewSuite(value: unknown): RequirementOverviewSuite {
  const row = iterationObject(value),
    product = row.project_product == null ? null : iterationObject(row.project_product)
  const project = product?.project == null ? null : iterationObject(product.project)
  const module = row.module == null ? null : iterationObject(row.module)
  const iteration = row.iteration_ref == null ? null : iterationObject(row.iteration_ref)
  return {
    ...parseIterationSuite(value),
    project_product: product
      ? {
          id: iterationRecordId(product.id),
          name: text(product.name),
          project: project ? { id: iterationRecordId(project.id), name: text(project.name) } : null,
        }
      : null,
    module: module
      ? {
          id: iterationRecordId(module.id),
          name: text(module.name),
          full_path: text(module.full_path),
        }
      : null,
    iteration_ref: iteration ? { id: iterationRecordId(iteration.id) } : null,
    automation_coverage_percent: number(row.automation_coverage_percent),
  }
}
export function parseRequirementOverviewCase(value: unknown): RequirementOverviewCase {
  const row = iterationObject(value)
  return {
    id: iterationRecordId(row.id),
    case_no: text(row.case_no),
    title: text(row.title),
    priority: number(row.priority),
    owner: person(row.owner),
  }
}
export function parseRequirementOverviewResource(value: unknown): RequirementOverviewResource {
  const row = iterationObject(value)
  return {
    id: iterationRecordId(row.id),
    title: text(row.title),
    context_key: text(row.context_key),
    update_time: text(row.update_time),
  }
}
