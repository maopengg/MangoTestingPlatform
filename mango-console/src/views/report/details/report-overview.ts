import { normalizeEmptyListTotal } from '@/utils/api-response'
export function reportObject(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : null
}
export function reportIdentifier(value: unknown): string | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? String(value) : null
  return typeof value === 'string' && /^\d+$/.test(value.trim()) ? value.trim() : null
}
const text = (value: unknown) => typeof value === 'string' ? value : ''
function count(value: unknown, fallback = 0): number {
  if (value == null) return fallback
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('报告统计格式不正确')
  return value
}
function nullableNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}
export function reportPayload(response: unknown) {
  const envelope = reportObject(response)
  if (!envelope || envelope.code !== 200) throw new Error('报告读取失败')
  return envelope.data
}
export interface ReportOverview {
  id: string
  tasks: { name: string } | null
  user: { name: string } | null
  execution_name: string
  status: number | null
  report_conclusion: number | null
  retained_summary: boolean
  diagnostic_file_path: string
  test_env: number | null
  api_concurrency_limit: number | null
  is_notice: number | null
  create_time: string
}
export function parseReportOverview(response: unknown, expectedId: string): ReportOverview {
  const row = reportObject(reportPayload(response))
  if (!row || reportIdentifier(row.id) !== expectedId) throw new Error('报告记录不匹配')
  const task = reportObject(row.tasks), user = reportObject(row.user)
  return {
    id: expectedId, tasks: task ? { name: text(task.name) } : null, user: user ? { name: text(user.name) } : null,
    execution_name: text(row.execution_name), status: nullableNumber(row.status),
    report_conclusion: nullableNumber(row.report_conclusion), retained_summary: Boolean(row.retained_summary),
    diagnostic_file_path: text(row.diagnostic_file_path), test_env: nullableNumber(row.test_env),
    api_concurrency_limit: nullableNumber(row.api_concurrency_limit), is_notice: nullableNumber(row.is_notice),
    create_time: text(row.create_time),
  }
}
export function emptyReportSummary() {
  return {
    count: 0, excluded_count: 0, fail_count: 0, success_count: 0, warning_count: 0,
    stay_begin_count: 0, proceed_count: 0, stopped_count: 0,
    ui_count: 0, api_count: 0, pytest_count: 0, evaluation_count: 0,
    raw_ui_count: 0, raw_api_count: 0, raw_pytest_count: 0, raw_evaluation_count: 0,
    ui_in_progress_count: 0, api_in_progress_count: 0, pytest_in_progress_count: 0, evaluation_in_progress_count: 0,
  }
}
export type ReportSummary = ReturnType<typeof emptyReportSummary>
export function parseReportSummary(response: unknown): ReportSummary {
  const row = reportObject(reportPayload(response))
  if (!row || row.count === undefined) throw new Error('报告统计缺少总数')
  const result = emptyReportSummary()
  for (const key of Object.keys(result) as Array<keyof ReportSummary>) {
    const fallbackKey = key.startsWith('raw_') ? key.slice(4) as keyof ReportSummary : key
    result[key] = count(row[key], count(row[fallbackKey]))
  }
  return result
}
export interface ReportFailureReasons {
  items: { message: string; count: number; percent: number }[]
  category_count: number
  failure_count: number
}
export const emptyReportFailureReasons = (): ReportFailureReasons => ({ items: [], category_count: 0, failure_count: 0 })
export function parseReportFailureReasons(response: unknown): ReportFailureReasons {
  const row = reportObject(reportPayload(response))
  if (!row || !Array.isArray(row.items)) throw new Error('失败原因统计格式不正确')
  return {
    category_count: count(row.category_count), failure_count: count(row.failure_count),
    items: row.items.map(value => {
      const item = reportObject(value)
      if (!item || typeof item.message !== 'string') throw new Error('失败原因格式不正确')
      const percent = nullableNumber(item.percent)
      if (percent === null || percent < 0 || percent > 100) throw new Error('失败原因比例格式不正确')
      return { message: item.message, count: count(item.count), percent }
    }),
  }
}
export function parseReportCasePage(response: unknown) {
  response = normalizeEmptyListTotal(response)
  const value = reportPayload(response), envelope = reportObject(response)
  if (!Array.isArray(value) || value.some(item => !reportObject(item))) throw new Error('报告列表格式不正确')
  return { rows: value, total: count(envelope?.totalSize ?? envelope?.total ?? envelope?.count) }
}
