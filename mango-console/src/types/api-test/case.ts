import type { ApiCasePublicationStatus } from './case-version'

export type JsonPrimitive = string | number | boolean | null
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[]
export interface JsonObject {
  [key: string]: JsonValue
}

export interface ApiKeyValueItem {
  key: string
  value: string
  datasource_alias?: number | null
  test_envs?: number[]
}

export interface ApiParametrizeItem {
  key: string
  value: string | null
}

export interface ApiParametrizeSuite {
  name: string
  parametrize: ApiParametrizeItem[]
}

export interface ApiCasePayload {
  id?: number
  project_product?: number
  module?: number
  name?: string
  case_flow?: string | null
  case_people?: number
  parametrize?: ApiParametrizeSuite[]
  level?: number
  scenario_layer?: number
  scenario_type?: number
  scenario_tags?: string[]
  scenario_description?: string | null
  front_custom?: ApiKeyValueItem[]
  front_sql?: ApiKeyValueItem[]
  front_headers?: number[]
  front_public?: number[]
  front_auth_config?: number[]
  callback_checks?: Record<string, any>[]
  posterior_sql?: ApiKeyValueItem[]
  status?: number
}

export interface ApiCaseQuery {
  page?: number
  pageSize?: number
  project_product?: number | string
  module?: number | string
  name?: string
  status?: number | string
  publication_status?: ApiCasePublicationStatus
  [key: string]: unknown
}

export interface ApiCaseConfigurationSummary {
  id: number
  name: string
  sql_count: number
  data_factory_count: number
  has_sql: boolean
  has_data_factory: boolean
  publication_status?: 'unpublished' | 'prepublished' | 'published'
  revision_id?: number | null
}

export interface ApiCaseConfigurationItem {
  kind: 'sql' | 'data_factory'
  location: string
  enabled: boolean | null
  configuration: Record<string, unknown>
}

export interface ApiCaseConfigurationDetails extends ApiCaseConfigurationSummary {
  items: ApiCaseConfigurationItem[]
}

export interface ApiCaseDetailedPayload {
  execution_config?: { is_recovery?: boolean }
  id?: number
  case?: number | string
  api_info?: number | string
  case_sort?: number
  status?: number
  error_message?: string | null
  parent_id?: number | string
}

export interface ApiCaseDataFactoryPayload {
  id?: number
  case?: number | string
  template?: number | string
  name?: string
  stage?: number
  sort?: number
  field_overrides?: JsonObject
  cleanup_strategy?: number | null
  status?: number
  [key: string]: unknown
}
