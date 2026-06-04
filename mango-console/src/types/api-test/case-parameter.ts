import type { ApiKeyValueItem, JsonObject, JsonValue } from './case'

export interface ApiJsonPathAssertionItem {
  actual: string
  method: string
  expect: string
}

export interface ApiSqlAssertionItem {
  actual: string
  method: string
  expect: string
  datasource_alias?: number | null
}

export interface ApiGeneralAssertionParameter {
  d: boolean
  f: string
  n: string
  p: string
  v: string
}

export interface ApiGeneralAssertionValue {
  label?: string | null
  value: string
  parameter: ApiGeneralAssertionParameter[]
}

export interface ApiGeneralAssertionItem {
  method: string
  value: ApiGeneralAssertionValue
}

export interface ApiRequestFileItem {
  key: string
  value: unknown
}

export interface ApiCaseParameterPayload {
  id?: number
  case_detailed?: number | string
  api_info?: number | string
  error_retry?: number | null
  retry_interval?: number | null
  name?: string
  headers?: number[]
  is_case_headers?: number
  params?: string | null
  data?: string | null
  json?: string | null
  file?: ApiRequestFileItem[] | JsonObject | null
  front_sql?: ApiKeyValueItem[]
  front_func?: string | null
  ass_general?: ApiGeneralAssertionItem[]
  ass_sql?: ApiSqlAssertionItem[]
  ass_json_all?: JsonObject | JsonValue[] | null
  ass_text_all?: string | null
  ass_jsonpath?: ApiJsonPathAssertionItem[]
  ass_schema?: JsonObject | null
  posterior_sql?: ApiKeyValueItem[]
  posterior_response?: ApiKeyValueItem[]
  posterior_response_text?: ApiKeyValueItem[]
  posterior_sleep?: number | null
  posterior_file?: ApiKeyValueItem[] | null
  posterior_func?: string | null
  status?: number
  result_data?: ApiCaseStepResult | JsonObject | null
}

export interface ApiCaseParameterQuery {
  id?: number | string
  case_detailed_id?: number | string
  page?: number
  pageSize?: number
  [key: string]: unknown
}

export interface ApiRequestResult {
  method?: string | null
  url?: string | null
  headers?: JsonObject | null
  params?: JsonObject | JsonValue[] | string | null
  data?: JsonObject | JsonValue[] | null
  json?: JsonObject | JsonValue[] | null
  file?: ApiRequestFileItem[] | JsonObject | string | null
  posterior_file?: string | null
}

export interface ApiResponseResult {
  code: number
  time: number
  request_headers?: JsonObject | null
  request_params?: JsonObject | JsonValue[] | string | null
  request_data?: JsonObject | JsonValue[] | null
  request_json?: JsonObject | JsonValue[] | null
  request_file?: ApiRequestFileItem[] | JsonObject | string | null
  headers: JsonObject
  json?: JsonObject | JsonValue[] | null
  text?: string | null
  error_msg?: string | null
}

export interface ApiAssertionResult {
  method: string
  expect?: unknown
  actual?: unknown
  ass_msg?: string | null
  status: number
}

export interface ApiCaseStepResult {
  id: number
  name: string
  status: number
  error_message?: string | null
  test_time?: string | null
  api_info_id: number
  ass?: ApiAssertionResult[] | null
  request: ApiRequestResult
  response?: ApiResponseResult | null
  cache_data: JsonObject
  data_factory_cache_data: JsonObject
}
