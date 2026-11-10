import { normalizeEmptyListTotal } from '@/utils/api-response'
import type { MonitoringTaskQuery } from '@/api/monitoring/task'
import type { MonitoringTaskSnapshot, TaskSearchItem } from './types'
import { productId } from './editor-draft'

export function recordObject(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid monitoring response')
  return value as Record<string, unknown>
}
function integer(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('Invalid monitoring number')
  return value
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid monitoring text')
  return value
}
function nullableText(value: unknown) { return value == null ? null : text(value) }
function named(value: unknown) { const row = recordObject(value); return { id: integer(row.id), name: text(row.name) } }
export function readMonitoringTask(value: unknown): MonitoringTaskSnapshot {
  const row = recordObject(value), product = recordObject(row.project_product)
  if (row.is_notice !== 0 && row.is_notice !== 1) throw new Error('Invalid notification switch')
  return {
    id: integer(row.id), name: text(row.name), description: nullableText(row.description),
    project_product: { ...named(product), project: product.project == null ? null : named(product.project) },
    notice_group: row.notice_group == null ? null : named(row.notice_group),
    test_env: row.test_env == null ? null : integer(row.test_env), test_env_display: nullableText(row.test_env_display),
    is_notice: row.is_notice, script_content: text(row.script_content),
    status: integer(row.status), status_display: text(row.status_display), pid: row.pid == null ? null : integer(row.pid),
    started_at: nullableText(row.started_at), stopped_at: nullableText(row.stopped_at),
    create_time: text(row.create_time), update_time: text(row.update_time), update_user: row.update_user == null ? null : named(row.update_user),
  }
}
export function readMonitoringTaskResponse(value: unknown, expectedId: number) {
  const response = recordObject(value)
  if (response.code !== 200) throw new Error('Monitoring request failed')
  const task = readMonitoringTask(response.data)
  if (task.id !== expectedId) throw new Error('Monitoring task mismatch')
  return task
}
export function readMonitoringTaskPage(value: unknown) {
  value = normalizeEmptyListTotal(value)

  const response = recordObject(value)
  if (response.code !== 200 || !Array.isArray(response.data)) throw new Error('Invalid monitoring page')
  return { rows: response.data.map(readMonitoringTask), total: integer(response.totalSize) }
}
export function readMonitoringRuntime(value: unknown, expectedId: number) {
  const response = recordObject(value), row = recordObject(response.data)
  if (response.code !== 200 || row.id !== expectedId) throw new Error('Invalid monitoring control response')
  return { status: integer(row.status), pid: row.pid == null ? null : integer(row.pid), started_at: nullableText(row.started_at), stopped_at: nullableText(row.stopped_at), update_time: text(row.update_time) }
}
export function readMonitoringLog(value: unknown): string {
  const response = recordObject(value)
  if (response.code !== 200 || !Array.isArray(response.data) || !response.data.every(line => typeof line === 'string')) throw new Error('Invalid monitoring log')
  return response.data.join('')
}
export function monitoringTaskQuery(items: TaskSearchItem[], page: number, pageSize: number): MonitoringTaskQuery {
  const query: MonitoringTaskQuery = { page, pageSize }
  const name = items.find(item => item.key === 'name')?.value
  if (typeof name === 'string' && name.trim()) query.name = name.trim()
  const product = productId(items.find(item => item.key === 'project_product')?.value ?? null)
  if (product !== null) query.project_product = product
  return query
}
export const monitoringProcessActive = (task: MonitoringTaskSnapshot | null) => !!task && (task.status === 1 || task.status === 5 || Boolean(task.pid))
export const monitoringCanStop = (task: MonitoringTaskSnapshot | null) => !!task && (task.status === 1 || task.status === 5)
