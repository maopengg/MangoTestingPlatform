export interface EvaluationCaseRecord {
  id: number
  name: string
  description?: string
  status: string
  project_product?: number
  project_product_data?: { id: number; name: string }
  module?: number | null
  module_data?: { id: number; name: string; full_path?: string } | null
  owner_name?: string | null
  dataset_id?: number | null
  dataset_name?: string | null
  dataset_version?: number | null
  dataset_version_no?: number | null
  dataset_input_variables?: InputVariable[]
  dataset_workflow_summary?: unknown
  create_time?: string
  update_time?: string
  config?: CaseConfig
}

export interface GraderCatalogEntry {
  grader_key: string
  grader_version: number
  name: string
  category?: string
  description?: string
  parameters_schema?: ParameterSchema
}

export interface ParameterSchema {
  type?: string
  title?: string
  default?: unknown
  enum?: unknown[]
  additionalProperties?: boolean | ParameterSchema
  description?: string
  minimum?: number
  maximum?: number
  properties?: Record<string, ParameterSchema>
  items?: ParameterSchema
  required?: string[]
  anyOf?: ParameterSchema[]
}

export interface GraderBinding {
  grader_key: string
  grader_version: number
  metric_key: string
  threshold: number | undefined
  weight: number | undefined
  hard_gate: boolean
  enabled: boolean
  parameters: Record<string, unknown>
}
export interface QualityGate {
  key: string
  metric_key?: string
  operator: string
  threshold: number | undefined
  severity: string
  group_by?: string | null
}
export interface CaseConfig {
  schema_version: number
  ai: {
    judge_profile_id: string | null
    summary_profile_id: string | null
    answer_profile_id: string | null
  }
  data_selection: { exclude: boolean; item_ids: number[] }
  target: {
    type: string
    ref_id: number | null
    version_ref: { kind: string; id: number } | null
    parameters: { code?: string }
  }
  mapping: { output: { paths: string[] } }
  grading: {
    default_graders: GraderBinding[]
    required_graders: GraderBinding[]
    aggregation: {
      policy_version: number
      min_valid_rate: number | null
      min_effect_pass_rate: number | null
    }
    quality_gates: QualityGate[]
  }
  execution: {
    max_concurrency: number | undefined
    item_timeout_seconds: number | undefined
    retry_count: number | undefined
    repeat_count: number | undefined
    stop_on_critical_failure: boolean
  }
  answering?: { question_path: string; max_tokens: number | undefined } | null
}
export type RelationSelection = number | number[] | null | undefined
export interface CaseForm {
  id?: number
  name: string
  description: string
  project_product: RelationSelection
  module: RelationSelection
  dataset_id?: number | null
  dataset_version?: number | null
  status: string
}
export interface InputVariable {
  name: string
  path: string
}
export interface DatasetOption {
  id: number
  name: string
}
export interface DatasetVersionOption {
  id: number
  version_no?: number | null
  version_label?: string
  status: string
  schema_snapshot?: { input_variables?: InputVariable[]; workflow?: unknown }
}
export interface AiProfileOption {
  id: string
  name: string
  model?: string
  enabled: boolean
  disabled_reason?: string
}
export interface InterfaceOption {
  id: number
  name: string
  protocol_type: string
  published: boolean
  module_id?: number
}
export interface EvaluationRows<T> {
  data: T[] | { items?: T[]; count?: number }
  totalSize?: number
}
export interface DatasetItemOption {
  id: number
  enabled: boolean
  input_data: unknown
  expected_output: unknown
}

export interface GradingPreview {
  items?: Array<{ item_id: number; graders?: GraderBinding[] }>
}

export interface WorkflowRecord {
  name: string
  stage: string
  scope: string
  status: string
  duration_ms?: number
  error_message?: string | null
  output?: unknown
}
export interface ExecutionSummary {
  total?: number
  valid?: number
  failed?: number
  invalid?: number
  warning?: number
  effect_pass_rate?: number | null
  average_score?: number | null
  memory_qa?: { counts: Record<string, number>; rates: Record<string, number> }
  ai_summary?: {
    status: string
    overview?: string
    findings?: string[]
    recommendations?: string[]
    error_message?: string
  }
}
export interface ExecutionRecord {
  id: number
  execution_no: string
  status: string
  test_env: number
  verdict: string
  progress?: number
  create_time?: string
  summary?: ExecutionSummary
  snapshot?: {
    dataset?: { id?: number; version_no?: number }
    selection?: { scope?: string }
    grader_bindings?: Record<string, GraderBinding>
  }
  details?: { error_message?: string; workflow?: WorkflowRecord[] }
}
export interface MemoryFactCheck {
  index: number
  status: string
  reason?: string
  actual_quote?: string
  source_quote?: string
}
export interface ItemGrade {
  grader_key: string
  passed: boolean
  score?: number | null
  reason?: string
  grading_snapshot?: { metric?: string }
  raw_value?: {
    classification?: string
    evidence?: { answer_quote?: string; reference_quote?: string }
    expected_checks?: MemoryFactCheck[]
    actual_checks?: MemoryFactCheck[]
  }
}
export interface ItemResult {
  id: number
  dataset_item_id: number
  repeat_index: number
  execution_status: string
  grade_status: string
  verdict: string
  score?: number | null
  error_category?: string
  attempts?: unknown[]
  actual_output?: unknown
  resolved_expected_output?: unknown
  details?: {
    timing?: { execution_ms?: number | null }
    error_message?: string
    cleanup_error?: string
    workflow?: WorkflowRecord[]
    turns?: Array<{
      index: number
      name?: string
      scored?: boolean
      score?: number | null
      input?: unknown
      expected?: unknown
      output?: unknown
      verdict?: string
      context?: { source_evidence?: unknown }
    }>
  }
  item_snapshot?: {
    input_data?: unknown
    context?: { source_evidence?: unknown }
    effective_graders?: Array<{ binding_hash: string }>
  }
  grades?: ItemGrade[]
}
export interface ResultPage<T> {
  data?: { items?: T[]; count?: number }
}

export interface CaseEditorHandle {
  open(id?: number, product?: RelationSelection, module?: RelationSelection): Promise<void>
  flush(): Promise<boolean>
  scrollToStep(key: string): void
  saving: boolean
  loading: boolean
  ready: boolean
  dirty: boolean
  saveError: string
  saveStatus: string
}

export interface CaseListRecord extends EvaluationCaseRecord {
  target_type?: string
  latest_result?: {
    id: number
    status: string
    finished_at?: string | null
    average_score?: number | null
    valid_rate?: number | null
  } | null
}
export interface CaseFilters {
  name: string
  status: string[]
  target_type: string[]
  project_product: number | null
  module: number | null
}
export interface CaseNavigationFilter {
  projectProduct: string | number | null
  module: string | number | null
  moduleIds?: Array<string | number>
}
