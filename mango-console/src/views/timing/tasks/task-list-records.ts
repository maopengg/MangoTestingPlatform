import { normalizeEmptyListTotal } from '@/utils/api-response'
import type { TaskRecentResult } from '@/api/system/tasks'
import { readTaskEditorDraft, taskEditorId, taskEditorResponse, type TaskEditorDraft, type TaskEditorId } from './task-editor-records'

interface TaskRelation { id: TaskEditorId; name: string }
export interface TaskListRecord extends Omit<TaskEditorDraft, 'project_product' | 'module' | 'case_people' | 'notice_group' | 'timing_strategies'> {
  id: TaskEditorId
  project_product: (TaskRelation & { project: TaskRelation | null }) | null
  module: (TaskRelation & { full_path: string }) | null
  case_people: TaskRelation | null
  notice_group: TaskRelation | null
  timing_strategies: Array<TaskRelation & { cron: string }>
  task_group: TaskEditorId | null
  task_group_member_id: TaskEditorId | null
  task_group_name: string
  status: number
  is_notice: number
  fail_notice: number
  diagnostic_file_path: string
  update_user: (TaskRelation & { username: string }) | null
  update_time: string
}
export type TaskListRecentResult = Omit<TaskRecentResult, 'test_suite_id'> & { test_suite_id: TaskEditorId | null }
export type TaskListQuery = Record<string, string | number> & { page: number; pageSize: number }
export function taskListObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid task response')
  return value as Record<string, unknown>
}
export function taskListId(value: unknown): TaskEditorId {
  const id = taskEditorId(value)
  if (id === null || (typeof id === 'number' ? id < 0 : !/^\d+$/.test(id))) throw Error('Invalid task ID')
  return id
}
function text(value: unknown): string {
  if (value == null) return ''
  if (typeof value !== 'string') throw Error('Invalid task text')
  return value
}
function numeric(value: unknown, fallback?: number): number {
  if (value == null && fallback !== undefined) return fallback
  if (typeof value !== 'number' || !Number.isFinite(value)) throw Error('Invalid task metric')
  return value
}
function relation(value: unknown): TaskRelation | null {
  if (value == null || value === '') return null
  if (typeof value !== 'object') return { id: taskListId(value), name: '' }
  const row = taskListObject(value)
  return { id: taskListId(row.id), name: text(row.name) }
}
export function readTaskListRecord(value: unknown): TaskListRecord {
  const row = taskListObject(value), draft = readTaskEditorDraft(value)
  const product = relation(row.project_product), module = relation(row.module), user = relation(row.update_user)
  const productData = typeof row.project_product === 'object' && row.project_product !== null ? taskListObject(row.project_product) : {}
  const moduleData = typeof row.module === 'object' && row.module !== null ? taskListObject(row.module) : {}
  const userData = typeof row.update_user === 'object' && row.update_user !== null ? taskListObject(row.update_user) : {}
  if (row.timing_strategies != null && !Array.isArray(row.timing_strategies)) throw Error('Invalid task strategies')
  const strategies: unknown[] = row.timing_strategies ?? []
  return {
    ...draft, id: taskListId(row.id), project_product: product ? { ...product, project: relation(productData.project) } : null,
    module: module ? { ...module, full_path: text(moduleData.full_path) } : null,
    case_people: relation(row.case_people), notice_group: relation(row.notice_group),
    timing_strategies: strategies.map(value => {
      const option = relation(value)
      if (!option) throw Error('Invalid task strategy')
      return { ...option, cron: typeof value === 'object' ? text(taskListObject(value).cron) : '' }
    }),
    task_group: row.task_group == null ? null : taskListId(row.task_group),
    task_group_member_id: row.task_group_member_id == null ? null : taskListId(row.task_group_member_id),
    task_group_name: text(row.task_group_name), status: numeric(row.status, 0), is_notice: numeric(row.is_notice, 0), fail_notice: numeric(row.fail_notice, 0),
    diagnostic_file_path: text(row.diagnostic_file_path), update_user: user ? { ...user, username: text(userData.username) } : null, update_time: text(row.update_time),
  }
}
export function readTaskList(response: unknown) {
  response = normalizeEmptyListTotal(response)
  const data = taskEditorResponse(response), envelope = taskListObject(response)
  if (!Array.isArray(data)) throw Error('Invalid task list')
  const total = numeric(envelope.totalSize)
  if (!Number.isSafeInteger(total) || total < 0) throw Error('Invalid task count')
  return { rows: data.map(readTaskListRecord), total }
}
export function readTaskRecentResults(response: unknown, taskIds: TaskEditorId[]): Record<string, TaskListRecentResult[]> {
  const data = taskListObject(taskEditorResponse(response))
  const result: Record<string, TaskListRecentResult[]> = {}
  for (const id of taskIds) {
    const values = data[String(id)] ?? []
    if (!Array.isArray(values)) throw Error('Invalid recent results')
    result[String(id)] = values.map(value => {
      const row = taskListObject(value), status = row.status_key
      if (status !== 'success' && status !== 'fail' && status !== 'warning' && status !== 'proceed' && status !== 'stay_begin' && status !== 'stopped' && status !== 'blocked') throw Error('Invalid recent status')
      return {
        test_suite_id: row.test_suite_id == null ? null : taskListId(row.test_suite_id), report_retained: row.report_retained !== false,
        status: numeric(row.status), status_key: status, status_text: text(row.status_text), test_env: numeric(row.test_env), test_env_text: text(row.test_env_text),
        create_time: row.create_time == null ? null : text(row.create_time), update_time: row.update_time == null ? null : text(row.update_time),
        duration_ms: numeric(row.duration_ms), total: numeric(row.total), success: numeric(row.success), fail: numeric(row.fail), warning: numeric(row.warning),
        proceed: numeric(row.proceed), stay_begin: numeric(row.stay_begin), stopped: numeric(row.stopped),
        blocked: numeric(row.blocked, 0),
        pass_rate: row.pass_rate == null ? null : numeric(row.pass_rate), excluded_count: numeric(row.excluded_count, 0),
      }
    })
  }
  return result
}
export function taskListQuery(values: Record<string, unknown>, page: number, pageSize: number, moduleId: TaskEditorId | null, moduleIds: TaskEditorId[]): TaskListQuery {
  const query: Record<string, string | number> = {}
  for (const [key, value] of Object.entries(values)) {
    if (value === '' || value == null || (Array.isArray(value) && !value.length)) continue
    if (key === 'project_product' || key === 'module') {
      const id = taskEditorId(value)
      if (id !== null) query[key] = id
    } else if (typeof value === 'string' || typeof value === 'number') query[key] = value
    else if (Array.isArray(value)) query[key] = value.join(',')
  }
  if (moduleId !== null) { query.module = moduleId; delete query.module__in }
  else if (moduleIds.length) { delete query.module; query.module__in = moduleIds.join(',') }
  return { ...query, page, pageSize }
}
