import { taskEditorResponse, type TaskEditorId } from './task-editor-records'
import { taskListId, taskListObject } from './task-list-records'

export interface TaskGroupMember {
  id: TaskEditorId
  module: { id: TaskEditorId; full_path: string }
  task_id: TaskEditorId | null
  task_name: string
  child_enabled: boolean
  effective_enabled: boolean
  sync_status: string
}
export interface TaskGroupDetail {
  id: TaskEditorId
  name: string
  module_count: number
  enabled_task_count: number
  sync_status: string
  members: TaskGroupMember[]
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw Error('Invalid task group detail text')
  return value
}
function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw Error('Invalid task group count')
  return value
}
function flag(value: unknown): boolean {
  if (typeof value !== 'boolean') throw Error('Invalid member enabled state')
  return value
}
export function readTaskGroupMember(value: unknown): TaskGroupMember {
  const row = taskListObject(value), module = taskListObject(row.module)
  return {
    id: taskListId(row.id), module: { id: taskListId(module.id), full_path: text(module.full_path) },
    task_id: row.task_id == null ? null : taskListId(row.task_id), task_name: text(row.task_name),
    child_enabled: flag(row.child_enabled), effective_enabled: flag(row.effective_enabled), sync_status: text(row.sync_status),
  }
}
export function readTaskGroupDetail(response: unknown, id: TaskEditorId): TaskGroupDetail {
  const row = taskListObject(taskEditorResponse(response))
  if (String(taskListId(row.id)) !== String(id) || !Array.isArray(row.members)) throw Error('Invalid task group detail identity')
  const members = row.members.map(readTaskGroupMember)
  if (new Set(members.map(member => String(member.id))).size !== members.length) throw Error('Duplicate task group member')
  return { id: taskListId(row.id), name: text(row.name), module_count: count(row.module_count), enabled_task_count: count(row.enabled_task_count), sync_status: text(row.sync_status), members }
}
export function readTaskGroupMemberUpdate(response: unknown, member: TaskGroupMember): TaskGroupMember {
  const result = readTaskGroupMember(taskEditorResponse(response))
  if (String(result.id) !== String(member.id) || String(result.module.id) !== String(member.module.id)) throw Error('Invalid member update identity')
  return result
}
export function taskGroupSyncText(value: string): string {
  return ({ pending: '待同步', synced: '已同步', failed: '同步失败', archived: '已归档' } as Record<string, string>)[value] ?? value
}
export function taskGroupSyncColor(value: string): string {
  return ({ pending: 'orange', synced: 'green', failed: 'red', archived: 'gray' } as Record<string, string>)[value] ?? 'gray'
}
