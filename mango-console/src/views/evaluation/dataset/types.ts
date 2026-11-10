import type { GraderBinding, InputVariable, ParameterSchema } from '../types'

export interface EvaluationDatasetRecord {
  id: number
  name: string
  task_type: string[] | string | null
  status: string
  description?: string | null
  current_version?: number | null
  version_count?: number
  item_count?: number
  update_time?: string | null
}

export interface EvaluationDatasetRow extends Omit<EvaluationDatasetRecord, 'task_type'> {
  task_type: string[]
}

export interface DatasetFilters {
  name: string
  task_type: string[]
  status: string[]
}

export interface DatasetForm {
  id: number | null
  name: string
  description: string
  task_type: string[]
  status: string
}

export interface DatasetWorkflow {
  preparation: string
  sequence: string
  steps: unknown[]
  bindings: unknown[]
}

export interface DatasetSchemaSnapshot {
  schema_version?: number
  input_schema?: ParameterSchema
  expected_schema?: ParameterSchema
  context_schema?: ParameterSchema
  input_variables?: InputVariable[]
  workflow?: DatasetWorkflow
}

export interface DatasetVersion {
  id: number
  status: string
  version_no?: number
  version_label?: string
  item_count?: number
  published_at?: string | null
  schema_snapshot?: DatasetSchemaSnapshot
}

export interface DatasetConfiguration extends DatasetSchemaSnapshot {
  input_variables: InputVariable[]
  workflow: DatasetWorkflow
}

export interface DatasetScenarioTurn {
  kind?: string
  name: string
  input_data: unknown
  expected_output: unknown
  context: unknown
  score: boolean
}

export interface DatasetItemScenario {
  group_key: string
  order: number | undefined
  turns: DatasetScenarioTurn[]
}

export interface DatasetSourceBinding {
  resource: string
  project_product_id?: number
  ref_id?: number
  name?: string
  revision_id?: number | null
  content_hash?: string
  target_ref_id?: number | null
}

export interface DatasetItemSource {
  kind: string
  binding?: DatasetSourceBinding | null
  module_id?: number | null
  query?: string
  key?: string
  parameters?: unknown
  variables?: InputVariable[]
  timeout_seconds?: number
}

export interface DatasetItemGrading {
  schema_version: number
  mode: string
  graders: GraderBinding[]
}

export interface DatasetItem {
  id: number
  input_data: unknown
  expected_output: unknown
  context?: unknown
  tags?: string[]
  priority?: string
  weight?: number
  enabled: boolean
  grading_config?: DatasetItemGrading
  scenario?: DatasetItemScenario
  data_source?: DatasetItemSource
}

export interface DatasetItemForm {
  id: number | undefined
  version_id: number | null
  input_text: string
  expected_text: string
  context_text: string
  tags_text: string
  priority: string
  weight: number | undefined
  enabled: boolean
  grading_config: DatasetItemGrading
  scenario: DatasetItemScenario
  data_source: DatasetItemSource
}

export interface DatasetQualityIssue {
  key: string
  message: string
  item_id?: number
  count?: number
  groups?: number[][]
}

export interface DatasetQualityReport {
  item_count?: number
  enabled_count?: number
  missing_expected_count?: number
  errors?: DatasetQualityIssue[]
  warnings?: DatasetQualityIssue[]
  warning_acknowledged?: boolean
}
