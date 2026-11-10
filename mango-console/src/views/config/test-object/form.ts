import { getOptionId } from '@/utils/business-format'
import { emptyTargetConfig, validateTargetConfig } from './target-config'
import type { TestTargetConfig } from './target-config'
import type { TargetId, TestObjectDraft, TestObjectRecord } from './types'
export function productId(value: unknown): TargetId | null {
  const id: unknown = getOptionId(value)
  return typeof id === 'number' || (typeof id === 'string' && id !== '') ? id : null
}
export function copyTargetConfig(config?: TestTargetConfig | null): TestTargetConfig {
  return {
    default: config?.default ?? '',
    selector: config?.selector ?? '',
    mapping: { ...config?.mapping },
  }
}
export function createTargetDraft(
  record?: TestObjectRecord,
  product: TargetId | null = null
): TestObjectDraft {
  return {
    project_product: record ? productId(record.project_product) : product,
    name: record?.name ?? '',
    environment: record?.environment ?? null,
    auto_type: record?.auto_type ?? null,
    legacyMode: Boolean(record?.value),
    legacyValue: record?.value ?? '',
    targetConfig: copyTargetConfig(record?.target_config),
  }
}
export function validateTargetDraft(draft: TestObjectDraft): string {
  if (productId(draft.project_product) === null) return '请选择项目产品'
  if (!draft.name) return '请输入环境名称'
  if (draft.environment == null || draft.environment === '') return '请选择被测环境'
  if (draft.auto_type == null || draft.auto_type === '') return '请选择产品的端类型'
  return draft.legacyMode
    ? draft.legacyValue
      ? ''
      : '请填写历史地址'
    : validateTargetConfig(draft.targetConfig)
}
export function targetPayload(draft: TestObjectDraft) {
  const base = {
    project_product: productId(draft.project_product),
    name: draft.name,
    environment: draft.environment,
    auto_type: draft.auto_type,
    value: draft.legacyMode ? draft.legacyValue : '',
  }
  return draft.legacyMode ? base : { ...base, target_config: copyTargetConfig(draft.targetConfig) }
}
export function switchTargetConfig(draft: TestObjectDraft) {
  draft.targetConfig = { ...emptyTargetConfig(), default: draft.legacyValue }
  draft.legacyMode = false
}
