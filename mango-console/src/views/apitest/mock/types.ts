export interface MockLogAssertion {
  key?: string
  name?: string
  field?: string
  message?: string
  passed?: boolean
  operator?: string
  [key: string]: unknown
}
export interface MockLogRecord {
  id: number | string
  create_time?: string
  error_message?: string
  assertion_passed?: boolean
  assertion_results?: MockLogAssertion[]
  method_name?: string
  response_status?: number
  request_path?: string
  trace_id?: string
  rule_key?: string
  duration_ms?: number
  client_ip?: string
  request_data?: { query?: unknown; headers?: unknown; body?: unknown }
  response_data?: { content_type?: string; headers?: unknown; body?: unknown }
}
export type MockEntityId = number | string
export interface MockListRecord {
  id: number
  name: string
  mock_key: string
  path: string
  method: number
  method_name: string
  enabled: boolean
  record_call_log: boolean
  update_time?: string
  update_user?: { id: MockEntityId; name: string } | null
  project_product: {
    id: MockEntityId
    name: string
    project?: { id: MockEntityId; name: string }
  } | null
}
export interface MockFilters {
  project_product: MockEntityId | MockEntityId[] | null
  id: string
  name: string
  mock_key: string
  method: number[]
  enabled: number[]
  record_call_log: number[]
}
export interface MockStatePatch {
  enabled?: boolean
  record_call_log?: boolean
}
