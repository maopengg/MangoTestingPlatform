import { requiredUiCaseAssetId, uiCaseAssetId, uiCaseAssetObject, uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'

interface Choice { value: UiCaseAssetId; name: string; disabled: boolean; statusText: string }
export interface UiCasePublicChoice extends Choice { key: string; type: UiCaseAssetId | null; testEnvs: UiCaseAssetId[]; isCommonEnv: boolean }
export interface UiCaseAuthChoice extends Choice { authType: UiCaseAssetId | null; testEnv: UiCaseAssetId | null; isCommonEnv: boolean }
export interface UiCaseDatasourceChoice { value: UiCaseAssetId; label: string; dbType: number }
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid case option label'); return value }
function rows(response: unknown): unknown[] { const data = uiCaseAssetResponse(response); if (!Array.isArray(data)) throw Error('Invalid case option list'); return data }
function environments(value: unknown): UiCaseAssetId[] { if (value == null || value === '') return []; return (Array.isArray(value) ? value : [value]).map(requiredUiCaseAssetId) }
function choice(value: unknown): Choice {
  const row = uiCaseAssetObject(value), status = row.status
  if (status !== 0 && status !== 1 && status !== '0' && status !== '1') throw Error('Invalid case option status')
  const disabled = status === 1 || status === '1'
  return { value: requiredUiCaseAssetId(row.id), name: text(row.name), disabled, statusText: disabled ? '默认开启' : '可选' }
}
export function readUiCasePublicChoices(response: unknown): UiCasePublicChoice[] {
  return rows(response).map(value => {
    const row = uiCaseAssetObject(value), base = choice(value), testEnvs = environments(row.test_envs)
    return { ...base, name: base.name || text(row.key) || `全局变量 ${base.value}`, key: text(row.key) || '-', type: uiCaseAssetId(row.type), testEnvs, isCommonEnv: testEnvs.length === 0 }
  })
}
export function readUiCaseAuthChoices(response: unknown): UiCaseAuthChoice[] {
  return rows(response).map(value => {
    const row = uiCaseAssetObject(value), base = choice(value), testEnv = uiCaseAssetId(row.test_env)
    return { ...base, name: base.name || `授权配置 ${base.value}`, authType: uiCaseAssetId(row.auth_type), testEnv, isCommonEnv: testEnv === null }
  })
}
export function readUiCaseDatasourceChoices(response: unknown): UiCaseDatasourceChoice[] {
  return rows(response).map(value => {
    const row = uiCaseAssetObject(value), type = requiredUiCaseAssetId(row.db_type), dbType = Number(type)
    if (!Number.isSafeInteger(dbType)) throw Error('Invalid datasource type')
    return { value: requiredUiCaseAssetId(row.id), label: text(row.name), dbType }
  })
}
