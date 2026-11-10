export type Id = string | number
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue }
export interface EntityRecord {
  id: Id
  name?: string
  table_name?: string
}
export interface GeneratorConfig {
  reason?: string
  value?: unknown
  prefix?: string
  length?: number
  min?: number
  max?: number
  precision?: number
  days?: number
  hours?: number
  minutes?: number
  dash?: boolean
  options?: Array<{ label?: string | number | boolean | null; value: unknown }>
  values?: unknown[]
  mode?: string
  alias?: string
  field?: string
  dependency_entity_id?: Id | null
}
export interface FieldRecord {
  id?: Id
  name: string
  label?: string | null
  generator_type?: number | string
  generator_config?: GeneratorConfig | null
  nullable?: boolean
  primary_key?: boolean
  autoincrement?: boolean
  db_type?: string
  platform_type?: string
  enum_values?: JsonValue[]
}
export interface EntityRulesHandle {
  open(id: Id): void
  close(): void
}

export type Overrides = Record<
  string,
  { generator_type: number; generator_config: GeneratorConfig }
>
export interface OutputItem {
  field: string
  key: string
}
export interface PostUpdate {
  target_node: string
  target_field: string
  source_node: string
  source_field: string
  sort: number
}
export interface PostUpdateResult {
  valid?: boolean
  message?: string
  sql_template?: string
}
export interface TemplateSummary {
  id: Id
  name?: string
  entity?: Id | EntityRecord | null
  field_overrides?: Overrides
}
export interface SceneItem {
  id?: Id | null
  _key?: string
  child_template: Id | null
  child_template_detail?: TemplateSummary | null
  name: string
  sort: number
  field_overrides: Overrides
}
export interface TemplateRecord {
  id: Id
  name?: string
  description?: string
  project_product?: Id | EntityRecord | null
  module?: Id | EntityRecord | null
  entity?: Id | EntityRecord | null
  cleanup_strategy?: number
  is_default?: boolean
  config_status?: number
  status?: number
  field_overrides?: Overrides
  output_config?: OutputItem[]
  post_insert_updates?: PostUpdate[]
  cleanup_resources?: unknown[]
  items?: SceneItem[]
  preview_context?: { template_id?: Id; overrides?: Overrides; output_config?: OutputItem[] }
}
export interface TemplateDraft {
  id: Id | null
  project_product: Id | null
  module: Id | null
  entity: Id | null
  name: string
  description: string
  cleanup_strategy: number
  is_default: boolean
  config_status: number
  status: number
  field_overrides: Overrides
  output_config: OutputItem[]
  post_insert_updates: PostUpdate[]
  cleanup_resources: unknown[]
  items: SceneItem[]
}
export interface PreviewNode {
  template_id?: number | null
  template_name?: string
  entity_id?: number | null
  entity_name?: string
  table_name?: string
  alias?: string
  field?: string
  target_field?: string
  action?: string
  reused?: boolean
  scene_item_id?: Id
  scene_item_name?: string
  status?: string
  missing_count?: number
  fields?: FieldRecord[]
  missing_fields?: FieldRecord[]
  children?: PreviewNode[]
}
export interface PreviewResult {
  dependency_tree?: PreviewNode | null
  post_insert_updates?: PostUpdateResult[]
  can_debug_run?: boolean
  preview_mode?: string
  entity?: EntityRecord
}
export interface EditableNode {
  fields: FieldRecord[]
  fieldOverrides: Overrides
  outputConfig: OutputItem[]
}
export interface DebugResult {
  execution_no?: string
  execution_id?: number
  context?: JsonValue
}
export interface DebugHandle {
  run(id: Id, overrides: Overrides, environment: Id | null): Promise<boolean>
  close(): void
}
export interface PostUpdatesHandle {
  open(): void
  close(): void
}
export interface PostUpdateNode {
  value: string
  label: string
  fields: FieldRecord[]
  overrides: Overrides
}
