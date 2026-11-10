import { reportIdentifier, reportObject, reportPayload } from './report-overview'

type ResultEvidence = Record<string, unknown>
const resultKey = (value: unknown): string | null =>
  typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value)) ? String(value) : null

export interface ReportResultTarget {
  detailId: string
  caseType: 0 | 2
  source: {
    id: string | null
    parameter_id: string | null
    name: string
    case_type: 0 | 2
    status: number | string | null
    error_message: string
    test_suite_detail_id: string
    __caseSourceId: string
  }
}
export function reportResultTarget(value: unknown, fallbackType: string): ReportResultTarget | null {
  const row = reportObject(value), id = reportIdentifier(row?.test_suite_detail_id ?? row?.__caseSourceId)
  if (!row || id === null) return null
  const caseType = Number(row.case_type ?? fallbackType)
  if (caseType !== 0 && caseType !== 2) return null
  return { detailId: id, caseType, source: {
    id: resultKey(row.id), parameter_id: resultKey(row.parameter_id), name: text(row.name), case_type: caseType,
    status: typeof row.status === 'string' || typeof row.status === 'number' ? row.status : null,
    error_message: text(row.error_message), test_suite_detail_id: id, __caseSourceId: id,
  } }
}

export interface ReportResultOption {
  id: string
  attempt_no: number
  status_text: string
  update_time: string
  create_time: string
  trigger_user_name: string
  is_case_latest: boolean
  is_latest: boolean
  test_suite_detail_id: string | null
  source_scope_name: string
  source_scope: string
}
const text = (value: unknown) => typeof value === 'string' ? value : ''
export function parseReportResultOptions(response: unknown): ReportResultOption[] {
  const payload = reportPayload(response)
  if (!Array.isArray(payload)) throw new Error('执行记录格式不正确')
  const seen = new Set<string>()
  return payload.map(value => {
    const row = reportObject(value), id = reportIdentifier(row?.id)
    if (!row || id === null || seen.has(id)) throw new Error('执行记录标识不正确')
    seen.add(id)
    return {
      id, attempt_no: typeof row.attempt_no === 'number' && Number.isSafeInteger(row.attempt_no) ? row.attempt_no : 0,
      status_text: text(row.status_text), update_time: text(row.update_time), create_time: text(row.create_time),
      trigger_user_name: text(row.trigger_user_name), is_case_latest: row.is_case_latest === true,
      is_latest: row.is_latest === true, test_suite_detail_id: reportIdentifier(row.test_suite_detail_id),
      source_scope_name: text(row.source_scope_name), source_scope: text(row.source_scope),
    }
  })
}

export function parseReportResult(response: unknown, expectedId: string): ResultEvidence | null {
  const payload = reportPayload(response)
  if (payload === null) return null
  const row = reportObject(payload)
  if (!row || reportIdentifier(row.id) !== expectedId) throw new Error('报告明细不匹配')
  return row
}

function matchingChild(source: ResultEvidence, children: ResultEvidence[]): ResultEvidence | null {
  for (const field of ['parameter_id', 'id'] as const) {
    const id = resultKey(source[field])
    if (id !== null) {
      const match = children.find(child => resultKey(child[field]) === id)
      if (match) return match
    }
  }
  if (typeof source.name === 'string' && source.name) {
    return children.find(child => child.name === source.name) ?? null
  }
  return null
}

/** Result evidence is dynamic renderer input, never an editor draft or save payload. */
export function buildReportResult(sourceValue: unknown, detailValue: unknown, fallbackType: string): ResultEvidence {
  const source = reportObject(sourceValue) ?? {}
  const detail = reportObject(detailValue) ?? {}
  const children = Array.isArray(detail.children)
    ? detail.children.map(reportObject).filter((child): child is ResultEvidence => child !== null) : []
  // Preserve legacy report selection: parameter, row ID, name, then the first structured result.
  const matched = matchingChild(source, children) ?? children[0] ?? detail
  const caseType = Number(source.case_type ?? detail.type ?? fallbackType)
  const statusDetails = reportObject(matched.statusDetails)
  const base: ResultEvidence = {
    ...matched,
    case_type: caseType,
    name: matched.name || source.name || detail.case_name || detail.name,
    status: matched.status ?? source.status ?? detail.status,
    error_message: matched.error_message || statusDetails?.message || source.error_message || detail.error_message,
    test_suite_detail_id: detail.id ?? source.test_suite_detail_id,
    __caseSourceId: detail.id ?? source.__caseSourceId,
  }
  if (caseType !== 0) return base
  return {
    ...base,
    test_time: base.test_time ?? detail.test_time,
    test_object: base.test_object ?? detail.test_object,
    video_path: base.video_path ?? detail.video_path,
    cache_data: base.cache_data ?? detail.cache_data,
    data_factory_cache_data: base.data_factory_cache_data ?? detail.data_factory_cache_data,
    element_result_list: [base],
    children: [base],
  }
}
