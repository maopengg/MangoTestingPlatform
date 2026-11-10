export type CaseSelection = string | number
export type CaseProductSelection = CaseSelection | CaseSelection[] | null

export interface CaseStep {
  action: string
  expected: string
}

export interface LibraryCaseForm {
  id: number | null
  version_no: number | null
  case_no: string
  title: string
  project_product: CaseProductSelection
  module: CaseSelection | null
  owner: CaseSelection | null
  category_level_1: string
  category_level_2: string
  category_level_3: string
  priority: number
  test_types: number[]
  story_refs: string[]
  precondition: string
  test_point: string
  test_steps: CaseStep[]
  expected_result: string
  acceptance_source: string
  automation_status: string
  scenario_layer: number
  scenario_type: number
  scenario_tags: string[]
  test_data: string
  remark: string
  status: number
}

type CaseRelation = CaseSelection | { id: number } | null

export type LibraryCaseEditorRecord = Partial<
  Omit<
    LibraryCaseForm,
    'project_product' | 'module' | 'owner' | 'precondition' | 'test_data' | 'remark'
  >
> & {
  project_product?: CaseRelation
  project_product_id?: CaseSelection | null
  module?: CaseRelation
  module_id?: CaseSelection | null
  owner?: CaseRelation
  owner_id?: CaseSelection | null
  precondition?: string | null
  test_data?: string | null
  remark?: string | null
}

export interface CaseUserOption {
  key: number
  title: string
}

export interface CaseCategoryOptions {
  category_level_1: string[]
  category_level_2: string[]
  category_level_3: string[]
}

export interface CaseEditorHandle {
  open: (record?: LibraryCaseEditorRecord) => Promise<void>
}

export interface CaseHistorySubject {
  id: number
  case_no: string
  title: string
}

export interface CaseHistoryHandle {
  open: (record: CaseHistorySubject) => Promise<void>
}

export interface CaseBindingSubject {
  id: number
  bindings?: Array<{
    automation_type: number
    automation_case_id: number
  }>
}

export interface CaseBindingHandle {
  open: (record: CaseBindingSubject) => void
}

export interface CasePlanSubject {
  id: number
  productId: CaseSelection | null
  ownerId: CaseSelection | null
}

export interface CasePlanHandle {
  openCreate: (selection: CasePlanSubject[]) => Promise<void>
  openJoin: (selection: CasePlanSubject[]) => Promise<void>
}

export interface LibraryPlanForm {
  name: string
  project_product: CaseProductSelection
  scope_type: number
  requirement_version: number | null
  iteration: number | null
  scope_ref: string
  environment: string
  build_version: string
  owner: CaseSelection | null
  planned_start_time: string | null
  planned_end_time: string | null
  status: number
  remark: string
}

export interface PlanChoice {
  label: string
  value: number
}

export interface PlanChoiceRecord {
  id: number
  name: string
  version_no?: number
  iteration_no?: string
}

export interface LibraryCaseBinding {
  automation_type: number
  automation_case_id: number
  automation_case_name: string
}

export interface LibraryCaseRow
  extends Omit<LibraryCaseForm, 'id' | 'version_no' | 'project_product' | 'module' | 'owner'> {
  id: number | string
  version_no: number | string
  project_product_id: CaseSelection | null
  module_id: CaseSelection | null
  owner_id: CaseSelection | null
  project_product_path: string
  module_path: string
  owner_name: string
  automation_bindings: string
  bindings: LibraryCaseBinding[]
  update_time: string
  __draft: boolean
  __touched: boolean
  draft_id?: string
}

export interface LibraryPersistedCaseRow extends LibraryCaseRow {
  id: number
  version_no: number
  __draft: false
}

export interface LibraryDraftDefaults {
  productId: CaseSelection | null
  productPath: string
  moduleId: CaseSelection | null
  modulePath: string
  ownerId: CaseSelection | null
  ownerName: string
}

export interface LibraryGridHandle {
  refreshRowCells: (id: number | string, fields: string[]) => void
}
