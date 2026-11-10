export type EntityId = number | string
export interface LogicalSource {
  id: number
  name: string
  source_category: number
  db_type: number
  description: string | null
  status: number
  project_product?: EntityId | { id: EntityId }
}
export interface SourceConnection {
  id: number
  db_type: number
  source_category: number
  display_name?: string
  name?: string
  host: string
  port: number
  file_path?: string
  extra_config?: { path_prefix?: string } | null
  update_time?: string
}
export interface BindingTarget {
  database_name: string
  schema_name: string
  redis_db: number | null
}
export interface LogicalBinding extends BindingTarget {
  id: number
  environment: number | null
  data_source?: SourceConnection | null
  database?: SourceConnection | number | null
  db_c_status: number
  db_rud_status: number
}
export interface AliasDraft {
  name: string
  sourceCategory: number
  dbType: number | null
  description: string
  status: number
}
export interface AliasEditorHandle {
  open(record?: LogicalSource): void
  close(): void
}
export interface BindingEditorHandle {
  open(record?: LogicalBinding): void
  close(): void
}
export interface QueryDrawerHandle {
  open(record: LogicalSource): void
  close(): void
}
export interface DiscoveredTable {
  name: string
  comment?: string
  schema_name?: string
  key: string
}
export interface TableSchema {
  columns: Array<{
    name: string
    db_type?: string
    label?: string
    nullable?: boolean
    primary_key?: boolean
    autoincrement?: boolean
  }>
  indexes?: Array<{ name: string; column_names?: string[]; unique?: boolean }>
  foreign_keys?: Array<{
    constrained_columns?: string[]
    referred_table: string
    referred_columns?: string[]
  }>
}
export interface GenerationResult {
  table_name: string
  status: string
  message: string
}
