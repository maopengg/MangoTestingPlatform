export interface PersonalProfile {
  id: number
  name: string
  username: string
  roleName: string | null
  lastLoginTime: string | null
  ip: string | null
  requiresEmailMigration: boolean
}
export interface PasswordDraft { password: string; email: string; new_password: string; confirm_password: string }
export interface PasswordDialogHandle { open(): void; close(): void }
export type CacheValue = null | string | number | boolean | CacheValue[] | { [key: string]: CacheValue }
export interface UserCacheItem {
  cache_key: string
  title: string
  value: CacheValue
  display_value: CacheValue
  value_type: 'string' | 'number' | 'boolean' | 'json' | 'environment'
  description: string
  clearable: boolean
  updated_at: string | null
  has_value: boolean
}
export interface UserCacheGroup {
  group_key: string
  title: string
  count: number
  value_count: number
  items: UserCacheItem[]
}
