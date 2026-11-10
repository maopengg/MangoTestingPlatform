import type { FlowData } from '@/types/components'

export interface UiCaseFrontCustomItem {
  key: string
  value: unknown
  test_envs?: Array<number | string>
}

export type UiCaseFrontSqlItem = {
  sql: string | Record<string, unknown>
  key_list?: string | string[] | null
  datasource_alias?: number | string | null
  test_envs?: Array<number | string>
}

export type UiCasePosteriorSqlItem = {
  sql: string | Record<string, unknown>
  datasource_alias?: number | string | null
  test_envs?: Array<number | string>
}

export interface UiCasePayload {
  id?: number | string
  name?: string
  front_custom?: UiCaseFrontCustomItem[]
  front_sql?: UiCaseFrontSqlItem[]
  front_public?: Array<number | string>
  front_auth_config?: Array<number | string>
  posterior_sql?: UiCasePosteriorSqlItem[]
  [key: string]: unknown
}

export interface UiAuthCookie {
  name: string
  value: string
  domain?: string | null
  path?: string
  expires?: number | null
  httpOnly?: boolean
  secure?: boolean
  sameSite?: string | null
}

export interface UiAuthStorageItem {
  origin: string
  key: string
  value: string
}

export interface UiAuthCacheConfig {
  cookies: UiAuthCookie[]
  local_storage: UiAuthStorageItem[]
  session_storage: UiAuthStorageItem[]
  headers: Record<string, string>
  storage_state?: unknown
}

export interface UiAuthConfigPayload {
  id?: number | string
  project_product?: number | string | null
  test_env: number | string
  name?: string
  auth_type?: number
  status?: number
  refresh_mode?: number
  token_ttl?: number
  expire_notice_minutes?: number
  page_step?: number | string | null
  time_task?: number | string | null
  notice_group?: number | string | null
  custom_code?: string
  manual_config?: UiAuthCacheConfig | Record<string, unknown>
  auto_auth_config?: Record<string, unknown>
  api_config?: Record<string, unknown>
}

export interface UiPageStepsPayload {
  id?: number | string
  flow_data?: FlowData
  goal?: string | null
  entry_criteria?: UiStepConditionGroup
  success_criteria?: UiStepConditionGroup
  healing_enabled?: boolean
  healing_policy?: UiStepHealingPolicy
  config_version?: number
  [key: string]: unknown
}

export interface UiStepCondition {
  type: 'url_path' | 'page_title' | 'visible_text' | 'element_state'
  matcher: 'equals' | 'contains' | 'starts_with' | 'regex' | 'count_gte' | 'visible' | 'hidden' | 'enabled' | 'editable' | 'checked'
  expected?: unknown
  element_id?: number | string
  count?: number
}

export interface UiStepConditionGroup {
  operator: 'all' | 'any'
  conditions: UiStepCondition[]
}

export interface UiStepHealingPolicy {
  mode: 'off' | 'suggest_only' | 'execute_low_risk'
  total_timeout_seconds: number
  max_model_calls: number
  max_patch_actions: number
  max_recovery_rounds: number
  allowed_actions: string[]
  auto_writeback: boolean
  auto_writeback_min_confidence: number
}

export interface UiPageStepsDetailPayload {
  id?: number | string
  page_step: number | string
  type?: number
  flow_data?: FlowData
  node_id?: string
  precondition?: UiStepConditionGroup | Record<string, never>
  postcondition?: UiStepConditionGroup | Record<string, never>
  [key: string]: unknown
}
