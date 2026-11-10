import { reportIdentifier, reportObject } from './report-overview'

export interface ReportStatusOption { key: number | string; title: string }
type Evidence = Record<string, unknown>
type Scalar = string | number | null
export interface ReportCaseRow {
  id: Scalar
  name: string
  status: number | null
  case_type: 0 | 1 | 2
  error_message: string
  parameter_id: Scalar
  is_recovery: boolean
  response_time: Scalar
  test_time: Scalar
  stop_time: Scalar
  test_object: string
  start: Scalar
  stop: Scalar
  children: undefined
  __rowKey: string
  __detailId: string
  __caseId: string | null
  __caseName: string
  __apiInfoName: string
  __caseCount: number
  __caseRowSpan: number
  __caseSourceId: string | null
  __isFirstCaseRow: boolean
  __isWarningRow: boolean
  __isSnapshotRow: boolean
  __snapshotParameterId: Scalar
  // Dynamic execution evidence stays read-only at the renderer/API boundary.
  __sourceRecord: Evidence
  __detailRecord: Evidence
  __infrastructurePhase: string
  __failureReason: string
}
const text = (value: unknown) => typeof value === 'string' ? value : ''
const scalar = (value: unknown): Scalar => typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value)) ? value : null
function numeric(value: unknown): number | null {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return null
  if (typeof value !== 'number' && typeof value !== 'string') return null
  if (typeof value === 'string' && !value.trim()) return null
  const result = Number(value)
  return Number.isFinite(result) ? result : null
}
function count(value: unknown, fallback = 0) {
  const result = numeric(value)
  return result !== null && Number.isSafeInteger(result) && result >= 0 ? result : fallback
}
export function reportRecords(value: unknown): Evidence[] {
  return Array.isArray(value) ? value.filter((row): row is Evidence => reportObject(row) !== null) : []
}
export function caseResultRows(item: Evidence): Evidence[] {
  const children = reportRecords(item.children)
  return children.length ? children : [item]
}
function snapshotRow(item: Evidence, row: Evidence, index: number, total: number) {
  if (item.result_mode !== 'snapshot') return false
  const current = scalar(reportObject(item.snapshot_current_step)?.parameter_id), parameter = scalar(row.parameter_id)
  return current !== null && parameter !== null ? String(current) === String(parameter) : index === total - 1
}
function snapshotMessage(item: Evidence, row: Evidence): string {
  const retry = reportObject(item.snapshot_retry), progress = reportObject(item.snapshot_progress)
  const parts = ['执行中快照']
  if (numeric(retry?.current) !== null || numeric(retry?.max) !== null) parts.push(`重试 ${scalar(retry?.current) ?? 0}/${scalar(retry?.max) ?? '-'}`)
  if (numeric(progress?.done) !== null || numeric(progress?.total) !== null) parts.push(`进度 ${scalar(progress?.done) ?? 0}/${scalar(progress?.total) ?? '-'}`)
  const error = text(row.error_message) || text(retry?.reason)
  if (error) parts.push(error)
  if (text(item.snapshot_updated_at)) parts.push(`更新于 ${item.snapshot_updated_at}`)
  return parts.join('，')
}
export function flattenReportCases(value: unknown, caseType: 0 | 1 | 2): ReportCaseRow[] {
  return reportRecords(value).flatMap((item, itemIndex) => {
    const rows = caseResultRows(item)
    const infoName = text(item.api_info_name) || text(rows.find(row => text(row.api_info_name))?.api_info_name)
    const warningCount = Math.max(count(item.warning) - rows.filter(row => numeric(row.status) === 4).length, 0)
    const warnings: Evidence[] = Array.from({ length: warningCount }, (_, index) => ({
      id: `warning-${scalar(item.id) ?? scalar(item.case_id) ?? 'case'}-${index}`,
      name: caseType === 1 ? infoName || '未执行步骤' : '未执行步骤', status: 4,
      error_message: '该用例前置步骤失败，未被执行', __isWarningRow: true,
    }))
    const displayRows = [...rows, ...warnings]
    const caseId = reportIdentifier(item.case_id ?? item.id), detailId = reportIdentifier(item.id)
    const caseName = text(item.case_name) || text(item.name) || '未命名用例'
    const control = reportObject(item.execution_control)
    return displayRows.map((row, index) => {
      const isSnapshot = caseType === 1 && snapshotRow(item, row, index, displayRows.length)
      const status = isSnapshot ? 3 : numeric(row.status)
      const error = isSnapshot ? snapshotMessage(item, row) : (caseType === 2 ? text(reportObject(row.statusDetails)?.message) : '') || text(row.error_message)
      const name = text(row.name) || caseName
      const detail: Evidence = {
        ...row, test_suite_detail_id: detailId, __caseSourceId: detailId,
        case_type: caseType, name, status, error_message: error,
      }
      if (caseType === 0) Object.assign(detail, {
        test_time: row.test_time ?? item.test_time, test_object: row.test_object ?? item.test_object,
        video_path: row.video_path ?? item.video_path, error_message: error || text(item.error_message),
        cache_data: row.cache_data ?? item.cache_data, data_factory_cache_data: row.data_factory_cache_data ?? item.data_factory_cache_data,
        element_result_list: [row], children: [row],
      })
      if (caseType === 1) Object.assign(detail, {
        __caseId: caseId, __caseName: caseName, result_mode: item.result_mode,
        snapshot_progress: item.snapshot_progress, snapshot_retry: item.snapshot_retry, snapshot_updated_at: item.snapshot_updated_at,
      })
      return {
        id: scalar(row.id), name, status, case_type: caseType, error_message: error,
        parameter_id: scalar(row.parameter_id), is_recovery: row.is_recovery === true,
        response_time: scalar(row.response_time ?? reportObject(row.response)?.time),
        test_time: scalar(row.test_time), stop_time: scalar(row.stop_time), test_object: text(row.test_object),
        start: scalar(row.start), stop: scalar(row.stop), children: undefined,
        __rowKey: `${detailId ?? caseId ?? itemIndex}-${scalar(row.id) ?? index}-${index}-${itemIndex}`,
        __detailId: detailId ?? '-', __caseId: caseId, __caseName: caseName,
        __apiInfoName: text(row.api_info_name) || infoName || '-',
        __caseCount: count(item.case_sum, displayRows.length), __caseRowSpan: index === 0 ? displayRows.length : 0,
        __caseSourceId: detailId, __isFirstCaseRow: index === 0, __sourceRecord: item, __detailRecord: detail,
        __isWarningRow: row.__isWarningRow === true, __isSnapshotRow: isSnapshot,
        __snapshotParameterId: scalar(reportObject(item.snapshot_current_step)?.parameter_id),
        __infrastructurePhase: text(control?.phase), __failureReason: text(item.failure_reason),
      }
    })
  })
}
export function reportStatusText(value: unknown, options: readonly ReportStatusOption[] = [], fallback = '未知'): string {
  const status = numeric(value)
  if (status === null) return fallback
  if (status === 4) return '警告'
  return options.find(item => String(item.key) === String(status))?.title || fallback
}
export function reportStatusColor(value: unknown, colors: Readonly<Record<string, string>> = {}): string {
  const status = numeric(value)
  return status === null ? 'gray' : status === 4 ? 'orange' : colors[String(status)] || 'gray'
}
export function formatReportDuration(value: Scalar): string {
  if (value === null || value === '') return ''
  const duration = numeric(value)
  return duration === null ? `${value} 秒` : `${duration.toFixed(2)} 秒`
}
export function formatReportDateTime(value: Scalar): string {
  if (value === null || value === '') return ''
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return '-'
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}
