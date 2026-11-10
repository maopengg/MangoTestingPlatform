export type EntityId = number | string
export type EntityReference = { id: number; name?: string }
export interface AuthDraft {
  name: string
  project_product: EntityId | EntityId[] | null
  test_env: number | null
  auth_type: number
  api_info: number | null
  target_address: string
  public_variable_ids: number[]
  custom_code: string | null
  refresh_mode: number
  token_ttl: number | null
  refresh_margin: number | null
  expire_notice_minutes: number | null
  time_task: number | null
  notice_group: number | null
}
export interface AuthRecord
  extends Omit<AuthDraft, 'project_product' | 'api_info' | 'time_task' | 'notice_group'> {
  id: number
  status: number
  project_product: EntityReference | number
  api_info: EntityReference | null
  time_task: EntityReference | null
  notice_group: EntityReference | null
  last_refresh_status: number
  update_user?: EntityReference | null
}
export interface AuthCache {
  name: string
  expires_at?: string | null
  remaining_minutes?: number | null
  last_refresh_time?: string | null
  last_refresh_error?: string | null
  cache_data?: Record<string, unknown> | null
}
export type SelectOption = { label: string; value: EntityId }
export type AuthEditorHandle = { open: (record?: AuthRecord, product?: EntityId | null) => void }
export type AuthCacheHandle = { open: (record: AuthRecord, refresh?: boolean) => Promise<void> }
export type AuthCodeHandle = { open: (record: AuthRecord) => void }
