export interface IterationScheduleSubject {
  id: number
  suite_id?: number
  requirement_name?: string
  requirement?: { name?: string } | null
  version_no?: number
  development_owner?: number | { id: number; name?: string } | null
  priority?: number
  planned_start_date?: string | null
  planned_submit_date?: string | null
  status?: number
}

export interface IterationScheduleForm {
  development_owner: number | null
  priority: number | null
  planned_start_date: string | null
  planned_submit_date: string | null
  status: number | null
}

export interface IterationScheduleHandle {
  open: (record: IterationScheduleSubject) => void
  isSaving: (id: number) => boolean
}

export interface IterationUserOption {
  key: number | string
  title: string
}
