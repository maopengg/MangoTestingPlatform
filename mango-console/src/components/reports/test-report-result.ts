import { historyId, historyObject, historyResponse, historyText } from '../business/execution-history'

export interface FailureResultOption {
  id: string | number
  label: string
  status_text: string
  update_time: string
  create_time: string
  trigger_user_name: string
  is_case_latest: boolean
  is_latest: boolean
  detailId: string | number | null
  source_scope_name: string
}
export function failureResultOptions(response: unknown): FailureResultOption[] {
  const rows = historyResponse(response), seen = new Set<string>()
  if (!Array.isArray(rows)) throw new Error('Invalid result history')
  return rows.map(value => {
    const row = historyObject(value), id = historyId(row?.id)
    if (!row || id === null || seen.has(String(id))) throw new Error('Invalid result history identifier')
    seen.add(String(id))
    return {
      id, label: historyText(row.label), status_text: historyText(row.status_text),
      update_time: historyText(row.update_time), create_time: historyText(row.create_time),
      trigger_user_name: historyText(row.trigger_user_name), is_case_latest: row.is_case_latest === true,
      is_latest: row.is_latest === true, detailId: historyId(row.test_suite_detail_id),
      source_scope_name: historyText(row.source_scope_name),
    }
  })
}
export interface FailureResultTarget {
  detailId: number | string
  caseType: 0 | 1 | 2
  caseId: number | string | null
  caseName: string
  fallbackError: string
}
export function failureResultTarget(value: unknown): FailureResultTarget | null {
  const row = historyObject(value), detailId = historyId(row?.testSuiteDetailId)
  const type = row?.caseType
  const caseType = type === 0 || type === '0' ? 0 : type === 1 || type === '1' ? 1 : type === 2 || type === '2' ? 2 : null
  return row && detailId !== null && caseType !== null ? {
    detailId, caseType, caseId: historyId(row.caseId), caseName: historyText(row.caseName), fallbackError: historyText(row.fallbackError),
  } : null
}

/** Dynamic evidence is read-only renderer input, never an editor or request payload. */
export function failureResultRecord(response: unknown, target: FailureResultTarget): Record<string, unknown> | null {
  const payload = historyResponse(response)
  if (payload === null) return null
  const detail = historyObject(payload)
  if (!detail || String(historyId(detail.id)) !== String(target.detailId)) throw new Error('Invalid result detail scope')
  const children = Array.isArray(detail.children) ? detail.children.map(historyObject).filter((row): row is Record<string, unknown> => row !== null) : []
  const matched = children[0] ?? historyObject(detail.children) ?? detail
  const base: Record<string, unknown> = {
    ...matched, case_type: target.caseType,
    name: historyText(matched.name) || target.caseName || historyText(detail.case_name) || historyText(detail.name),
    status: matched.status ?? detail.status,
    error_message: historyText(matched.error_message) || historyText(historyObject(matched.statusDetails)?.message) || historyText(detail.error_message) || target.fallbackError,
    test_suite_detail_id: target.detailId,
  }
  if (target.caseType !== 0) return base
  return {
    ...base, test_time: base.test_time ?? detail.test_time,
    test_object: base.test_object ?? detail.test_object, video_path: base.video_path ?? detail.video_path,
    cache_data: base.cache_data ?? detail.cache_data,
    data_factory_cache_data: base.data_factory_cache_data ?? detail.data_factory_cache_data,
    element_result_list: [base], children: [base],
  }
}
