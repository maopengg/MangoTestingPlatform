export type Id = number | string
export type Selection = Id | Id[] | null
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue }
export interface Reference {
  id: Id
  name?: string
  full_path?: string
}
export interface EntityRecord {
  id: number
  name: string
  project_product: Reference | Id
  module: Reference | Id | null
  datasource_alias: Reference | Id
  description?: string | null
  table_name: string
  schema_name?: string
  primary_key?: string
  unique_key?: string
  create_type?: number
  delete_type?: number
  cleanup_order?: number
  status: number
  status_change_source?: number
  status_change_reason?: string
  status_changed_at?: string
}
export interface EntityDraft {
  project_product: Selection
  module: Id | null
  datasource_alias: Id | null
  name: string
  description: string
  table_name: string
  schema_name: string
  primary_key: string
  unique_key: string
  create_type: number
  delete_type: number
  cleanup_order: number
  status: number
}
export interface LogicalSource {
  id: number
  name: string
  project_product?: Id | Reference
}
export interface TableInfo {
  name?: string
  table?: string
  comment?: string
  table_comment?: string
  schema_name?: string
}
export interface TableOption {
  label: string
  value: string
  comment: string
  schema_name: string
}
export interface TableSchema {
  columns?: FieldRecord[]
  schema_name?: string
  table_comment?: string
  primary_keys?: string[]
  indexes?: Array<{ unique?: boolean; column_names?: string[] }>
}
export interface EnumOption {
  label: string
  value: JsonValue
}
export interface GeneratorConfig {
  value?: JsonValue
  values?: JsonValue[]
  options?: EnumOption[]
  mode?: string
  reason?: string
  field?: string
  alias?: string
  dependency_entity_id?: Id | null
  prefix?: string
  length?: number
  min?: number
  max?: number
  precision?: number
  days?: number
  hours?: number
  minutes?: number
  dash?: boolean
}
export interface FieldRecord {
  id?: number
  name: string
  label?: string | null
  comment?: string
  db_type?: string
  platform_type?: string
  nullable?: boolean
  primary_key?: boolean
  autoincrement?: boolean
  max_length?: number | null
  enum_values?: JsonValue[]
  generator_type?: number
  generator_config?: GeneratorConfig
  sort?: number
  recommend?: { generator_type?: number; generator_config?: GeneratorConfig }
}
export interface FieldRow extends FieldRecord {
  generator_type: number
  generator_config: GeneratorConfig
  generator_config_value: string
  preview_value?: JsonValue
  preview_valid: boolean
  preview_message: string
}
export interface PreviewField {
  name: string
  value?: JsonValue
  valid?: boolean
  message?: string
}
export interface StatusLog {
  id: number
  create_time?: string
  from_status_name?: string
  to_status_name?: string
  source: number
  source_name?: string
  reason?: string
  operator?: { name?: string; username?: string } | null
  source_record_type?: string
  source_record_id?: Id | null
}
export interface BatchDraft {
  project_product: Selection
  module: Id | null
  datasource_alias: Id | null
  sync_fields: boolean
  skip_exists: boolean
}
export interface BatchRow {
  key: string
  table_name: string
  schema_name: string
  table_comment: string
  name: string
  status: string
  message: string
  disabled: boolean
  entity_id?: number | null
  field_count?: number
}
export interface BatchResult {
  items: Array<{
    table_name: string
    name?: string
    status: string
    message: string
    entity_id?: number | null
    field_count?: number
  }>
  success?: number
  skipped?: number
  failed?: number
}
export interface NavigationDefaults {
  projectProduct: Id | null
  module: Id | null
}
export interface EntityEditorHandle {
  open(record?: EntityRecord, defaults?: NavigationDefaults): void
  close(): void
}
export interface RecordPanelHandle {
  open(record: EntityRecord): void
  close(): void
}
export interface BatchPanelHandle {
  open(defaults?: NavigationDefaults): void
  close(): void
}
export interface EnumEditorHandle {
  open(row: FieldRow): void
  close(): void
}
export interface DependencyOption {
  label: string
  value: string
  raw_id: Id
  level: 'module' | 'entity' | 'field'
  isLeaf: boolean
  children?: DependencyOption[]
}
