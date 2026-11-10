export type EntityId = number | string
export type ProductSelection = EntityId | EntityId[] | null
export interface LogicalSource {
  id: number
  project_product?: EntityId | { id: EntityId; name?: string } | null
  name: string
  source_category: number
  db_type: number
  description?: string | null
  status: number
}
export interface SourceConnection {
  id: number
  source_category: number
  db_type: number
  display_name?: string
  file_path?: string
  host?: string
  port?: number
  extra_config?: { path_prefix?: string } | null
}
export interface BindingTarget {
  database_name: string
  schema_name: string
  redis_db: number | null
}
export interface LogicalBinding extends BindingTarget {
  id: number
  environment: number | null
  data_source?: SourceConnection | number | null
  database?: SourceConnection | number | null
  description?: string | null
  db_c_status: number
  db_rud_status: number
}
export interface AliasDraft {
  project_product: ProductSelection
  name: string
  source_category: number
  db_type: number | null
  description: string
  status: number
}
export interface BindingDraft {
  environment: EntityId | null
  data_source: number | null
  target: BindingTarget
  allowQuery: boolean
  allowWrite: boolean
  description: string
}
export interface AliasEditorHandle {
  open(record?: LogicalSource, product?: EntityId | null): void
  close(): void
}
export interface BindingEditorHandle {
  open(alias: LogicalSource, record?: LogicalBinding): void
  close(): void
}
export interface BindingsDrawerHandle {
  open(alias: LogicalSource): void
  close(): void
}
