export interface RunHistoryFilters {
  name: string
  status: string[]
  verdict: string[]
}

export interface RunHistoryRecord {
  id: number
  name: string
  status: string
  verdict: string
  engine: string
  peak_target_users: number | null
  actual_node_count: number | null
  requested_node_count: number | null
  create_time: string
  project_product: { id: number; name: string }
  module_full_path: string
}
