export interface DefectUserOption {
  key: string | number
  title: string
}

export interface DefectActionSubject {
  id: number
  status: number
  defect_no: string
  assignee?: { id: number } | null
  resolution?: number | null
  resolution_note?: string | null
  environment?: string | null
}

export interface DefectTransitionSubject {
  id: number
  currentStatus: number
  assignee: number | null
  resolution: number | null
  resolution_note: string
}

export interface DefectTransitionForm {
  status: number | null
  assignee: string | number | null
  resolution: string | number | null
  resolution_note: string
}

export interface DefectMutationResult {
  id: number
}

export interface DefectTransitionHandle {
  open: (record: DefectActionSubject, target?: number) => void
  isSaving: (id: number) => boolean
}

export interface DefectRetestHandle {
  open: (record: DefectActionSubject) => void
  isSaving: (id: number) => boolean
}

export type DefectSelection = string | number | null
export type DefectProductSelection = DefectSelection | Array<string | number>
export interface DefectStep {
  sort: number
  action: string
  expected: string
  actual: string
}
export interface DefectForm {
  id: number | null
  title: string
  project_product: DefectProductSelection
  module: DefectSelection
  requirement_version: number | null
  source_type: number
  defect_type: number
  severity: number
  priority: number
  description: string
  precondition: string
  reproduce_steps: DefectStep[]
  expected_result: string
  actual_result: string
  environment: string
  attachment_file_ids: number[]
  assignee: DefectSelection
  case_ids: number[]
  source_plan_id: DefectSelection
  plan_case_ids: number[]
}
export interface DefectRelation {
  id: number
  case: number | null
  plan_case: number | null
  case_no: string
  case_title: string
  plan_id: number | null
  plan_name: string
  result: number | null
  executor_name: string
  execute_time: string
}
export interface DefectMetadata {
  defect_no: string
  status: number | null
  reporter_name: string
  create_time: string
  update_time: string
  resolution: number | null
  resolution_note: string
  resolved_at: string
  closed_at: string
  relations: DefectRelation[]
}
export interface DefectCaseChoice {
  id: number
  case_no: string
  title: string
  module_id: number | null
  precondition: string
  test_steps: Array<{ action: string; expected: string }>
  expected_result: string
  actual_result: string
}
export interface DefectPlanChoice {
  value: number
  label: string
  environment: string
}
export interface DefectRouteSeed {
  projectProduct: number
  requirementVersion: number | null
  planId: number | null
  planCaseIds: number[]
  caseIds: number[]
}
export interface DefectEditorHandle {
  isSaving: (id: number) => boolean
  open: (
    record?: unknown,
    defaults?: { projectProduct: DefectSelection; module: DefectSelection }
  ) => Promise<void>
  openById: (id: number) => Promise<void>
  openFromRoute: (seed: DefectRouteSeed) => Promise<void>
}

export interface DefectUserDisplay {
  id: number
  name: string
}
export interface DefectProductDisplay {
  id: number
  name: string
  project: { id: number | null; name: string } | null
}
export interface DefectModuleDisplay {
  id: number
  name: string
  full_path: string
}
export type DefectListRecord = Omit<
  DefectForm,
  'id' | 'project_product' | 'module' | 'assignee' | 'source_plan_id' | 'case_ids' | 'plan_case_ids'
> &
  DefectMetadata & {
    id: number
    status: number
    project_product: DefectProductDisplay | null
    module: DefectModuleDisplay | null
    assignee: DefectUserDisplay | null
    reporter: DefectUserDisplay | null
    relation_count: number
  }
export interface DefectFilters {
  project_product: DefectProductSelection
  module: DefectSelection
  keyword: string
  status: DefectSelection
  severity: DefectSelection
  priority: DefectSelection
  defect_type: DefectSelection
  source_type: DefectSelection
  assignee: DefectSelection
  reporter: DefectSelection
  source_plan: DefectSelection
  create_range: string[] | null
  update_range: string[] | null
}
export interface DefectStats {
  open_count: number
  my_pending_count: number
  serious_count: number
  resolved_pending_count: number
}
export type DefectQuickField = 'severity' | 'priority' | 'assignee'
