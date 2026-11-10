import { normalizeEmptyListTotal } from '@/utils/api-response'
import type { MonitoringReport, MonitoringReportQuery } from '@/api/monitoring/report'
import type { ReportSearchItem } from './types'

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid report response')
  return value as Record<string, unknown>
}
function integer(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('Invalid report number')
  return value
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('Invalid report text')
  return value
}
function nullableText(value: unknown) { return value == null ? null : text(value) }

export function readMonitoringReport(value: unknown): MonitoringReport {
  const row = object(value)
  const group = row.task_notice_group == null ? null : object(row.task_notice_group)
  return {
    id: integer(row.id), create_time: text(row.create_time), update_time: text(row.update_time),
    task: row.task === null ? null : integer(row.task), task_name: text(row.task_name),
    task_notice_group: group === null ? null : { id: integer(group.id), name: text(group.name) },
    status: integer(row.status), status_display: text(row.status_display),
    msg: nullableText(row.msg), send_text: nullableText(row.send_text), is_notice: integer(row.is_notice),
  }
}

export function readReportPage(value: unknown) {
  value = normalizeEmptyListTotal(value)

  const response = object(value)
  if (response.code !== 200 || !Array.isArray(response.data)) throw new Error('Invalid report page')
  return { rows: response.data.map(readMonitoringReport), total: integer(response.totalSize) }
}

export function createReportQuery(items: ReportSearchItem[], page: number, pageSize: number): MonitoringReportQuery {
  const result: MonitoringReportQuery = { page, pageSize }
  const name = items.find(item => item.key === 'task_name')?.value
  if (typeof name === 'string' && name.trim()) result.task__name__contains = name.trim()
  const status = items.find(item => item.key === 'status')?.value
  if (Array.isArray(status)) {
    const values = [...new Set(status
      .filter(value => typeof value === 'number' || (typeof value === 'string' && value.trim() !== ''))
      .map(Number).filter(value => Number.isSafeInteger(value) && value >= 0))]
    if (values.length) result.status__in = values.join(',')
  }
  return result
}
