import { getOptionId } from '@/utils/business-format'
import type { PublicDraft, PublicEntityId, PublicEnvironment, PublicRecord } from './types'
import { COMMON_ENV_VALUE, codeVariableExample } from './config'
export function normalizeEnvironmentList(value: unknown): PublicEnvironment[] {
  const items = Array.isArray(value) ? value : value == null || value === '' ? [] : [value]
  return items.filter(
    (item): item is PublicEnvironment => typeof item === 'string' || typeof item === 'number'
  )
}
export function normalizeEnvironmentSelection(values: PublicEnvironment[]): PublicEnvironment[] {
  if (!values.length) return [COMMON_ENV_VALUE]
  if (values.includes(COMMON_ENV_VALUE))
    return values.at(-1) === COMMON_ENV_VALUE
      ? [COMMON_ENV_VALUE]
      : values.filter((value) => value !== COMMON_ENV_VALUE)
  return [...values]
}
export function normalizeEnvironmentValues(value: unknown): number[] {
  const list = normalizeEnvironmentList(value)
  if (list.includes(COMMON_ENV_VALUE)) return []
  return [
    ...new Set(
      list
        .filter((value) => value !== '')
        .map(Number)
        .filter(Number.isInteger)
    ),
  ]
}
export function environmentSelectValue(record?: PublicRecord): PublicEnvironment[] {
  const values = normalizeEnvironmentList(record?.test_envs)
  if (values.length) return [...values]
  const legacy = normalizeEnvironmentList(record?.test_env)
  return legacy.length ? legacy : [COMMON_ENV_VALUE]
}
export function createPublicDraft(
  record?: PublicRecord,
  product: PublicEntityId | null = null
): PublicDraft {
  return {
    project_product: record ? getOptionId(record.project_product) : product,
    type: record?.type ?? null,
    test_envs: environmentSelectValue(record),
    name: record?.name ?? '',
    key: record?.key ?? '',
    value: record?.value ?? '',
    datasource_alias: record ? getOptionId(record.datasource_alias) : null,
  }
}
export function publicPayload(draft: PublicDraft) {
  return {
    project_product: getOptionId(draft.project_product),
    type: draft.type,
    test_envs: normalizeEnvironmentValues(draft.test_envs),
    name: draft.name,
    key: draft.key,
    value: draft.type === 2 && !draft.value ? codeVariableExample : draft.value,
    datasource_alias: draft.type === 1 ? draft.datasource_alias : null,
  }
}
export function publicValidation(draft: PublicDraft) {
  const product = getOptionId(draft.project_product)
  if (product == null || product === '') return '请选择项目/产品'
  if (draft.type == null || ![0, 1, 2].includes(draft.type)) return '请选择变量类型'
  if (!draft.name.trim()) return '请输入参数名称'
  if (!draft.key.trim()) return '请输入变量 key'
  if (!draft.value) return draft.type === 2 ? '请输入自定义代码' : '请输入变量值'
  if (draft.type === 1 && (draft.datasource_alias == null || draft.datasource_alias === ''))
    return 'SQL公共变量必须选择逻辑数据库'
  return ''
}
