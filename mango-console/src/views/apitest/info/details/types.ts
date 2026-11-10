export type ApiInfoId = number | string
export type ExtractionRow = { key: string; value: string }
export interface ApiInfoRecord {
  id: ApiInfoId
  name: string
  method: number | null
  url: string
  project_product: ApiInfoId | { id: ApiInfoId } | null
  protocol_type: string
  headers: Record<string, unknown> | unknown[] | null
  params: string | null
  is_text_params?: number
  body_type: string
  body_config: Record<string, unknown> | null
  sse_config: Record<string, unknown> | null
  mcp_config?: Record<string, unknown> | null
  posterior_json_path: ExtractionRow[]
  posterior_re: ExtractionRow[]
  posterior_func: string | null
  status?: number
}
export interface ApiResponseData {
  code?: number | string | null
  time?: number | string | null
  error_msg?: string
  url?: string
  headers?: Record<string, unknown>
  json?: unknown
  text?: string
  request_headers?: Record<string, unknown>
  request_params?: Record<string, unknown> | string | unknown[]
  request_body?: unknown
  request_protocol_type?: string
  request_body_type?: string
  response_mode?: string
  sse_events?: unknown[]
  ws_messages?: unknown[]
  ws_stop_reason?: string
  ws_close_code?: number
  ws_close_reason?: string
  grpc_full_method?: string
  grpc_status_code?: string | number
  grpc_status_details?: string
  grpc_initial_metadata?: unknown
  grpc_trailing_metadata?: unknown
  cache_all?: Record<string, unknown>
}
export interface ApiVersionSelection {
  kind: 'current' | 'revision'
  id: number
  label: string
  payload: Partial<ApiInfoRecord>
}
export type ApiInfoPatch = Partial<
  Pick<
    ApiInfoRecord,
    | 'method'
    | 'url'
    | 'headers'
    | 'params'
    | 'body_type'
    | 'body_config'
    | 'sse_config'
    | 'posterior_json_path'
    | 'posterior_re'
    | 'posterior_func'
  >
>
