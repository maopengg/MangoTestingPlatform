export interface DataFactoryGeneratorConfig {
  value?: string | number | boolean | null
  [key: string]: any
}

export interface DataFactoryFieldOverrideRule {
  generator_type: number
  generator_config: DataFactoryGeneratorConfig
}

export type DataFactoryFieldOverrides = Record<string, DataFactoryFieldOverrideRule>

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
