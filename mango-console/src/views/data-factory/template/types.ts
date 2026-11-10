import type { DataFactoryFieldOverrides, DataFactoryOutputConfig } from '@/types/data-factory'
export type Id = string | number
export interface Reference {
  id: Id
  name?: string
  table_name?: string
  full_path?: string
}
export interface EntityOption extends Reference {
  display_name: string
}
export interface TemplateRecord {
  id: number
  name: string
  project_product: Id | Reference
  module: Id | Reference | null
  entity: Id | Reference | null
  description?: string | null
  field_overrides?: DataFactoryFieldOverrides
  output_config?: DataFactoryOutputConfig
  cleanup_strategy: number
  is_default: boolean
  usage_scope: number
  status: number
  config_status?: number
}
export interface TemplateDraft {
  project_product: Id | Id[] | null
  module: Id | null
  entity: Id | null
  name: string
  description: string
  field_overrides: DataFactoryFieldOverrides
  output_config: DataFactoryOutputConfig
  cleanup_strategy: number
  is_default: boolean
  usage_scope: number
  status: number
}
export interface NavigationDefaults {
  projectProduct: Id | null
  module: Id | null
}
export interface EditorHandle {
  open(record?: TemplateRecord, defaults?: NavigationDefaults): void
  close(): void
}
