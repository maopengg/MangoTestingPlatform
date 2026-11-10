export interface IterationPerson {
  id: number
  name: string
}
export interface IterationDetail {
  id: number
  name: string
  status: number
  start_date: string | null
  end_date: string | null
  owner: IterationPerson | null
}
export interface IterationRow extends IterationDetail {
  iteration_no: string
  project_product: { id: number; name: string; project: { id: number; name: string } | null } | null
  remark: string
  requirement_count: number
  plan_count: number
  open_defect_count: number
  update_time: string
  test_metrics: { total: number; executed: number; progress: number; pass_rate: number }
}
export interface IterationForm {
  iteration_no: string
  name: string
  project_product: number | string | Array<number | string> | null
  owner: number | string | null
  start_date: string | null
  end_date: string | null
  status: number | string | null
  remark: string
}
export interface IterationOption {
  key: number | string
  title: string
}
export interface IterationEditorHandle {
  open: (record: IterationRow | null, productId?: number | null) => void
  isSaving: (id: number) => boolean
}
export interface IterationSuite {
  id: number
  requirement_name: string
  requirement: { id: number; name: string; requirement_key: string } | null
  version_no: number
  development_owner: IterationPerson | null
  owner: IterationPerson | null
  priority: number
  status: number
  planned_start_date: string | null
  planned_submit_date: string | null
  actual_submit_at: string | null
  update_time: string
  case_count: number
  open_defect_count: number
  test_metrics: { progress: number; pass_rate: number }
}
export interface IterationBoardColumn {
  status: number
  title: string
  items: IterationSuite[]
}
export interface IterationGanttItem {
  id: string | number
  suite_id: number
  requirement_key: string
  requirement_name: string
  version_no: number
  status: number
  planned_start_date: string | null
  planned_submit_date: string | null
  time_progress: number
  overlap: boolean
  overdue: boolean
  overlap_with: string[]
}
export interface IterationGanttData {
  iteration: { id: number; start_date: string | null; end_date: string | null } | null
  today: string | null
  groups: Array<{ owner_id: number | null; owner_name: string; items: IterationGanttItem[] }>
  summary: {
    owner_count: number
    requirement_count: number
    overdue_count: number
    overlap_count: number
  }
}
export interface IterationPlan {
  id: number
  name: string
  scope_type: number
  status: number
  owner: IterationPerson | null
  execution_stats: { executed: number; total: number; progress: number; pass_rate: number }
  open_defect_count: number
  update_time: string
}
export interface IterationDefect {
  id: number
  defect_no: string
  title: string
  status: number
  severity: number
  priority: number
  assignee: IterationPerson | null
  update_time: string
}

export interface RequirementOverviewSuite extends IterationSuite {
  project_product: { id: number; name: string; project: { id: number; name: string } | null } | null
  module: { id: number; name: string; full_path: string } | null
  iteration_ref: { id: number } | null
  automation_coverage_percent: number
}
export interface RequirementOverviewCase {
  id: number
  case_no: string
  title: string
  priority: number
  owner: IterationPerson | null
}
export interface RequirementOverviewResource {
  id: number
  title: string
  context_key: string
  update_time: string
}
