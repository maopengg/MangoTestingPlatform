export interface RequirementCaseRow {
  id: number
  case_no: string
  title: string
  priority: number | null
  owner: { name: string } | null
}

export interface RequirementCasePickerHandle {
  open(): void
  isSaving(): boolean
  isOpen(): boolean
}

export interface RequirementTaskForm {
  name: string
  task_type: number
  status: number
  owner: number | null
  planned_start_date: string | null
  planned_end_date: string | null
  estimated_person_days: number | null
  actual_person_days: number | null
  self_test_status: number
  sort_order: number
}

export interface RequirementTaskRecord extends RequirementTaskForm {
  id: number
  requirement_version: number
  owner_name: string
}

export interface RequirementTaskRow {
  key: string
  id: number | null
  form: RequirementTaskForm
  confirmed: RequirementTaskRecord | null
  error: boolean
}

export interface RequirementTasksHandle {
  isSaving(): boolean
}

export interface RequirementVersionForm {
  requirement_name: string
  description: string
  owner: number | null
  development_owner: number | null
  delivery_team: number | null
  iteration_ref: number | null
  test_required: boolean
  automation_recommended: boolean
  effect_test_required: boolean
  planned_start_date: string | null
  planned_submit_date: string | null
  planned_release_date: string | null
  customer_deadline_date: string | null
  committed_release_date: string | null
  customer_ref: string
}
export type RequirementVersionField = keyof RequirementVersionForm
export type RequirementFlag = 'test_required' | 'automation_recommended' | 'effect_test_required'
export interface RequirementForm {
  owner: number | null
  issue_type: number
  requirement_category: number
}
export interface RequirementRecord {
  id: number
  name: string
  requirement_key: string
  form: RequirementForm
}
export interface RequirementVersion {
  id: number
  status: number
  update_time: string
  version_no: number
  product: { id: number; name: string } | null
  requirement: RequirementRecord | null
  form: RequirementVersionForm
  ownerName: string
  developerName: string
  teamName: string
  iterationName: string
}
export interface RequirementPlan {
  id: number
  name: string
  status: number
  owner: { name: string } | null
  execution_stats: { progress: number; pass_rate: number }
}
export interface RequirementDefect {
  id: number
  defect_no: string
  title: string
  status: number
  severity: number
  assignee: { name: string } | null
}
export interface RequirementResource {
  id: number
  title: string
  context_key: string
  content: string
  file_name: string
  update_time: string
}
