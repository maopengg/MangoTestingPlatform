export type JsonPrimitive = string | number | boolean | null
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[]
export interface JsonObject {
  [key: string]: JsonValue
}

export interface ApiKeyValueItem {
  key: string
  value: string
  datasource_alias?: number | null
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
  scenario_tags?: number[]
  scenario_description?: string | null
  front_custom?: ApiKeyValueItem[]
  front_sql?: ApiKeyValueItem[]
  front_headers?: number[]
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
  [key: string]: unknown
}

export interface ApiCaseDetailedPayload {
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
