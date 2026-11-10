import { get, post } from '@/api/http'
import request from '@/api/axios.config'

export interface ExecutionResultQuery {
  source_type?: string
  target_type: string
  target_id?: number | string
  test_suite_id?: number | string
  test_suite_detail_id?: number | string
  revision_id?: number | string | null
  revision_id_isnull?: boolean | number | string
  release_id?: number | string | null
  test_env?: number | string | null
  page?: number
  pageSize?: number
}

export function getExecutionResultList(data: ExecutionResultQuery) {
  return get({
    url: 'system/execution/result/list',
    data: () => data,
  })
}

export function getExecutionResultDetail(id: number | string) {
  return get({
    url: 'system/execution/result/detail',
    data: () => ({ id }),
  })
}

export function getExecutionResultLatest(data: ExecutionResultQuery, silentError = false) {
  return get({
    url: 'system/execution/result/latest',
    silentError,
    data: () => data,
  })
}

export interface AssertionAiAnalysisResult {
  available: boolean
  reason: string
  summary: string
  failed_count: number
  analyzed_count: number
  omitted_count: number
  items: Array<{
    assertion_index: number
    explanation: string
    next_check: string
  }>
}

export function postAssertionAiAnalysis(assertions: Record<string, unknown>[]) {
  return post<AssertionAiAnalysisResult>({
    url: 'system/execution/result/assertion/ai-analysis',
    data: () => ({ assertions }),
  })
}

export interface ApiCaseDiagnosisPreview {
  result_id: number
  case_id: number
  test_env: number | null
  revision_id: number | null
  release_id: number | null
  create_time: string
  status: number
  error_message: string
  evidence_level: 'result' | 'trace' | 'none'
  units: Array<{
    unit_index: number
    step_id: number
    parameter_id: number | null
    retry_index: number | null
    name: string
    status: number
    error_message: string
    failure_category: string
    http_status: number | null
  }>
  failed_count: number
  can_analyze: boolean
}

export interface ApiCaseDiagnosisResult {
  available: boolean
  reason: string
  result_id: number
  scope_used: string
  included_unit_count: number
  omitted_unit_count: number
  evidence_level: string
  focus_index: number
  analysis?: {
    location: string
    cause: string
    evidence: string[]
    next_check: string
    confidence: 'high' | 'medium' | 'low'
  }
}

export function getApiCaseDiagnosisPreview(resultId: number | string) {
  return get<ApiCaseDiagnosisPreview>({
    url: 'system/execution/result/case/ai-preview',
    data: () => ({ result_id: resultId }),
  })
}

export function postApiCaseDiagnosis(data: {
  result_id: number | string
  scope: 'auto' | 'focus' | 'all'
  focus_index?: number
}) {
  return post<ApiCaseDiagnosisResult>({
    url: 'system/execution/result/case/ai-analysis',
    data: () => data,
  })
}

export interface ExecutionResultAdminQuery {
  id?: number | string
  id__in?: string
  source_type?: string
  source_type__in?: string
  target_type?: string
  target_type__in?: string
  target_id?: number | string
  status?: number | string
  status__in?: string
  test_env?: number | string
  test_env__in?: string
  trigger_user_id?: number | string
  trigger_user_id__in?: string
  result_state?: 'available' | 'cleaned' | 'empty' | string
  result_state__in?: string
  is_latest?: boolean | string
  trace_id?: string
  task_id?: string
  error_message?: string
  create_time_start?: string
  create_time_end?: string
  page?: number
  pageSize?: number
}

export function getExecutionResultAdminList(data: ExecutionResultAdminQuery) {
  return get({
    url: 'system/execution/result/admin/list',
    data: () => data,
  })
}

export function getExecutionResultAdminConfig() {
  return get({
    url: 'system/execution/result/admin/config',
    data: () => ({}),
  })
}

export function postExecutionResultAdminCleanup() {
  return post({
    url: 'system/execution/result/admin/cleanup',
    data: () => ({}),
  })
}

export async function getExecutionResultDetailResolved(id: number | string) {
  const res = await getExecutionResultDetail(id)
  return resolveExecutionResultResponse(res)
}

export async function getExecutionResultLatestResolved(data: ExecutionResultQuery, silentError = false) {
  const res = await getExecutionResultLatest(data, silentError)
  return resolveExecutionResultResponse(res, silentError)
}

async function resolveExecutionResultResponse(res: any, silentError = false) {
  const detail = res.data || null
  if (detail?.result_too_large && detail?.id) {
    const response = await request.get('system/execution/result/content', {
      params: { id: detail.id },
      responseType: 'json',
      ...(silentError ? { silentError: true } : {}),
    })
    detail.result_data = response.data
    detail.result_too_large = false
  }
  return {
    ...res,
    data: detail,
  }
}
