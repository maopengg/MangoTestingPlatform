export interface PerformanceGoal {
  p95_ms: number
  error_rate_percent: number
  load_achievement_rate_percent: number
}

export type PerformanceGoalTemplateKey = 'recommended' | 'custom'

export interface PerformanceGoalPayload {
  template_key: PerformanceGoalTemplateKey
  p95_ms: number
  max_error_rate: number
  min_load_achievement_rate: number
}

export type LoadType = 'concurrency' | 'arrival_rate' | 'iteration_rate'
export type LoadProfile = 'constant_concurrency' | 'fixed_iterations' | 'staircase' |
  'linear_ramp' | 'spike' | 'soak' | 'constant_arrival_rate' | 'constant_iteration_rate'

export interface LoadConfiguration {
  name: string
  profile: LoadProfile
  duration_seconds: number | null
  target_users: number | null
  target_rate: number | null
  rate_time_unit: 'second' | 'minute' | null
  preallocated_vus: number | null
  max_vus: number | null
  ramp_type: 'linear' | 'step'
  spawn_rate: number | null
  user_wait_min_ms: number | null
  user_wait_max_ms: number | null
  total_iterations: number | null
  start_users: number | null
  step_users: number | null
  step_interval_seconds: number | null
  ramp_seconds: number | null
  hold_seconds: number | null
  baseline_seconds: number | null
  recovery_seconds: number | null
}

export interface LoadConfigurationChange {
  loadType: LoadType
  configuration: LoadConfiguration
}

// Arco 数值框清空返回 undefined，API 中未适用字段使用 null。
export type LoadConfigurationDraft = {
  [Key in keyof LoadConfiguration]: Exclude<LoadConfiguration[Key], null> |
    (null extends LoadConfiguration[Key] ? undefined : never)
}

export interface ScenarioExecutionDraft {
  test_env: number | undefined
  selected_executor_fingerprints: string[]
  remark: string
  production_load_confirmed: boolean
  capture_request: boolean
  capture_response: boolean
}

export interface ExecutorCandidate {
  fingerprint: string
  executor_name: string
  available: number
  calibrated: boolean
}

export interface ExecutorPreflight {
  can_run: boolean
  capacity_type: 'vu' | 'rps'
  required_per_node: number
  requested_node_count: number
  candidates: ExecutorCandidate[]
  selected: ExecutorCandidate[]
}

export interface ScenarioScriptPreview {
  scenario_version: number
  snapshot_hash: string
  script: string
  snapshot: string
}

export type ScriptPreviewTab = 'script' | 'snapshot'

export interface ScenarioForm {
  name: string
  engine: 'k6'
  project_product: number | null
  version: number | null
  source_case_release_id: number | undefined
  default_executor_count: number | undefined
  node_failure_policy: 'strict' | 'continue'
  min_ready_nodes: number | undefined
  load_type: LoadType
}

export interface SourceCaseStep {
  key: string
  name: string
  api_info_id: number | null
  extractor_count: number
  check_count: number
}

export interface SourceCaseRelease {
  release_id: number
  case_id: number
  name: string
  title: string
  disabled: boolean
  compatible: boolean
  incompatible_reasons: string[]
  version_label: string
  revision_no: number
  module_full_path: string
  steps: SourceCaseStep[]
}

export interface ScenarioConfigurationRecord {
  id: number
  form: ScenarioForm
  load: LoadConfiguration
  source: SourceCaseRelease | null
  goal: PerformanceGoal
  goalTemplate: PerformanceGoalTemplateKey
}

export type PerformanceGoalDraft = { [Key in keyof PerformanceGoal]: number | undefined }
