export interface SourceExtraConfig {
  ssl?: boolean
  scheme?: 'http' | 'https'
  path_prefix?: string
  verify_certs?: boolean
}

export interface DataSourceRecord {
  id: number
  source_category: number
  db_type: number
  display_name: string
  host: string
  port: number
  file_path: string
  user: string
  extra_config?: SourceExtraConfig | null
  update_time?: string
}

export interface SourceDraft {
  source_category: number | null
  db_type: number | null
  display_name: string
  host: string
  port: string | number
  file_path: string
  user: string
  password: string
  extra_config: SourceExtraConfig
}

export interface SourceBinding {
  id: number
  datasource_alias_id: number
  datasource_alias__name: string
  datasource_alias__project_product_id: number
  datasource_alias__project_product__name: string
  datasource_alias__project_product__project__name: string
  environment: number
  database_name: string
  schema_name: string
  redis_db: number | null
  db_c_status: number
  db_rud_status: number
  project_product_path?: string
}

export interface DiscoveredDatabase {
  name: string
}
export interface ConnectionCheck {
  key?: string
  name: string
  status: string
  message: string
}
export interface ConnectionResult {
  connected: boolean
  checks?: ConnectionCheck[]
  error?: string
}
export interface SourceEditorHandle {
  open(record?: DataSourceRecord): void
  close(): void
}
