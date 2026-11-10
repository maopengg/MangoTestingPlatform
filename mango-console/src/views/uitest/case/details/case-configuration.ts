import { cloneLosslessJson, stringifyLosslessJson } from '@/utils/lossless-json'
import { requiredUiCaseAssetId, uiCaseAssetId, uiCaseAssetObject, uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
import type { UiCaseFrontCustomItem, UiCaseFrontSqlItem, UiCasePosteriorSqlItem } from '@/types/ui-test/case'

export interface UiCaseConfiguration {
  front_custom: UiCaseFrontCustomItem[]
  front_sql: UiCaseFrontSqlItem[]
  posterior_sql: UiCasePosteriorSqlItem[]
  front_public: UiCaseAssetId[]
  front_auth_config: UiCaseAssetId[]
}
export interface UiCaseConfigurationRecord extends UiCaseConfiguration {
  id: UiCaseAssetId
  name: string
  project_product: { id: UiCaseAssetId; name: string } | null
}
export type UiCaseConfigurationMode = 'all' | 'globals'
export const emptyUiCaseConfiguration = (): UiCaseConfiguration => ({ front_custom: [], front_sql: [], posterior_sql: [], front_public: [], front_auth_config: [] })
function list(value: unknown): unknown[] { if (value == null || value === '') return []; if (!Array.isArray(value)) throw Error('Invalid case configuration list'); return value }
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid case configuration text'); return value }
function ids(value: unknown): UiCaseAssetId[] { return list(value).map(requiredUiCaseAssetId) }
function sql(value: unknown): string | Record<string, unknown> { return typeof value === 'string' ? value : cloneLosslessJson(uiCaseAssetObject(value)) }
function operation(value: unknown): UiCasePosteriorSqlItem {
  const row = uiCaseAssetObject(value)
  return { sql: sql(row.sql ?? ''), datasource_alias: uiCaseAssetId(row.datasource_alias), test_envs: ids(row.test_envs) }
}
function frontOperation(value: unknown): UiCaseFrontSqlItem {
  const row = uiCaseAssetObject(value), key = row.key_list
  if (key != null && typeof key !== 'string' && (!Array.isArray(key) || !key.every(item => typeof item === 'string'))) throw Error('Invalid SQL cache keys')
  return { ...operation(value), key_list: key == null ? key : typeof key === 'string' ? key : [...key] }
}
export function readUiCaseConfiguration(value: unknown): UiCaseConfiguration {
  const row = uiCaseAssetObject(value)
  return {
    front_custom: list(row.front_custom).map(value => { const item = uiCaseAssetObject(value); return { key: text(item.key), value: cloneLosslessJson(item.value === undefined ? '' : item.value), test_envs: ids(item.test_envs) } }),
    front_sql: list(row.front_sql).map(frontOperation), posterior_sql: list(row.posterior_sql).map(operation),
    front_public: ids(row.front_public), front_auth_config: ids(row.front_auth_config),
  }
}
export function readUiCaseConfigurationRecord(response: unknown, expectedId: UiCaseAssetId): UiCaseConfigurationRecord {
  const values = uiCaseAssetResponse(response)
  if (!Array.isArray(values) || values.length !== 1) throw Error('Case record not found')
  const row = uiCaseAssetObject(values[0]), id = requiredUiCaseAssetId(row.id)
  if (String(id) !== String(expectedId)) throw Error('Unexpected case record')
  const product = row.project_product == null ? null : typeof row.project_product === 'object' ? uiCaseAssetObject(row.project_product) : { id: row.project_product }
  return { ...readUiCaseConfiguration(row), id, name: text(row.name), project_product: product === null ? null : { id: requiredUiCaseAssetId(product.id), name: text(product.name) } }
}
export function uiCaseConfigurationPayload(record: UiCaseConfigurationRecord, draft: UiCaseConfiguration, mode: UiCaseConfigurationMode) {
  const current = readUiCaseConfiguration(draft)
  if (mode === 'globals') return { id: record.id, front_public: current.front_public, front_auth_config: current.front_auth_config }
  return { id: record.id, name: record.name, ...current }
}
export const uiCaseConfigurationSignature = (value: unknown) => stringifyLosslessJson(value)
export function firstUiCaseContextId(...values: unknown[]): UiCaseAssetId | null {
  for (const value of values) {
    if (value == null || value === '') continue
    try { return uiCaseAssetId(value) } catch { return null }
  }
  return null
}
export function bootstrapUiCaseContextId(value: unknown): UiCaseAssetId | null {
  try { return uiCaseAssetId(uiCaseAssetObject(value).id) } catch { return null }
}
