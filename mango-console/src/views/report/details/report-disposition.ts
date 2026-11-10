import { reportIdentifier, reportObject } from './report-overview'

export interface ReportDispositionRecord {
  id: string | null
  name: string
  status: number | null
  fail: number
  case_sum: number
  is_excluded: boolean
  failure_reason: string
  failure_description: string
  execution_control: { phase: string; requires_review: boolean | null } | null
}
export interface ReportDispositionDraft {
  is_excluded: boolean
  failure_reason: string
  failure_description: string
}
const text = (value: unknown) => typeof value === 'string' ? value : ''
const count = (value: unknown, fallback = 0) => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : fallback
export const emptyDispositionDraft = (): ReportDispositionDraft => ({ is_excluded: false, failure_reason: '', failure_description: '' })
export function reportDispositionRecord(value: unknown): ReportDispositionRecord | null {
  const row = reportObject(value)
  if (!row) return null
  const control = reportObject(row.execution_control)
  return {
    id: reportIdentifier(row.id), name: text(row.case_name) || text(row.name),
    status: typeof row.status === 'number' && Number.isFinite(row.status) ? row.status : null,
    fail: count(row.fail), case_sum: count(row.case_sum, 1), is_excluded: row.is_excluded === true,
    failure_reason: text(row.failure_reason), failure_description: text(row.failure_description),
    execution_control: control ? { phase: text(control.phase), requires_review: typeof control.requires_review === 'boolean' ? control.requires_review : null } : null,
  }
}
export function dispositionDraft(record: ReportDispositionRecord): ReportDispositionDraft {
  return { is_excluded: record.is_excluded, failure_reason: record.failure_reason, failure_description: record.failure_description }
}
export function dispositionPayload(draft: ReportDispositionDraft): ReportDispositionDraft {
  return { is_excluded: draft.is_excluded, failure_reason: draft.failure_reason || '', failure_description: draft.failure_description.trim() }
}
