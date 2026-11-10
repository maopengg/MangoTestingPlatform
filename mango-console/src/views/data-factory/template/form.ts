import { getOptionId } from '@/utils/business-format'
import type { TemplateRecord, TemplateDraft, NavigationDefaults, Reference } from './types'
export function optionId(value: unknown): string | number | null {
  const id: unknown = getOptionId(value)
  return typeof id === 'number' || (typeof id === 'string' && id !== '') ? id : null
}
function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value))
}
export const createDraft = (
  record?: TemplateRecord,
  defaults?: NavigationDefaults
): TemplateDraft => ({
  project_product: record ? optionId(record.project_product) : defaults?.projectProduct ?? null,
  module: record ? optionId(record.module) : defaults?.module ?? null,
  entity: optionId(record?.entity),
  name: record?.name ?? '',
  description: record?.description ?? '',
  field_overrides: clone(record?.field_overrides ?? {}),
  output_config: clone(record?.output_config ?? []),
  cleanup_strategy: record?.cleanup_strategy ?? 1,
  is_default: record?.is_default ?? false,
  usage_scope: Number(record?.usage_scope) === 2 ? 2 : 1,
  status: record?.status ?? 1,
})
export function templatePayload(form: TemplateDraft) {
  return {
    project_product: optionId(form.project_product),
    module: optionId(form.module),
    entity: optionId(form.entity),
    name: form.name,
    description: form.description,
    field_overrides: clone(form.field_overrides),
    output_config: clone(form.output_config),
    cleanup_strategy: form.cleanup_strategy,
    is_default: form.is_default,
    usage_scope: form.usage_scope,
    status: form.status,
  }
}
export function validateDraft(form: TemplateDraft) {
  return optionId(form.project_product) === null ||
    optionId(form.module) === null ||
    optionId(form.entity) === null ||
    !form.name.trim() ||
    !form.usage_scope
    ? '请先填写产品、模块名称、实体名称、场景名称和场景用途'
    : ''
}
export function formatEntityLabel(entity?: Reference | string | number | null): string {
  if (entity == null || entity === '') return '-'
  if (typeof entity !== 'object') return String(entity)
  const table = entity.table_name?.trim(),
    name = entity.name?.trim()
  return table && name && table !== name
    ? `${table}（${name}）`
    : table || name || String(entity.id)
}
export function filterEntityOption(input: string, option: unknown): boolean {
  if (!option || typeof option !== 'object') return false
  const data = 'raw' in option ? option.raw : 'data' in option ? option.data : option
  if (!data || typeof data !== 'object') return false
  return Object.entries(data).some(
    ([key, value]) =>
      ['table_name', 'name', 'display_name', 'label'].includes(key) &&
      String(value ?? '')
        .toLowerCase()
        .includes(input.trim().toLowerCase())
  )
}
export function enumTitle(
  options: Array<{ key: string | number; title: string }> = [],
  value: number | string
) {
  return options.find((item) => String(item.key) === String(value))?.title ?? String(value)
}
