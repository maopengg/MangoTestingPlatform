export interface ProjectRecord {
  id: number
  name: string
  status: number
  create_time?: string
  update_time?: string
  update_user?: { id?: number; name?: string; username?: string } | null
}
export interface ProjectDraft {
  name: string
}
export interface ProjectUserOption {
  key: number | string
  title: string
}
