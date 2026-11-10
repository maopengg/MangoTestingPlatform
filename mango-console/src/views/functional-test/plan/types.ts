import type { LibraryCaseForm, LibraryPlanForm } from '../case-library/types'

export interface PlanLibraryCase {
  id: number
  case_no: string
  title: string
  category_level_1: string
  category_level_2: string
  category_level_3: string
  priority: number | null
}
export interface PlanCasePickerHandle {
  open: () => void
  isSaving: () => boolean
  isOpen: () => boolean
}
export interface PlanDefectOption {
  value: number
  label: string
}
export interface PlanDefectRelationHandle {
  open: (mode: 'bind' | 'unbind', caseIds: number[], options?: PlanDefectOption[]) => void
  isSaving: () => boolean
  isOpen: () => boolean
}
export type PlanEditorForm = Omit<LibraryPlanForm, 'status'>
export interface PlanListRow {
  id: number
  name: string
  status: number
  scope_type: number
  scope_ref: string
  project_product: { id: number; name: string; project: { id: number; name: string } | null } | null
  owner: { id: number; name: string } | null
  requirement_version: {
    id: number
    requirement_name: string
    version_no: number
    requirement: { name: string } | null
  } | null
  iteration: { id: number; name: string; iteration_no: string } | null
  environment: string
  build_version: string
  planned_start_time: string | null
  planned_end_time: string | null
  remark: string
  case_count: number
  open_defect_count: number
  unlinked_failed_count: number
  update_time: string
  execution_stats: {
    executed: number
    total: number
    passed: number
    failed: number
    blocked: number
    skipped: number
    progress: number
    pass_rate: number
  }
}
export interface PlanEditorDefaults {
  productId: number | null
  requirementId?: number | null
}
export interface PlanEditorHandle {
  open: (record: PlanListRow | null, defaults?: PlanEditorDefaults) => void
  isSaving: (id?: number) => boolean
}

export interface PlanCaseRow
  extends Omit<
    LibraryCaseForm,
    'id' | 'version_no' | 'project_product' | 'module' | 'owner' | 'status'
  > {
  id: number
  plan: number
  result: number
  project_product_id: number | null
  module_id: number | null
  owner_id: number | null
  project_product_path: string
  module_path: string
  owner_name: string
  automation_bindings: string
  actual_result: string
  execution_note: string
  defect_summary: string
  open_defect_count: number
  defects: Array<{ id: number; defect_no: string; title: string; status: number }>
}
export interface PlanDetail {
  id: number
  name: string
  status: number
  scope_type: number
  scope_ref: string
  project_product: { id: number; name: string } | null
  requirement_version: {
    requirement_name: string
    version_no: number
    requirement: { name: string } | null
  } | null
  iteration: { name: string } | null
  environment: string
  build_version: string
  started_at: string
  finished_at: string
  defect_count: number
  open_defect_count: number
  unlinked_failed_count: number
  execution_stats: { executed: number; total: number; pass_rate: number }
  cases: PlanCaseRow[]
}
export type PlanExecutionResult =
  | {
      kind: 'start' | 'finish'
      id: number
      status: number
      started_at: string
      finished_at: string
    }
  | { kind: 'remove'; ids: number[] }
  | { kind: 'batch'; rows: PlanCaseRow[] }
