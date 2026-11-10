import type { ApiCaseParameterPayload } from '@/types/api-test/case-parameter'
export type ConfigSearchTarget = {
  stepId?: string | number
  scenarioId?: string | number
  caseApiType?: string
  caseApiSonType?: string
  detailType?: string
  detailTab?: string
}

export type ConfigSearchDocument = ConfigSearchTarget & {
  location: string
  fieldLabel: string
  value: unknown
}

export type ConfigSearchMatch = ConfigSearchTarget & {
  location: string
  path: string
  preview: string
}

export type ApiCaseExecutionTraceQuery = {
  result_id?: number | string
  trace_id?: string
  test_suite_detail_id?: string | number
  case_id?: string | number
}

export type CaseEntityId = string | number
export type ScenarioEditorMode = 'create' | 'edit' | 'copy'
export interface CaseWorkspaceRecord {
  id: CaseEntityId
  name: string
  project_product: { id: CaseEntityId } | null
  front_custom: import('@/types/api-test/case').ApiKeyValueItem[]
  front_sql: import('@/types/api-test/case').ApiKeyValueItem[]
  front_headers: number[]
  front_public: number[]
  front_auth_config: number[]
  callback_checks: CallbackRuleDraft[]
  posterior_sql: import('@/types/api-test/case').ApiKeyValueItem[]
  parametrize?: import('@/types/api-test/case').ApiParametrizeSuite[]
  published_release_id?: number | null
  publication_status?: string
  scenario_description?: string | null
  update_time?: string | null
}
export interface ApiCaseStep {
  id: CaseEntityId
  case?: number | { id: number }
  case_sort?: number
  logical_id?: string
  pinned_api_info_revision?: number | null
  api_info: {
    id: CaseEntityId
    module?: CaseEntityId | { id: CaseEntityId } | null
    name?: string
    method?: number | string
    url?: string
    protocol_type?: string
    body_type?: string
  }
  execution_config?: { is_recovery?: boolean }
  runtime_result_outdated?: boolean
  status?: number
  error_message?: string | null
}
export interface ApiCaseScenario
  extends Omit<
    ApiCaseParameterPayload,
    | 'id'
    | 'body_config'
    | 'ass_json_all'
    | 'ass_schema'
    | 'sse_config'
    | 'result_data'
    | 'front_sql'
    | 'posterior_sql'
    | 'posterior_response'
    | 'posterior_response_text'
    | 'posterior_sleep'
    | 'ass_jsonpath'
    | 'ass_general'
    | 'ass_sql'
  > {
  id: number
  test_time?: string | null
  allow_failure?: boolean
  __formatted?: boolean
  __persistedHeaders?: number[]
  runtime_result_outdated?: boolean
  body_config?: {
    protocol_expectation?: { mode?: string; status_codes?: number[] }
    [key: string]: unknown
  } | null
  ass_json_all?: unknown
  ass_schema?: unknown
  sse_config?: Record<string, unknown> | null
  front_sql: import('@/types/api-test/case').ApiKeyValueItem[]
  posterior_sql: import('@/types/api-test/case').ApiKeyValueItem[]
  posterior_response: import('@/types/api-test/case').ApiKeyValueItem[]
  posterior_response_text: import('@/types/api-test/case').ApiKeyValueItem[]
  posterior_sleep?: number | string | null
  ass_jsonpath: import('@/types/api-test/case-parameter').ApiJsonPathAssertionItem[]
  ass_general: Array<
    Omit<import('@/types/api-test/case-parameter').ApiGeneralAssertionItem, 'value'> & {
      value: Partial<import('@/types/api-test/case-parameter').ApiGeneralAssertionValue>
    }
  >
  ass_sql: Array<
    Omit<import('@/types/api-test/case-parameter').ApiSqlAssertionItem, 'datasource_alias'> & {
      datasource_alias: number | null
    }
  >
  result_data?: {
    id?: number
    status?: number
    test_time?: string | null
    error_message?: string | null
    automatic_retry_condition?: boolean
    response?: { code: number; json?: unknown; text?: string | null; [key: string]: unknown } | null
    [key: string]: unknown
  } | null
  __assertion_verify_result?: import('@/types/api-test/case-parameter').ApiAssertionResult[] | null
  __assertion_verify_signature?: string | null
  __assertion_verify_stale?: boolean
  __assertion_compare_open?: boolean
}
export interface CaseGlobalOption {
  value: number
  name: string
  disabled: boolean
  envText: string
  statusText: string
  type?: number
  typeText?: string
  key?: string
  authType?: number
  authTypeText?: string
  testEnv?: number | string | null
  isCommonEnv?: boolean
}
export interface CaseAssertionMethod {
  value: string
  label: string
  children?: CaseAssertionMethod[]
}
export interface CaseResourceOptions {
  ass: CaseAssertionMethod[]
  textAss: CaseAssertionMethod[]
  caseHeadersList: number[]
  headers_list: Array<{ id: number; name?: string; key: string; value: string }>
  parameter_headers_list: Array<{ id: number; name?: string; key: string; value: string }>
  datasourceAliasOptions: Array<{ label: string; value: number; dbType: string }>
  publicOptions: CaseGlobalOption[]
  authConfigOptions: CaseGlobalOption[]
}

export interface ScenarioPatch {
  id: number
  changes: Record<string, unknown>
}

export interface CaseTrace {
  trace_id: string
  status: number
  duration_ms?: number
  started_at?: string
  finished_at?: string
  source_type: number
  worker_name?: string
}
export interface CaseTraceNode {
  id: string | number
  parent_step_id?: string | number | null
  step_type: string
  label: string
  status: number
  duration_ms?: number
  error_message?: string
  detail_ref_type?: string
  detail_ref_id?: string | number
  summary?: unknown
}

export interface CaseExecutionSummary {
  id: string | number
  create_time?: string
  test_env?: number | null
  test_env_name?: string
  status?: number
}
export interface CallbackCheckDraft {
  key: string
  type: string
  source: string
  field: string
  operator: string
  expected: unknown
  expected_text?: string
  general_editor?: boolean
  assertions?: Array<{
    group_name?: string
    group_logic?: string
    method: string
    value: Partial<import('@/types/api-test/case-parameter').ApiGeneralAssertionValue>
  }>
}
export interface CallbackRuleDraft {
  key: string
  name: string
  enabled: boolean
  trigger_step_key: string
  mock_config_id?: number
  correlation: { source: string; field: string; expected: { cache_key: string } }
  timeout_seconds: number
  observation_seconds: number
  max_deliveries: number
  min_deliveries: number
  min_retry_interval_ms: number
  max_retry_interval_ms: number | null
  events: { mode: string; count: number }
  event_id_source: string
  event_id_field: string
  delivery_policy: string
  response_mode: string
  failure_status: number
  checks: CallbackCheckDraft[]
}
export interface CallbackDelivery {
  id: number
  passed?: boolean
  evidence_complete?: boolean
  evidence_expired?: boolean
  body_sha256?: string
  body_length?: number
  raw_body?: string
  business_body?: string
  transport_headers?: Record<string, unknown>
  checks?: Array<{
    key: string
    passed: boolean
    diagnostic?: boolean
    message?: string
    assertions?: import('@/types/api-test/case-parameter').ApiAssertionResult[]
  }>
}
