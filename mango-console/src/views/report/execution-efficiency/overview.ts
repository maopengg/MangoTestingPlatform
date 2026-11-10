export type EfficiencyId = number | string
export function efficiencyObject(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
}
export const efficiencyText = (value: unknown) => typeof value === 'string' ? value : ''
export function efficiencyId(value: unknown): EfficiencyId | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : typeof value === 'string' && /^\d+$/.test(value) ? value : null
}
export function efficiencyNumber(value: unknown): number | null {
  if (typeof value !== 'number' && !(typeof value === 'string' && /^\d+(\.\d+)?$/.test(value))) return null
  const number = Number(value)
  return Number.isFinite(number) && number >= 0 ? number : null
}
export function efficiencyPayload(value: unknown): Record<string, unknown> {
  const response = efficiencyObject(value), row = efficiencyObject(response?.data)
  if (response?.code !== 200 || !row) throw new Error('Invalid efficiency response')
  return row
}
function rows(value: unknown): Record<string, unknown>[] {
  if (value === undefined) return []
  if (!Array.isArray(value)) throw new Error('Invalid efficiency rows')
  return value.map(item => { const row = efficiencyObject(item); if (!row) throw new Error('Invalid efficiency row'); return row })
}
function ownership(row: Record<string, unknown>) {
  const product = efficiencyObject(row.project_product), project = efficiencyObject(product?.project), module = efficiencyObject(row.module)
  return {
    project_product: { id: efficiencyId(product?.id), name: efficiencyText(product?.name), project: { name: efficiencyText(project?.name) } },
    module: { id: efficiencyId(module?.id), name: efficiencyText(module?.name), full_path: efficiencyText(module?.full_path) },
  }
}
function liveRow(row: Record<string, unknown>) {
  const current = efficiencyObject(row.current_case)
  if (efficiencyId(row.id) === null || efficiencyId(row.report_id) === null) throw new Error('Invalid efficiency row identifier')
  return {
    ...ownership(row), id: efficiencyId(row.id), report_id: efficiencyId(row.report_id),
    name: efficiencyText(row.name), report_name: efficiencyText(row.report_name), case_name: efficiencyText(row.case_name),
    test_env: efficiencyId(row.test_env), stage: efficiencyText(row.stage), reason: efficiencyText(row.reason),
    pending: efficiencyNumber(row.pending) ?? 0, running: efficiencyNumber(row.running) ?? 0, completed: efficiencyNumber(row.completed) ?? 0,
    api_concurrency_limit: efficiencyNumber(row.api_concurrency_limit), effective_api_limit: efficiencyNumber(row.effective_api_limit),
    longest_wait_ms: efficiencyNumber(row.longest_wait_ms), elapsed_ms: efficiencyNumber(row.elapsed_ms), diagnosis: efficiencyText(row.diagnosis),
    current_case: current ? { case_name: efficiencyText(current.case_name), stage: efficiencyText(current.stage), elapsed_ms: efficiencyNumber(current.elapsed_ms) } : null,
  }
}
const summaryFields = ['completed', 'p50_ms', 'p95_ms', 'retry_count', 'retry_duration_ms', 'pending', 'running', 'report_count', 'longest_wait_ms', 'anomaly_count', 'covered_completed', 'api_completed', 'sample_count', 'reports_without_details'] as const
type Summary = { [K in typeof summaryFields[number]]: number | null }
export function parseEfficiencyOverview(value: unknown) {
  const row = efficiencyPayload(value), source = efficiencyObject(row.summary), workers = efficiencyObject(row.workers)
  if (!source) throw new Error('Invalid efficiency summary')
  const summary = Object.fromEntries(summaryFields.map(key => [key, efficiencyNumber(source[key])])) as Summary
  return {
    summary, count: efficiencyNumber(row.count) ?? 0, as_of: efficiencyText(row.as_of),
    workers: { online: efficiencyNumber(workers?.online), capacity: efficiencyNumber(workers?.capacity), running: efficiencyNumber(workers?.running) },
    items: rows(row.items).map(liveRow),
    basic: rows(row.basic).map(item => ({ type: efficiencyId(item.type), name: efficiencyText(item.name), total: efficiencyNumber(item.total) ?? 0, completed: efficiencyNumber(item.completed) ?? 0, pending: efficiencyNumber(item.pending) ?? 0, running: efficiencyNumber(item.running) ?? 0 })),
    trend: rows(row.trend).map(item => ({ time: efficiencyText(item.time), completed: efficiencyNumber(item.completed) ?? 0, p50_ms: efficiencyNumber(item.p50_ms), p95_ms: efficiencyNumber(item.p95_ms) })),
    phases: rows(row.phases).map(item => ({ name: efficiencyText(item.name), duration_ms: efficiencyNumber(item.duration_ms) })),
    slow_cases: rows(row.slow_cases).map(item => {
      if (!efficiencyText(item.trace_id)) throw new Error('Invalid efficiency trace identifier')
      return { ...ownership(item), trace_id: efficiencyText(item.trace_id), report_id: efficiencyId(item.report_id), detail_id: efficiencyId(item.detail_id), case_name: efficiencyText(item.case_name), started_at: efficiencyText(item.started_at), duration_ms: efficiencyNumber(item.duration_ms), dominant_phase: efficiencyText(item.dominant_phase) }
    }),
    slow_reports: rows(row.slow_reports).map(item => {
      if (efficiencyId(item.report_id) === null) throw new Error('Invalid efficiency report identifier')
      return { ...ownership(item), report_id: efficiencyId(item.report_id), name: efficiencyText(item.name), observed_span_ms: efficiencyNumber(item.observed_span_ms), first_start_delay_ms: efficiencyNumber(item.first_start_delay_ms), running: item.running === true, timing_complete: typeof item.timing_complete === 'boolean' ? item.timing_complete : null }
    }),
  }
}
export type EfficiencyOverview = ReturnType<typeof parseEfficiencyOverview>
export interface EfficiencyOption { value: EfficiencyId; label: string }
export function parseEfficiencyOptions(value: unknown): { items: EfficiencyOption[]; more: boolean } {
  const row = efficiencyPayload(value)
  if (!Array.isArray(row.items) || typeof row.has_more !== 'boolean') throw new Error('Invalid efficiency options')
  return { items: rows(row.items).map(item => { const id = efficiencyId(item.id); if (id === null) throw new Error('Invalid option identifier'); return { value: id, label: efficiencyText(item.name) } }), more: row.has_more }
}
export function efficiencyEnumOptions(value: unknown): EfficiencyOption[] {
  return (Array.isArray(value) ? value : []).flatMap(item => { const row = efficiencyObject(item), id = efficiencyId(row?.key); return id === null ? [] : [{ value: id, label: efficiencyText(row?.title) }] })
}
