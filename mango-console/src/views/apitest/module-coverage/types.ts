export type CoverageTab = 'overview' | 'interfaces' | 'cases' | 'scans'
export interface CoverageModule {
  id: number
  name?: string
  full_path?: string
  parent?: CoverageModule | null
}
export interface CoverageProduct {
  id: number
  name: string
  project?: { id: number; name: string }
}
export interface CodeEvidence {
  path?: string
  symbol?: string
  start_line?: number
  end_line?: number
}
export interface CoveragePayload {
  test_scenario?: string
  core_assertion?: string
  scenario_assertion?: string
  preconditions?: string
  data_strategy?: string
  cleanup_strategy?: string
  remark?: string
  code_evidence?: string | CodeEvidence[]
}
export interface CoverageRecord extends CoveragePayload {
  id: number
  key?: string
  name?: string
  status?: string
  source_key?: string
  repository_key?: string
  repository_name?: string
  branch?: string
  method?: string
  url?: string
  interface_name?: string
  module?: CoverageModule | null
  owner_module?: CoverageModule | null
  project_product?: CoverageProduct | null
  module_id?: number
  project_product_id?: number
  interface_source_key?: string
  coverage_interface?: number
  payload?: CoveragePayload
  api_case?: number | null
  api_case_name?: string
  legacy_scenario_assertion?: string
  test_ownership?: string
  scenario_layer?: number
  scenario_type?: number
  scenario_tags?: string[]
  node_ids?: string[]
  branch_ids?: string[]
  current_commit?: string
  commit_sha?: string
  base_commit_sha?: string
  scan_mode?: string
  scope_type?: string
  target_interface?: number
  expected_case_count?: number
  summary?: Record<string, number>
  update_time?: string
  finished_at?: string
  coverage_policy?: string
  coverage_reason?: string
  coverage_validity?: string
  coverage_validity_reason?: string
  coverage_rate?: number
  coverage_status?: string
  analysis_status?: string
  analysis_reason?: string
  analysis_commit_sha?: string
  latest_inventory_commit_sha?: string
  resolution_status?: string
  resolution_reason?: string
  lifecycle_status?: string
  api_info_id?: number
  api_info_binding_status?: string
  api_info_binding_reason?: string
  latest_scan_id?: number
  first_scan_id?: number
  latest_commit_sha?: string
  sync_action?: string
  change_status?: string
  execution_result?: string
  case_count?: number
  effective_completed_case_count?: number
  target_case_count?: number
  completed_case_count?: number
  deferred_case_count?: number
  effective_valid_case_count?: number
  effective_pending_review_case_count?: number
  effective_invalid_case_count?: number
  mermaid?: string
  cases?: CoverageRecord[]
}
export interface CoverageSnapshot {
  id: number
  scan?: number
  commit_sha?: string
  sync_action?: string
  create_time?: string
  content_hash?: string
  payload?: CoveragePayload
  method?: string
  url?: string
  mermaid?: string
  resolution_status?: string
}
export interface CoverageDiff {
  current?: CoverageSnapshot | null
  previous?: CoverageSnapshot | null
}
export interface ScanValidation {
  received_interface_count?: number
  expected_interface_count?: number
  received_case_count?: number
  expected_case_count?: number
  resolved_interface_count?: number
  placeholder_interface_count?: number
  gap_interface_count?: number
  blocking_errors?: string[]
  gap_errors?: string[]
  unresolved_interface_sample_limit?: number
  unresolved_interfaces?: Array<{
    status: string
    source_key: string
    reason: string
    next_action?: string
    resumption_point?: string
  }>
}
export interface ScanUploadStatus {
  count?: number
  items?: Array<{ source_key: string; sync_action: string }>
  interface_items?: Array<{ source_key: string; sync_action: string }>
}
export interface CoverageFilters {
  repository_key: string
  branch: string
  name: string
  interface_name: string
  coverage_reason: string
  api_info_id?: number
  status?: string
  change_status?: string
  coverage_validity?: string
  interface_status?: string
  api_info_binding_status?: string
  coverage_policy?: string
  scenario_layer?: number
  scenario_type?: number
  scenario_tag?: string
  resolution_statuses: string[]
  analysis_statuses: string[]
  coverage_statuses: string[]
  sync_actions: string[]
  methods: string[]
}
export type CoverageMultiFilter =
  | 'resolution_statuses'
  | 'analysis_statuses'
  | 'coverage_statuses'
  | 'sync_actions'
  | 'methods'
