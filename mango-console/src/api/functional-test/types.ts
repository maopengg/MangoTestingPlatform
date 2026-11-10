export interface ManualCaseBinding {
  id: number
  automation_type: number
  automation_case_id: number
  api_case: number | null
  ui_case: number | null
  automation_case_name: string | null
  optimize_status: number
}

export interface ManualCaseDetail {
  id: number
  title: string
  case_no: string
  priority: number
  precondition: string | null
  test_point: string
  test_data: string | null
  remark: string | null
  source_text: string | null
  change_status: number
  automation_impact_status: number
  bindings: ManualCaseBinding[]
}

export interface ManualCaseVersionSnapshot {
  case_no: string
  title: string
  priority: number
  test_types: number[]
  project_product_id: number | null
  project_product_name: string
  module_id: number | null
  module_path: string
  category_level_1: string
  category_level_2: string
  category_level_3: string
  owner_id: number | null
  owner_name: string
  scenario_layer: number
  scenario_type: number
  scenario_tags: string[]
  automation_status: string
  status: number
  automation_bindings: Array<{
    automation_type: number
    automation_case_id: number
    automation_case_name: string
    api_case_id: number | null
    ui_case_id: number | null
  }>
  precondition: string | null
  test_point: string
  expected_result: string | null
  remark: string | null
  test_steps: Array<{ action: string; expected: string }>
}

export interface ManualCaseVersion {
  id: number
  case: number
  version_no: number
  snapshot: Partial<ManualCaseVersionSnapshot>
  source: number
  source_name: string
  changed_by: { id: number; name?: string; username?: string } | null
  create_time: string
}

export interface ManualCaseUpdateAck {
  id: number
  version_no: number
  update_time: string
  project_product_id: number | null
  project_product_path: string
  module_id: number | null
  module_path: string
}

export interface ManualCaseBatchUpdateResult {
  updated?: ManualCaseUpdateAck[]
  conflicts?: Array<{ id: number; expected_version: number; current_version: number }>
}
