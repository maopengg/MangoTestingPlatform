import { cloneLosslessJson } from '@/utils/lossless-json'
import type { UiAuthConfigPayload } from '@/types/ui-test/case'

export type UiAuthId = number | string
export interface UiAuthOption { key: UiAuthId; title: string }
export interface UiAuthDraft {
  project_product: UiAuthId | null
  test_env: number | null
  name: string
  auth_type: number
  status: 0 | 1
  page_step: UiAuthId | null
  api_info: UiAuthId | null
  time_task: UiAuthId | null
  notice_group: UiAuthId | null
  refresh_mode: number
  token_ttl: number | null
  expire_notice_minutes: number | null
}
export interface UiAuthJsonDraft { manual: string; auto: string; api: string }
export function uiAuthObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid UI authorization object')
  return value as Record<string, unknown>
}
export function uiAuthResponse(value: unknown): unknown {
  const response = uiAuthObject(value)
  if (response.code !== 200) throw Error('UI authorization request failed')
  return response.data
}
export function uiAuthId(value: unknown): UiAuthId | null {
  if (Array.isArray(value)) return uiAuthId(value[value.length - 1])
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'object') return uiAuthId(uiAuthObject(value).id)
  if (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) return value
  if (typeof value === 'string' && /^\d+$/.test(value)) return value
  throw Error('Invalid UI authorization ID')
}
export function requiredUiAuthId(value: unknown): UiAuthId {
  const id = uiAuthId(value)
  if (id === null) throw Error('Missing UI authorization ID')
  return id
}
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid UI authorization text'); return value }
function numeric(value: unknown, fallback: number | null): number | null {
  if (value == null || value === '') return fallback
  if (typeof value !== 'string' && typeof value !== 'number') throw Error('Invalid UI authorization number')
  const result = Number(value)
  if (!Number.isSafeInteger(result) || result < 0) throw Error('Invalid UI authorization number')
  return result
}
export function createUiAuthDraft(): UiAuthDraft {
  return { project_product: null, test_env: null, name: '', auth_type: 0, status: 1, page_step: null, api_info: null, time_task: null, notice_group: null, refresh_mode: 0, token_ttl: 1440, expire_notice_minutes: 30 }
}
export function createUiAuthJsonDraft(): UiAuthJsonDraft {
  return {
    manual: '{"cookies":[],"local_storage":[],"session_storage":[],"headers":{}}',
    auto: '{"url":"","cookie_domains":[],"local_storage_keys":[],"session_storage_keys":[],"headers":{},"timeout":300}',
    api: '{"api_info":null,"token_path":"$.response.json.data.token","cookie_mapping":{},"local_storage_mapping":[],"session_storage_mapping":[],"header_mapping":{}}',
  }
}
export function readUiAuthDraft(value: unknown): UiAuthDraft {
  const row = uiAuthObject(value), api = row.api_config == null ? {} : uiAuthObject(row.api_config), status = numeric(row.status, 1)
  if (status !== 0 && status !== 1) throw Error('Invalid authorization enabled state')
  return { project_product: uiAuthId(row.project_product), test_env: numeric(row.test_env, null), name: text(row.name), auth_type: numeric(row.auth_type, 0) ?? 0, status,
    page_step: uiAuthId(row.page_step), api_info: uiAuthId(api.api_info ?? api.api_info_id), time_task: uiAuthId(row.time_task), notice_group: uiAuthId(row.notice_group), refresh_mode: numeric(row.refresh_mode, 0) ?? 0,
    token_ttl: numeric(row.token_ttl, 1440), expire_notice_minutes: numeric(row.expire_notice_minutes, 30) }
}
export function readUiAuthJsonDraft(value: unknown): UiAuthJsonDraft {
  const row = uiAuthObject(value)
  return { manual: JSON.stringify(row.manual_config == null ? {} : uiAuthObject(row.manual_config), null, 2), auto: JSON.stringify(row.auto_auth_config == null ? {} : uiAuthObject(row.auto_auth_config), null, 2), api: JSON.stringify(row.api_config == null ? {} : uiAuthObject(row.api_config), null, 2) }
}
export function parseUiAuthJson(value: string): Record<string, unknown> {
  const parsed: unknown = JSON.parse(value || '{}')
  return uiAuthObject(parsed)
}
export function uiAuthPayload(form: UiAuthDraft, json: UiAuthJsonDraft, id: UiAuthId | null): UiAuthConfigPayload {
  const manual = parseUiAuthJson(json.manual), auto = parseUiAuthJson(json.auto), api = parseUiAuthJson(json.api)
  const product = uiAuthId(form.project_product), apiId = uiAuthId(form.api_info)
  return {
    ...(id === null ? {} : { id: requiredUiAuthId(id) }), project_product: product, test_env: form.test_env ?? '', name: form.name, auth_type: form.auth_type, status: form.status,
    refresh_mode: form.auth_type === 3 ? 0 : form.refresh_mode, token_ttl: form.token_ttl ?? undefined, expire_notice_minutes: form.expire_notice_minutes ?? undefined,
    page_step: form.auth_type === 3 ? uiAuthId(form.page_step) : null, time_task: form.auth_type === 2 && form.refresh_mode === 1 ? uiAuthId(form.time_task) : null,
    notice_group: form.auth_type !== 3 && form.refresh_mode === 2 ? uiAuthId(form.notice_group) : null, custom_code: '',
    manual_config: cloneLosslessJson(manual), auto_auth_config: cloneLosslessJson(auto), api_config: { ...cloneLosslessJson(api), api_info: apiId ?? uiAuthId(api.api_info ?? api.api_info_id) },
  }
}
export function validateUiAuthDraft(form: UiAuthDraft): string {
  if (uiAuthId(form.project_product) === null) return '请选择项目/产品'
  if (form.test_env === null) return '请选择被测环境'
  if (!form.name.trim()) return '请输入授权名称'
  if (![0,1,2,3].includes(form.auth_type)) return '当前授权方式暂未开放'
  if (form.auth_type === 3 && uiAuthId(form.page_step) === null) return '请选择登录页面步骤'
  if (form.auth_type !== 3 && ![0,1,2].includes(form.refresh_mode)) return '请选择有效的刷新方式'
  if (form.auth_type !== 2 && form.auth_type !== 3 && form.refresh_mode === 1) return '当前授权方式不支持定时刷新'
  if (form.auth_type === 2 && form.refresh_mode === 1 && uiAuthId(form.time_task) === null) return '请选择定时策略'
  if (form.auth_type !== 3 && form.refresh_mode === 2 && uiAuthId(form.notice_group) === null) return '请选择到期提醒通知组'
  if (form.token_ttl === null || !Number.isSafeInteger(form.token_ttl) || form.token_ttl <= 0) return '授权有效期必须大于0'
  if (form.auth_type !== 3 && form.refresh_mode === 2 && (form.expire_notice_minutes === null || !Number.isSafeInteger(form.expire_notice_minutes) || form.expire_notice_minutes < 10 || form.expire_notice_minutes >= form.token_ttl)) return '提前提醒时间须不少于10分钟且小于授权有效期'
  return ''
}
export function readUiAuthOptions(value: unknown): UiAuthOption[] {
  if (!Array.isArray(value)) throw Error('Invalid UI authorization options')
  return value.map(value => { const row = uiAuthObject(value), key = requiredUiAuthId(row.key ?? row.value ?? row.id); return { key, title: text(row.title ?? row.label ?? row.name) || `ID ${key}` } })
}
export function selectedUiAuthOptions(options: UiAuthOption[], id: UiAuthId | null, fallback: UiAuthOption[]): UiAuthOption[] {
  const result = options.map(option => String(option.key) === String(id) && id !== null ? { ...option, key: id } : { ...option })
  if (id !== null && !result.some(option => String(option.key) === String(id))) result.push({ key: id, title: fallback.find(option => String(option.key) === String(id))?.title ?? `ID ${id}` })
  return result
}
