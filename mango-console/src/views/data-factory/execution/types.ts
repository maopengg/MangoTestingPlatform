export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue }
export interface SourceInfo {
  source_type_name?: string
  executor_name?: string
  executor_username?: string
  case_owner_name?: string
  case_owner_username?: string
  case_name?: string
  case_id?: number
  scenario_id?: number
  template_id?: number
  source_id?: number | string
  ui_module_name?: string
  api_info_name?: string
  api_info_url?: string
  api_info_method_name?: string
  scenario_name?: string
  template_name?: string
}
export interface ExecutionRecord {
  id: number
  execution_no: string
  status: number
  cleanup_status: number
  stage: number
  source_info?: SourceInfo | null
  source_display?: string
  error_message?: string
  project_product?: { id: number; name?: string }
  module?: { id: number; name?: string; full_path?: string }
}
export interface SqlRecord {
  id: number
  source_stage: string
  status: string
  sql_text: string
  duration_ms: number | null
  is_slow?: boolean
  affected_rows?: number
  error_message?: string
  result_preview?: string
}
export interface CleanupSnapshot {
  rule?: { datasource_alias_id?: number }
  index?: string
  document_id?: string
}
export interface CleanupResult {
  snapshot_index?: number | null
  index?: string
  document_id?: string
  success?: boolean
  checked_at?: string
  error?: string
}
export interface ExecutionItem {
  id: number
  alias: string
  cleanup_status: number
  cleanup_order?: number
  primary_value?: JsonValue
  data?: JsonValue
  storage_snapshot?: {
    database_name?: string
    database_id?: number
    table_name?: string
    primary_key?: string
  }
  sql_executions?: SqlRecord[]
  cleanup_resources?: {
    sql_cleaned?: boolean
    snapshots?: CleanupSnapshot[]
    results?: CleanupResult[]
  }
}
export interface ExecutionDetail {
  execution: ExecutionRecord
  items?: ExecutionItem[]
  context?: JsonValue
  sql_executions?: SqlRecord[]
}
export interface CleanupResponse {
  fail?: number
  message?: string
}
export interface DetailHandle {
  open(record: ExecutionRecord): void
  close(): void
  refreshFor(id: number): void
}
