import { normalizeEmptyListTotal } from '@/utils/api-response'
export type ReportId = number | string
export type ReportSummaryKey = 'total' | 'success' | 'fail' | 'warning' | 'proceed' | 'stay_begin' | 'stopped' | 'excluded_count'
export interface ReportOption { value: ReportId; label: string }
export interface ReportTrendItem {
  label: string; batch_count: number; scheduled_count: number; other_count: number
  success_count: number; fail_count: number; warning_count: number; pass_rate: number | null
}
export interface ReportRow {
  id: ReportId; execution_name: string; status: number | null; report_conclusion: number | null
  test_env: number | null; is_notice: number | null; api_concurrency_limit: number | null
  execution_scope: ReportId | null; execution_scenes: ReportId[]; automation_types: number[]
  diagnostic_file_path: string; create_time: string
  execution_summary: Record<ReportSummaryKey, number>
  user: { id: ReportId | null; name: string } | null
  tasks: { id: ReportId | null; name: string; notice_group: ReportId | null } | null
  project_product: { id: ReportId; name: string; project: { id: ReportId | null; name: string } | null } | null
  module: { id: ReportId | null; name: string; full_path: string } | null
}
export function reportObject(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
export function reportId(value: unknown): ReportId | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? value : null
  return typeof value === 'string' && /^\d+$/.test(value) ? value : null
}
export function reportOptionValue(value: unknown): ReportId | null {
  return typeof value === 'string' ? value.trim() || null : reportId(value)
}
export function reportNumber(value: unknown): number | null {
  if (typeof value !== 'number' && !(typeof value === 'string' && /^\d+(\.\d+)?$/.test(value))) return null
  return Number.isFinite(Number(value)) && Number(value) >= 0 ? Number(value) : null
}
export function reportText(value: unknown) { return typeof value === 'string' ? value : '' }
export function reportEnvelope(value: unknown) {
  const response = reportObject(value)
  if (response.code !== 200) throw new Error('Report request failed')
  return response
}
function linkedId(value: unknown) { return reportId(value) ?? reportId(reportObject(value).id) }
const summaryKeys: ReportSummaryKey[] = ['total', 'success', 'fail', 'warning', 'proceed', 'stay_begin', 'stopped', 'excluded_count']
export function parseReportRow(value: unknown): ReportRow | null {
  const row = reportObject(value), id = reportId(row.id)
  if (id === null) return null
  const summary = reportObject(row.execution_summary)
  const product = reportObject(row.project_product), productId = linkedId(row.project_product)
  const project = reportObject(product.project), module = reportObject(row.module)
  const tasks = reportObject(row.tasks), user = reportObject(row.user)
  return {
    id, execution_name: reportText(row.execution_name), status: reportNumber(row.status),
    report_conclusion: reportNumber(row.report_conclusion), test_env: reportNumber(row.test_env),
    is_notice: reportNumber(row.is_notice), api_concurrency_limit: reportNumber(row.api_concurrency_limit),
    execution_scope: reportOptionValue(row.execution_scope),
    execution_scenes: Array.isArray(row.execution_scenes) ? row.execution_scenes.map(reportOptionValue).filter((item): item is ReportId => item !== null) : [],
    automation_types: Array.isArray(row.automation_types) ? row.automation_types.map(reportNumber).filter((item): item is number => item !== null) : [],
    diagnostic_file_path: reportText(row.diagnostic_file_path), create_time: reportText(row.create_time),
    execution_summary: Object.fromEntries(summaryKeys.map(key => [key, reportNumber(summary[key]) ?? 0])) as Record<ReportSummaryKey, number>,
    user: row.user == null ? null : { id: linkedId(row.user), name: reportText(user.name) },
    tasks: row.tasks == null ? null : { id: linkedId(row.tasks), name: reportText(tasks.name), notice_group: linkedId(tasks.notice_group) },
    project_product: productId === null ? null : {
      id: productId, name: reportText(product.name), project: product.project == null ? null : { id: linkedId(product.project), name: reportText(project.name) },
    },
    module: row.module == null ? null : { id: linkedId(row.module), name: reportText(module.name), full_path: reportText(module.full_path) },
  }
}
export function parseReportList(value: unknown) {
  value = normalizeEmptyListTotal(value)

  const response = reportEnvelope(value), total = reportNumber(response.totalSize)
  if (!Array.isArray(response.data) || total === null || !Number.isSafeInteger(total)) throw new Error('Invalid report list')
  const seen = new Set<string>()
  const rows = response.data.map(parseReportRow).filter((row): row is ReportRow => {
    if (!row || seen.has(String(row.id))) return false
    seen.add(String(row.id)); return true
  })
  return { rows, total }
}
export function parseReportOptions(value: unknown): ReportOption[] {
  const response = reportEnvelope(value)
  if (!Array.isArray(response.data)) throw new Error('Invalid report options')
  const items = new Map<string, ReportOption>()
  for (const entry of response.data) {
    const row = reportObject(entry), value = reportId(row.key) ?? reportId(row.id) ?? reportId(row.value)
    if (value !== null) items.set(String(value), { value, label: reportText(row.title) || reportText(row.name) || reportText(row.label) || String(value) })
  }
  return [...items.values()]
}
export function createReportCounts() { return { success: 0, fail: 0, warning: 0, pending: 0, todo: 0, stopped: 0 } }
export function parseReportTrendItems(value: unknown): ReportTrendItem[] {
  if (!Array.isArray(value)) return []
  return value.flatMap(entry => {
    const row = reportObject(entry), rate = reportNumber(row.pass_rate)
    if (typeof row.label !== 'string' || !row.label) return []
    return [{ label: row.label, batch_count: reportNumber(row.batch_count) ?? 0,
      scheduled_count: reportNumber(row.scheduled_count) ?? 0, other_count: reportNumber(row.other_count) ?? 0,
      success_count: reportNumber(row.success_count) ?? 0, fail_count: reportNumber(row.fail_count) ?? 0,
      warning_count: reportNumber(row.warning_count) ?? 0, pass_rate: rate !== null && rate <= 100 ? rate : null }]
  })
}
export function parseReportOverview(value: unknown, today = new Date()) {
  const payload = reportEnvelope(value).data
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new Error('Invalid report overview')
  const data = reportObject(payload), counts = createReportCounts()
  if (!Array.isArray(data.status_distribution) && reportNumber(data.successSun) === null && reportNumber(data.failSun) === null) throw new Error('Invalid report distribution')
  if (data.trend != null && !Array.isArray(data.trend)) throw new Error('Invalid report trend')
  if (Array.isArray(data.status_distribution)) {
    const byStatus = new Map(data.status_distribution.map(entry => { const row = reportObject(entry); return [reportNumber(row.status), reportNumber(row.value) ?? 0] }))
    counts.success = byStatus.get(1) ?? 0; counts.fail = byStatus.get(0) ?? 0
    counts.warning = byStatus.get(4) ?? 0; counts.pending = byStatus.get(3) ?? 0
    counts.todo = byStatus.get(2) ?? 0; counts.stopped = byStatus.get(5) ?? 0
  } else { counts.success = reportNumber(data.successSun) ?? 0; counts.fail = reportNumber(data.failSun) ?? 0 }
  let trend: ReportTrendItem[]
  if (Array.isArray(data.trend)) trend = parseReportTrendItems(data.trend)
  else {
    const success = Array.isArray(data.success) ? data.success : [], fail = Array.isArray(data.fail) ? data.fail : []
    const length = Math.max(success.length, fail.length, 12), monday = new Date(today)
    monday.setDate(monday.getDate() - (monday.getDay() || 7) + 1)
    const label = (value: Date) => `${String(value.getMonth() + 1).padStart(2, '0')}/${String(value.getDate()).padStart(2, '0')}`
    trend = Array.from({ length }, (_, index) => {
      const start = new Date(monday); start.setDate(start.getDate() - (length - 1 - index) * 7)
      const end = new Date(start); end.setDate(end.getDate() + 6)
      const passed = reportNumber(success[index]) ?? 0, failed = reportNumber(fail[index]) ?? 0, total = passed + failed
      return { label: `${label(start)}-${label(end)}`, batch_count: 0, scheduled_count: 0, other_count: total,
        success_count: passed, fail_count: failed, warning_count: 0, pass_rate: total ? Number((passed / total * 100).toFixed(2)) : null }
    })
  }
  return { counts, trend }
}
