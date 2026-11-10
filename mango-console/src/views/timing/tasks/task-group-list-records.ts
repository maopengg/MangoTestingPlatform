import type { ExecutionQualityResult } from '@/api/system/tasks'
import { readTaskGroupDraft } from './task-group-editor-records'
import { taskEditorResponse, type TaskEditorId } from './task-editor-records'
import { taskListId, taskListObject } from './task-list-records'

export interface TaskGroupFilters {
  navigation_module_ids: TaskEditorId[]
  navigation_module_id: TaskEditorId | null
  name: string
  test_envs: number[]
  case_types: number[]
  execution_scenes: string[]
  status: number | null
  is_notice: number | null
  sync_status: string | null
}
export interface TaskGroupSummary { id: TaskEditorId; name: string }
interface Relation { id: TaskEditorId; name: string }
export type GroupRecentResult = ExecutionQualityResult & { group_execution_id: TaskEditorId }
export interface TaskGroupListRecord extends TaskGroupSummary {
  project_product: Relation & { project: Relation | null }
  case_people: Relation | null
  notice_group: Relation | null
  timing_strategies: Array<Relation & { cron: string }>
  test_envs: number[]
  case_types: number[]
  execution_scenes: string[]
  status: 0 | 1
  is_notice: 0 | 1
  fail_notice: 0 | 1
  module_count: number
  enabled_task_count: number
  sync_status: string
  update_user_name: string
  update_time: string
  recent_results: GroupRecentResult[]
}
export interface GroupNoticeExecution { id: TaskEditorId; test_env: number; planned_at: string; notice_group__name: string }
export type TaskGroupQuery = { page: number; pageSize: number; project_product_id?: TaskEditorId; module_ids?: TaskEditorId[]; name?: string; test_envs?: number[]; case_types?: number[]; execution_scenes?: string[]; status?: number; is_notice?: number; sync_status?: string }
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid task group text'); return value }
function number(value: unknown): number { if (typeof value !== 'number' || !Number.isFinite(value)) throw Error('Invalid task group metric'); return value }
function count(value: unknown): number { const result = number(value); if (!Number.isSafeInteger(result) || result < 0) throw Error('Invalid task group count'); return result }
function relation(value: unknown): Relation | null {
  if (value == null) return null
  const row = taskListObject(value)
  return { id: taskListId(row.id), name: text(row.name) }
}
export function taskGroupSummary(value: unknown): TaskGroupSummary {
  const row = taskListObject(value)
  return { id: taskListId(row.id), name: text(row.name) }
}
function readRecent(value: unknown): GroupRecentResult {
  const row = taskListObject(value), status = row.status_key
  if (status !== 'success' && status !== 'fail' && status !== 'warning' && status !== 'proceed' && status !== 'stay_begin' && status !== 'stopped') throw Error('Invalid group recent status')
  return { group_execution_id: taskListId(row.group_execution_id), status: number(row.status), status_key: status, status_text: text(row.status_text),
    test_env: number(row.test_env), test_env_text: text(row.test_env_text), create_time: row.create_time == null ? null : text(row.create_time), update_time: row.update_time == null ? null : text(row.update_time),
    duration_ms: number(row.duration_ms), total: count(row.total), success: count(row.success), fail: count(row.fail), warning: count(row.warning), proceed: count(row.proceed), stay_begin: count(row.stay_begin), stopped: count(row.stopped), excluded_count: row.excluded_count == null ? 0 : count(row.excluded_count), pass_rate: row.pass_rate == null ? null : number(row.pass_rate) }
}
export function readTaskGroupRecord(value: unknown): TaskGroupListRecord {
  const row = taskListObject(value), draft = readTaskGroupDraft(row), product = relation(row.project_product)
  if (!product || !Array.isArray(row.timing_strategies) || (row.recent_results !== undefined && !Array.isArray(row.recent_results))) throw Error('Invalid task group record')
  const recent: unknown[] = row.recent_results ?? []
  return { ...taskGroupSummary(row), project_product: { ...product, project: relation(taskListObject(row.project_product).project) }, case_people: relation(row.case_people), notice_group: relation(row.notice_group),
    timing_strategies: row.timing_strategies.map(value => { const option = relation(value); if (!option) throw Error('Invalid timing'); return { ...option, cron: text(taskListObject(value).cron) } }),
    test_envs: draft.test_envs, case_types: draft.case_types, execution_scenes: draft.execution_scenes, status: draft.status, is_notice: draft.is_notice, fail_notice: draft.fail_notice,
    module_count: count(row.module_count), enabled_task_count: count(row.enabled_task_count), sync_status: text(row.sync_status), update_user_name: text(row.update_user_name), update_time: text(row.update_time), recent_results: recent.map(readRecent) }
}
export function readTaskGroupList(response: unknown) {
  const data = taskListObject(taskEditorResponse(response))
  if (!Array.isArray(data.items)) throw Error('Invalid task group list')
  const rows = data.items.map(readTaskGroupRecord)
  if (new Set(rows.map(row => String(row.id))).size !== rows.length) throw Error('Duplicate task group')
  return { rows, total: count(data.count) }
}
export function readTaskGroupUpdate(response: unknown, id: TaskEditorId) {
  const record = readTaskGroupRecord(taskListObject(taskEditorResponse(response)).item)
  if (String(record.id) !== String(id)) throw Error('Task group update identity mismatch')
  return record
}
export function taskGroupQuery(product: TaskEditorId | null, filters: TaskGroupFilters, page: number, pageSize: number): TaskGroupQuery {
  const moduleIds = filters.navigation_module_ids.length ? filters.navigation_module_ids.map(taskListId) : filters.navigation_module_id === null ? [] : [taskListId(filters.navigation_module_id)]
  return { page, pageSize, ...(product === null ? {} : { project_product_id: taskListId(product) }), ...(moduleIds.length ? { module_ids: moduleIds } : {}),
    ...(filters.name.trim() ? { name: filters.name.trim() } : {}), ...(filters.test_envs.length ? { test_envs: filters.test_envs.slice() } : {}),
    ...(filters.case_types.length ? { case_types: filters.case_types.slice() } : {}), ...(filters.execution_scenes.length ? { execution_scenes: filters.execution_scenes.slice() } : {}),
    ...(filters.status == null ? {} : { status: filters.status }), ...(filters.is_notice == null ? {} : { is_notice: filters.is_notice }), ...(filters.sync_status ? { sync_status: filters.sync_status } : {}) }
}
export function readGroupNoticeExecutions(response: unknown): GroupNoticeExecution[] {
  const rows = taskEditorResponse(response)
  if (!Array.isArray(rows)) throw Error('Invalid group notice executions')
  const result = rows.map(value => { const row = taskListObject(value); return { id: taskListId(row.id), test_env: count(row.test_env), planned_at: text(row.planned_at), notice_group__name: text(row.notice_group__name) } })
  if (new Set(result.map(row => String(row.id))).size !== result.length) throw Error('Duplicate group notice execution')
  return result
}
export function readGroupTriggerResult(response: unknown) {
  const row = taskListObject(taskEditorResponse(response))
  return { generated_count: count(row.generated_count), failed_count: count(row.failed_count) }
}
