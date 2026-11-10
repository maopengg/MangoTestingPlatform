import { getOptionId } from '@/utils/business-format'
import type { TemplateDraft, TemplateRecord, SceneItem } from './types'
export function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value))
}
export function optionId(value: unknown): string | number | null {
  const id: unknown = getOptionId(value)
  return typeof id === 'number' || (typeof id === 'string' && id !== '') ? id : null
}
let clientId = 0
export function normalizeLoadedItems(items: SceneItem[]): SceneItem[] {
  return items
    .map((item, index) => ({
      id: item.id ?? null,
      _key: item._key ?? `scene-${++clientId}`,
      child_template: optionId(item.child_template),
      child_template_detail: item.child_template_detail ? clone(item.child_template_detail) : null,
      name: item.name || item.child_template_detail?.name || '',
      sort: item.sort ?? index * 10,
      field_overrides: clone(item.field_overrides ?? {}),
    }))
    .sort((a, b) => a.sort - b.sort)
}
export function createDraft(
  record?: TemplateRecord | null,
  id: string | number | null = null
): TemplateDraft {
  return {
    id: record?.id ?? id,
    project_product: optionId(record?.project_product),
    module: optionId(record?.module),
    entity: optionId(record?.entity),
    name: record?.name ?? '',
    description: record?.description ?? '',
    cleanup_strategy: record?.cleanup_strategy ?? 1,
    is_default: record?.is_default ?? false,
    config_status: record?.config_status ?? 0,
    status: record?.status ?? 1,
    field_overrides: clone(record?.field_overrides ?? {}),
    output_config: clone(record?.output_config ?? []),
    post_insert_updates: clone(record?.post_insert_updates ?? []),
    cleanup_resources: clone(record?.cleanup_resources ?? []),
    items: normalizeLoadedItems(record?.items ?? []),
  }
}
