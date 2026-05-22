export interface DataFactorySkipGeneratorConfig {
  reason?: string | null
}

export interface DataFactoryFixedGeneratorConfig {
  value?: string | number | boolean | null
}

export interface DataFactoryRandomStringGeneratorConfig {
  prefix?: string
  length?: number
}

export interface DataFactoryRandomNumberGeneratorConfig {
  min?: number
  max?: number
}

export interface DataFactoryRandomDecimalGeneratorConfig
  extends DataFactoryRandomNumberGeneratorConfig {
  precision?: number
}

export interface DataFactoryRelativeTimeGeneratorConfig {
  days?: number
  hours?: number
  minutes?: number
}

export interface DataFactoryUuidGeneratorConfig {
  dash?: boolean
}

export interface DataFactoryEnumOption {
  label?: string | number | boolean | null
  value: any
}

export interface DataFactoryEnumGeneratorConfig {
  values?: any[]
  options?: DataFactoryEnumOption[]
  mode?: 'fixed' | 'random'
  value?: any
}

export interface DataFactoryEntityDependencyGeneratorConfig {
  dependency_entity_id: number
  field: string
}

export interface DataFactoryOverrideDependencyGeneratorConfig
  extends DataFactoryEntityDependencyGeneratorConfig {
  template_id?: number | null
  strategy?: 'reuse_or_create' | 'must_exist' | 'create_always'
}

export interface DataFactoryFunctionGeneratorConfig {
  value: string
}

export type DataFactoryGeneratorConfig =
  | DataFactorySkipGeneratorConfig
  | DataFactoryFixedGeneratorConfig
  | DataFactoryRandomStringGeneratorConfig
  | DataFactoryRandomNumberGeneratorConfig
  | DataFactoryRandomDecimalGeneratorConfig
  | DataFactoryRelativeTimeGeneratorConfig
  | DataFactoryUuidGeneratorConfig
  | DataFactoryEnumGeneratorConfig
  | DataFactoryEntityDependencyGeneratorConfig
  | DataFactoryOverrideDependencyGeneratorConfig
  | DataFactoryFunctionGeneratorConfig

export interface DataFactoryFieldOverrideRule {
  generator_type: number
  generator_config: DataFactoryGeneratorConfig
}

export type DataFactoryFieldOverrides = Record<string, DataFactoryFieldOverrideRule>

export interface DataFactorySceneFieldOverrides {
  __main__?: DataFactoryFieldOverrides
  __items__?: Record<string, DataFactoryFieldOverrides>
}

export type DataFactoryAnyFieldOverrides =
  | DataFactoryFieldOverrides
  | DataFactorySceneFieldOverrides

export interface DataFactoryOutputConfigItem {
  field: string
  key: string
}

export type DataFactoryOutputConfig = DataFactoryOutputConfigItem[]

export interface DataFactoryFieldRule {
  id?: number
  name: string
  label?: string
  db_type?: string
  platform_type?: string
  nullable?: boolean
  primary_key?: boolean
  autoincrement?: boolean
  generator_type?: number
  generator_config?: DataFactoryGeneratorConfig
  enum_values?: any[]
}

export interface DataFactoryTemplateItem {
  id?: number | string
  child_template: number | null
  child_template_detail?: any
  name: string
  sort: number
  field_overrides: DataFactoryFieldOverrides
}
