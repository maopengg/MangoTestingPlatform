export interface ModuleParent {
  id: number
  name?: string
}
export interface ModuleRecord {
  id: number
  name: string
  parent?: ModuleParent | null
  level: number
  full_path?: string
  create_time?: string
  update_time?: string
  update_user?: { name?: string; username?: string } | null
}
export interface ModuleDraft {
  id: number | null
  name: string
  parent: number | null
  parentName: string
  level: number
}
export interface ModuleEditorHandle {
  create(parent?: ModuleRecord): void
  edit(record: ModuleRecord): void
  close(): void
}
