export interface PersonalProfile {
  id: number
  name: string
  username: string
  roleName: string | null
  departmentNames: string[]
  ip: string | null
  requiresEmailMigration: boolean
}
export interface PasswordDraft { password: string; email: string; new_password: string; confirm_password: string }
export interface PasswordDialogHandle { open(): void; close(): void }
export type ConfigValue = null | string | number | boolean | ConfigValue[] | { [key: string]: ConfigValue }
export interface UserConfigItem {
  key: string
  name: string
  value: ConfigValue
  value_type: 'string' | 'number' | 'boolean' | 'json' | 'environment'
  description: string
  clearable: boolean
  updated_at: string | null
}
