import { normalizeEmptyListTotal } from '@/utils/api-response'
import { cloneLosslessJson } from '@/utils/lossless-json'
import { readUiAuthDraft, requiredUiAuthId, uiAuthId, uiAuthObject, uiAuthResponse, type UiAuthDraft, type UiAuthId } from './auth-editor-records'

interface AuthRelation { id: UiAuthId; name: string }
export interface UiAuthListRecord extends Omit<UiAuthDraft, 'project_product' | 'page_step' | 'time_task' | 'notice_group' | 'api_info'> {
  id: UiAuthId
  project_product: (AuthRelation & { project: AuthRelation | null }) | null
  page_step: AuthRelation | null
  time_task: AuthRelation | null
  notice_group: AuthRelation | null
  manual_config: Record<string, unknown>
  auto_auth_config: Record<string, unknown>
  api_config: Record<string, unknown>
  custom_code: string
  expires_at: string
  last_refresh_time: string
  last_refresh_status: number
  last_refresh_error: string
  refreshing: boolean
  update_user: (AuthRelation & { username: string }) | null
  update_time: string
}
const filterKeys = ['id', 'name', 'test_env__in', 'auth_type__in', 'refresh_mode__in', 'last_refresh_status__in', 'update_user__in'] as const
export type UiAuthListQuery = { page: number; pageSize: number; project_product?: UiAuthId } & Partial<Record<typeof filterKeys[number], string | number>>
function text(value: unknown): string {
  if (value == null) return ''
  if (typeof value !== 'string') throw Error('Invalid authorization text')
  return value
}
function relation(value: unknown): AuthRelation | null {
  if (value == null || value === '') return null
  if (typeof value !== 'object') return { id: requiredUiAuthId(value), name: '' }
  const row = uiAuthObject(value)
  return { id: requiredUiAuthId(row.id), name: text(row.name) }
}
export function readUiAuthListRecord(value: unknown): UiAuthListRecord {
  const row = uiAuthObject(value), draft = readUiAuthDraft(row)
  const { api_info: _apiInfo, ...fields } = draft
  const product = relation(row.project_product), user = relation(row.update_user)
  const productData = row.project_product !== null && typeof row.project_product === 'object' ? uiAuthObject(row.project_product) : {}
  const userData = row.update_user !== null && typeof row.update_user === 'object' ? uiAuthObject(row.update_user) : {}
  const refreshStatus = row.last_refresh_status ?? 0
  if (typeof refreshStatus !== 'number' || !Number.isSafeInteger(refreshStatus)) throw Error('Invalid authorization refresh status')
  if (row.refreshing != null && typeof row.refreshing !== 'boolean') throw Error('Invalid authorization refreshing state')
  return {
    ...fields, id: requiredUiAuthId(row.id),
    project_product: product ? { ...product, project: relation(productData.project) } : null,
    page_step: relation(row.page_step), time_task: relation(row.time_task), notice_group: relation(row.notice_group),
    manual_config: cloneLosslessJson(row.manual_config == null ? {} : uiAuthObject(row.manual_config)),
    auto_auth_config: cloneLosslessJson(row.auto_auth_config == null ? {} : uiAuthObject(row.auto_auth_config)),
    api_config: cloneLosslessJson(row.api_config == null ? {} : uiAuthObject(row.api_config)),
    custom_code: text(row.custom_code), expires_at: text(row.expires_at), last_refresh_time: text(row.last_refresh_time),
    last_refresh_status: refreshStatus, last_refresh_error: text(row.last_refresh_error), refreshing: row.refreshing === true,
    update_user: user ? { ...user, username: text(userData.username) } : null, update_time: text(row.update_time),
  }
}
export function readUiAuthList(value: unknown) {
  value = normalizeEmptyListTotal(value)

  const data = uiAuthResponse(value), total = uiAuthObject(value).totalSize
  if (!Array.isArray(data) || typeof total !== 'number' || !Number.isSafeInteger(total) || total < 0) throw Error('Invalid authorization list')
  const rows = data.map(readUiAuthListRecord)
  if (new Set(rows.map(row => String(row.id))).size !== rows.length) throw Error('Duplicate authorization records')
  return { rows, total }
}
export function uiAuthListQuery(values: Record<string, unknown>, product: unknown, page: number, pageSize: number): UiAuthListQuery {
  const query: UiAuthListQuery = { page, pageSize }
  const productId = uiAuthId(product)
  if (productId !== null) query.project_product = productId
  for (const key of filterKeys) {
    const value = values[key]
    if (value == null || value === '' || (Array.isArray(value) && !value.length)) continue
    if (typeof value !== 'string' && typeof value !== 'number') throw Error('Invalid authorization filter')
    query[key] = value
  }
  return query
}
function arrayLength(value: unknown) { return Array.isArray(value) ? value.length : 0 }
function objectSize(value: unknown) { return value && typeof value === 'object' && !Array.isArray(value) ? Object.keys(value).length : 0 }
export function getAuthConfigText(record: UiAuthListRecord): string {
  if (record.auth_type === 0) {
    const config = record.manual_config
    return [`Cookie ${arrayLength(config.cookies)}`, `本地存储 ${arrayLength(config.local_storage)}`, `会话存储 ${arrayLength(config.session_storage)}`, `请求头 ${objectSize(config.headers)}`].join('；')
  }
  if (record.auth_type === 1) {
    const config = record.auto_auth_config
    return [typeof config.url === 'string' && config.url ? config.url : '使用授权环境地址', `超时 ${config.timeout ?? 300}秒`, `Cookie域 ${arrayLength(config.cookie_domains)}`, `本地存储键 ${arrayLength(config.local_storage_keys)}`, `会话存储键 ${arrayLength(config.session_storage_keys)}`, `请求头 ${objectSize(config.headers)}`].join('；')
  }
  if (record.auth_type === 2) {
    const config = record.api_config, apiId = uiAuthId(config.api_info ?? config.api_info_id)
    return [`登录接口 ${apiId === null ? '-' : `#${apiId}`}`, `Token路径 ${typeof config.token_path === 'string' ? config.token_path || '-' : '-'}`, `Cookie映射 ${objectSize(config.cookie_mapping)}`, `本地存储映射 ${arrayLength(config.local_storage_mapping)}`, `会话存储映射 ${arrayLength(config.session_storage_mapping)}`, `请求头映射 ${objectSize(config.header_mapping)}`].join('；')
  }
  if (record.auth_type === 3) return record.page_step ? `${record.page_step.name || '页面步骤'}（#${record.page_step.id}）` : '-'
  return record.custom_code ? '已配置自定义代码' : '-'
}
export function getRefreshStrategyText(record: UiAuthListRecord): string {
  if (record.auth_type === 3) return '-'
  if (record.refresh_mode === 0) return '手动触发'
  if (record.refresh_mode === 1) return record.time_task?.name ? `定时策略：${record.time_task.name}` : '未配置定时策略'
  if (record.refresh_mode === 2) return `提前 ${record.expire_notice_minutes ?? '-'} 分钟；通知组：${record.notice_group?.name || '未配置通知组'}`
  return '-'
}
