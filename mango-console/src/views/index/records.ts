import { normalizeEmptyListTotal } from '@/utils/api-response'
import { reportStatusLabels } from './config'
import type { HomeReportCounts, HomeReportSummary, ProjectQualityItem, UpcomingTaskRecord, RiskTodoItem, RiskCleanupDetail, StatisticsData, HomeExecutionTrend, HomeActivitySnapshot } from './types'

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid home object')
  return value as Record<string, unknown>
}
function payload(value: unknown): unknown {
  const response = object(value)
  if (response.code !== 200) throw Error('Invalid home response')
  return response.data
}
function number(value: unknown): number {
  if (typeof value !== 'number' && (typeof value !== 'string' || !value.trim())) throw Error('Invalid home number')
  const result = Number(value)
  if (!Number.isFinite(result)) throw Error('Invalid home number')
  return result
}
function count(value: unknown): number {
  const result = number(value)
  if (!Number.isInteger(result) || result < 0) throw Error('Invalid home count')
  return result
}
function rate(value: unknown): number | null { return value == null ? null : number(value) }
export function emptyReportCounts(): HomeReportCounts {
  return { success: 0, fail: 0, warning: 0, proceed: 0, stay_begin: 0, stopped: 0 }
}
export function readProjectQuality(value: unknown): ProjectQualityItem[] {
  const rows = payload(value)
  if (!Array.isArray(rows)) throw Error('Invalid project quality rows')
  return rows.map(value => {
    const row = object(value)
    if (row.project_name != null && typeof row.project_name !== 'string') throw Error('Invalid project name')
    return {
      project_id: row.project_id == null ? null : count(row.project_id),
      project_name: row.project_name == null ? null : row.project_name,
      report_count: count(row.report_count), success_count: count(row.success_count),
      fail_count: count(row.fail_count), warning_count: count(row.warning_count),
      other_count: count(row.other_count), pass_rate: rate(row.pass_rate),
    }
  })
}
export function readReportSummary(value: unknown): HomeReportSummary {
  const data = payload(value)
  const counts = emptyReportCounts()
  const keys = Object.keys(reportStatusLabels) as Array<keyof HomeReportCounts>
  if (Array.isArray(data)) {
    const legacy = new Map(data.map(value => {
      const row = object(value)
      return [String(row.name || ''), count(row.value ?? 0)] as const
    }))
    keys.forEach(key => { counts[key] = legacy.get(reportStatusLabels[key]) ?? 0 })
    const completed = counts.success + counts.fail + counts.warning
    return { counts, passRate: completed ? Number((counts.success / completed * 100).toFixed(2)) : null }
  }
  const row = object(data), values = object(row.status_counts)
  keys.forEach(key => { counts[key] = count(values[key]) })
  return { counts, passRate: rate(row.final_pass_rate) }
}
export function formatPercent(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return '-'
  const result = Number(value)
  return Number.isFinite(result) ? `${result.toFixed(2)}%` : '-'
}

function text(value: unknown): string {
  if (typeof value !== 'string') throw Error('Invalid home text')
  return value
}
function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw Error('Invalid home list')
  return value
}
export function readUpcomingTasks(value: unknown): { rows: UpcomingTaskRecord[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const response = object(value)
  const rows = array(payload(response)).map(value => {
    const row = object(value), product = object(row.project_product)
    const project = object(product.project), owner = object(row.case_people)
    return {
      id: count(row.id), name: text(row.name),
      test_envs: array(row.test_envs).map(count),
      execution_scenes: array(row.execution_scenes).map(text),
      execution_scope: row.execution_scope == null ? null : text(row.execution_scope),
      latest_result_status: row.latest_result_status == null ? null : count(row.latest_result_status),
      next_run_at: text(row.next_run_at), next_run_time: text(row.next_run_time),
      seconds_until_run: count(row.seconds_until_run),
      project_product: { name: text(product.name), project: { name: text(project.name) } },
      case_people: { id: owner.id == null ? null : count(owner.id), name: text(owner.name) },
      timing_strategies: array(row.timing_strategies).map(value => {
        const strategy = object(value)
        return { id: count(strategy.id), name: text(strategy.name), cron: text(strategy.cron) }
      }),
    }
  })
  // ResponseData omits totalSize when the backend count is zero.
  const total = response.totalSize == null && rows.length === 0 ? 0 : count(response.totalSize)
  return { rows, total }
}

export function readRiskTodos(value: unknown): { rows: RiskTodoItem[]; total: number; pending: number } {
  const data = object(payload(value))
  const rows = array(data.items).map(value => {
    const row = object(value), product = object(row.project_product), project = object(product.project)
    const module = row.module == null ? null : object(row.module)
    if (typeof row.can_mark_handled !== 'boolean') throw Error('Invalid risk state')
    return {
      id: count(row.id), source_type: count(row.source_type), source_id: count(row.source_id),
      event_type: count(row.event_type), event_type_name: text(row.event_type_name), severity: count(row.severity),
      title: text(row.title), summary: text(row.summary), due_at: row.due_at == null ? null : text(row.due_at),
      occurred_at: text(row.occurred_at), project_product: { name: text(product.name), project: { name: text(project.name) } },
      module: module ? { id: count(module.id), name: text(module.name) } : null,
      details: { ...object(row.details) },
      owners: array(row.owners).map(value => {
        const owner = object(value)
        return { id: count(owner.id), name: text(owner.name), username: text(owner.username) }
      }),
      can_mark_handled: row.can_mark_handled,
    }
  })
  return { rows, total: count(data.count), pending: count(object(data.summary).pending) }
}

export function riskCleanupDetails(value: unknown): RiskCleanupDetail[] {
  if (!Array.isArray(value)) return []
  return value.filter(value => value && typeof value === 'object' && !Array.isArray(value)).map(value => {
    const row = object(value)
    const optionalText = (key: string): string => {
      const value = row[key]
      return value == null ? '' : typeof value === 'string' ? value : JSON.stringify(value) ?? ''
    }
    return {
      item_id: typeof row.item_id === 'string' || typeof row.item_id === 'number' ? row.item_id : null,
      alias: optionalText('alias'), table_name: optionalText('table_name'), environment_name: optionalText('environment_name'),
      database_name: optionalText('database_name'), error: optionalText('error'), primary_key: optionalText('primary_key'),
      primary_value: row.primary_value,
    }
  })
}

export function readHandledTodo(value: unknown, id: number): string {
  const response = object(value), row = object(payload(response))
  if (count(row.id) !== id || row.can_mark_handled !== false) throw Error('Invalid handled acknowledgement')
  return text(response.msg)
}

export const emptyStatistics = (): StatisticsData => ({
    uiStats: {
      elementCount: null,
      pageCount: null,
      stepCount: null,
      caseCount: null,
      publicCount: null,
      authConfigCount: null,
    },
    apiStats: {
      interfaceCount: null,
      caseCount: null,
      scenarioCount: null,
      publicCount: null,
      headerCount: null,
      authConfigCount: null,
    },
    pytestStats: {
      projectCount: null,
      caseCount: null,
      fileCount: null,
      boundProjectCount: null,
      boundProductCount: null,
    },
    dataFactoryStats: {
      datasourceCount: null,
      datasourceBindingCount: null,
      entityCount: null,
      fieldCount: null,
      templateCount: null,
      caseConfigCount: null,
    },
    testConfigStats: {
      projectCount: null,
      projectProductCount: null,
      databaseCount: null,
      testObjectCount: null,
      testFileCount: null,
    },
    scheduledTaskStats: {
      taskCount: null,
      strategyCount: null,
      fireRecordCount: null,
      systemJobCount: null,
    },
  })


export function readStatistics(value: unknown): StatisticsData {
  const data = object(payload(value)), result = emptyStatistics()
  for (const group of Object.keys(result) as Array<keyof StatisticsData>) {
    const incoming = object(data[group])
    const output = result[group]
    for (const key of Object.keys(output)) {
      // 每个分组的键来自默认值工厂，只写已登记指标。
      Object.assign(output, { [key]: incoming[key] == null ? null : count(incoming[key]) })
    }
  }
  return result
}

export function emptyExecutionTrend(): HomeExecutionTrend {
  return { labels: [], api_count: [], ui_count: [], pytest_count: [] }
}
export function readExecutionTrend(value: unknown): HomeExecutionTrend {
  const data = object(payload(value)), labels = array(data.labels).map(text)
  const api_count = array(data.api_count).map(count), ui_count = array(data.ui_count).map(count)
  const pytest_count = array(data.pytest_count).map(count)
  if ([api_count, ui_count, pytest_count].some(values => values.length !== labels.length)) throw Error('Invalid trend series length')
  return { labels, api_count, ui_count, pytest_count }
}

export function emptyHomeActivity(): HomeActivitySnapshot {
  return { rows: [], total: 0, activeUsers: 0, activityRate: 0, visitCount: 0, daily: [] }
}
export function readHomeActivity(value: unknown): HomeActivitySnapshot {
  const data = object(payload(value)), ids = array(data.user_ids), names = array(data.name)
  const counts = array(data.total_logins)
  if (ids.length !== names.length || counts.length !== names.length) throw Error('Invalid activity series length')
  const rows = names.map((name, index) => ({ id: String(count(ids[index])), name: text(name), count: count(counts[index]) }))
  return {
    rows, total: count(data.rank_total), activeUsers: count(data.active_users),
    activityRate: number(data.activity_rate), visitCount: count(data.visit_count),
    daily: array(data.daily_activity).map(value => {
      const row = object(value)
      return { date: text(row.date), active_users: count(row.active_users) }
    }),
  }
}
