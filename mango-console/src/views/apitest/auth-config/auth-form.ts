import type { AuthDraft, AuthRecord, EntityId } from './types'

export const customAuthCodeExample = `def auth(context):
    """函数名和参数保持不变；返回 dict，接口通过 \${token} 等变量引用。"""
    return {"token": "your_token"}`

function referenceId(value: { id: number } | number | null | undefined) {
  return typeof value === 'object' ? value?.id ?? null : value ?? null
}

export function createAuthDraft(
  record?: AuthRecord,
  environment: number | null = null,
  product: EntityId | null = null
): AuthDraft {
  return {
    name: record?.name ?? '',
    project_product: record ? referenceId(record.project_product) : product,
    test_env: record?.test_env ?? environment,
    auth_type: record?.auth_type ?? 0,
    api_info: referenceId(record?.api_info),
    target_address: record?.target_address ?? '',
    public_variable_ids: [...(record?.public_variable_ids ?? [])],
    custom_code: record?.custom_code ?? (record ? '' : customAuthCodeExample),
    refresh_mode: record?.refresh_mode ?? 0,
    token_ttl: record?.token_ttl ?? 1440,
    refresh_margin: record?.refresh_margin ?? 10,
    expire_notice_minutes: record?.expire_notice_minutes ?? 30,
    time_task: referenceId(record?.time_task),
    notice_group: referenceId(record?.notice_group),
  }
}

export function normalizeSubmitValue(draft: AuthDraft) {
  const product = Array.isArray(draft.project_product)
    ? draft.project_product.slice(-1)[0]
    : draft.project_product
  return {
    ...draft,
    project_product: product,
    target_address: draft.target_address ?? '',
    public_variable_ids: [...(draft.public_variable_ids ?? [])],
    custom_code: draft.auth_type === 0 ? null : draft.custom_code,
    api_info: draft.auth_type === 1 ? null : draft.api_info,
    time_task: [1, 2].includes(draft.refresh_mode) ? draft.time_task : null,
    notice_group: draft.refresh_mode === 4 ? draft.notice_group : null,
  }
}
