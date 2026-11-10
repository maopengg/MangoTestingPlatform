import { cloneLosslessJson } from '@/utils/lossless-json'
import type { DataFactoryAnyFieldOverrides, DataFactoryEnumGeneratorConfig, DataFactoryFieldOverrides, DataFactoryFieldRule, DataFactoryGeneratorConfig } from '@/types/data-factory'
import { factoryConfigId, factoryConfigObject, readFactoryConfigTemplate, type FactoryConfigId, type FactoryConfigTemplate } from './case-config-record'

export interface FactoryEditorItem { id: FactoryConfigId | null; name: string; child_template: FactoryConfigId | null; child_template_detail: FactoryConfigTemplate | null; field_overrides: DataFactoryFieldOverrides }
export interface FactoryEditorTemplate extends FactoryConfigTemplate { items: FactoryEditorItem[]; field_overrides: DataFactoryAnyFieldOverrides }
export interface FactoryPreviewField extends DataFactoryFieldRule { value?: unknown; valid?: boolean; message?: string; display_value?: unknown; deferred?: boolean }
export interface FactoryMissingField { field: string; message: string }
export interface FactoryPreviewNode {
  template_id?: FactoryConfigId | null; template_name?: string; entity_id?: FactoryConfigId | null; entity_name?: string; table_name?: string
  alias?: string; field?: string; target_field?: string; action?: string; reused?: boolean; scene_item_id?: FactoryConfigId; scene_item_name?: string
  status?: string; strategy?: string; value?: unknown; message?: string; missing_count?: number; fields?: FactoryPreviewField[]; missing_fields?: FactoryMissingField[]; children?: FactoryPreviewNode[]
}
export interface FactoryEditorPreview { fields: FactoryPreviewField[]; items: Array<{ id: FactoryConfigId | null; name: string; template: { id: FactoryConfigId | null }; fields: FactoryPreviewField[] }>; dependency_tree: FactoryPreviewNode | null }
export interface FactoryEditorDraft {
  id: FactoryConfigId | null; source_type: number | undefined; source_id: FactoryConfigId | null | undefined
  project_product: FactoryConfigId | null | undefined; datasource_alias: FactoryConfigId | null; module: FactoryConfigId | null; template: FactoryConfigId | null
  name: string; sort: number; field_overrides: DataFactoryAnyFieldOverrides; cleanup_strategy: number | null; status: number; stage: number
}
const object = factoryConfigObject
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid factory text'); return value }
function number(value: unknown): number { if (typeof value !== 'number' || !Number.isFinite(value)) throw Error('Invalid factory number'); return value }
function list(value: unknown): unknown[] { if (value == null) return []; if (!Array.isArray(value)) throw Error('Invalid factory list'); return value }
function generator(value: unknown): DataFactoryGeneratorConfig {
  const row = object(value ?? {})
  for (const key of ['length', 'min', 'max', 'precision', 'days', 'hours', 'minutes']) if (row[key] != null) number(row[key])
  if (row.mode != null && row.mode !== 'fixed' && row.mode !== 'random') throw Error('Invalid generator mode')
  if (row.options != null) list(row.options).forEach(option => { object(option) })
  if (row.values != null) list(row.values)
  // 生成器 JSON 属于既有可扩展协议；验证公共结构后保留未消费的配置键。
  const result: DataFactoryEnumGeneratorConfig = {}
  Object.assign(result, cloneLosslessJson(row))
  return result
}
export function readFactoryRules(value: unknown): DataFactoryFieldOverrides {
  return Object.fromEntries(Object.entries(object(value ?? {})).map(([key, value]) => { const row = object(value); return [key, { generator_type: number(row.generator_type), generator_config: generator(row.generator_config) }] }))
}
export function readFactoryOverrides(value: unknown): DataFactoryAnyFieldOverrides {
  const row = object(value ?? {})
  if ('__main__' in row || '__items__' in row) return { __main__: readFactoryRules(row.__main__), __items__: Object.fromEntries(Object.entries(object(row.__items__ ?? {})).map(([key, value]) => [key, readFactoryRules(value)])) }
  return readFactoryRules(row)
}
export function factorySceneOverrides(value: DataFactoryAnyFieldOverrides): { __main__: DataFactoryFieldOverrides; __items__: Record<string, DataFactoryFieldOverrides> } {
  const row = object(value)
  return '__main__' in row || '__items__' in row ? { __main__: readFactoryRules(row.__main__), __items__: Object.fromEntries(Object.entries(object(row.__items__ ?? {})).map(([key, value]) => [key, readFactoryRules(value)])) } : { __main__: readFactoryRules(row), __items__: {} }
}
export function readFactoryEditorTemplates(values: unknown): FactoryEditorTemplate[] {
  return list(values).map(value => {
    const row = object(value), summary = readFactoryConfigTemplate(value)
    if (!summary) throw Error('Missing factory template')
    return { ...summary, field_overrides: readFactoryOverrides(row.field_overrides), items: list(row.items).map(value => { const item = object(value); return { id: factoryConfigId(item.id), name: text(item.name), child_template: factoryConfigId(item.child_template), child_template_detail: readFactoryConfigTemplate(item.child_template_detail), field_overrides: readFactoryRules(item.field_overrides) } }) }
  })
}
export function readFactoryFields(values: unknown): FactoryPreviewField[] {
  return list(values).map(value => {
    const row = object(value)
    const field: FactoryPreviewField = { name: text(row.name), label: text(row.label), db_type: text(row.db_type), platform_type: text(row.platform_type) }
    if (!field.name) throw Error('Missing factory field')
    if (row.id != null && typeof row.id === 'number') field.id = number(row.id)
    if (row.generator_type != null) field.generator_type = number(row.generator_type)
    if (row.generator_config != null) field.generator_config = generator(row.generator_config)
    if (row.enum_values != null) field.enum_values = cloneLosslessJson(list(row.enum_values))
    for (const key of ['nullable', 'primary_key', 'autoincrement', 'deferred', 'valid'] as const) { const value = row[key]; if (value != null) { if (typeof value !== 'boolean') throw Error('Invalid field flag'); field[key] = value } }
    if ('value' in row) field.value = cloneLosslessJson(row.value)
    if ('message' in row) field.message = text(row.message)
    if ('display_value' in row) field.display_value = cloneLosslessJson(row.display_value)
    return field
  })
}
function previewNode(value: unknown, depth = 0): FactoryPreviewNode | null {
  if (value == null) return null
  if (depth > 64) throw Error('Factory preview nesting limit')
  const row = object(value), result: FactoryPreviewNode = {}
  for (const key of ['template_id', 'entity_id', 'scene_item_id'] as const) if (row[key] != null) { const id = factoryConfigId(row[key]); if (id === null) throw Error('Invalid preview ID'); result[key] = id }
  for (const key of ['template_name', 'entity_name', 'table_name', 'alias', 'field', 'target_field', 'action', 'scene_item_name', 'status', 'strategy', 'message'] as const) if (row[key] != null) result[key] = text(row[key])
  if ('value' in row) result.value = cloneLosslessJson(row.value)
  if (row.reused != null) { if (typeof row.reused !== 'boolean') throw Error('Invalid preview flag'); result.reused = row.reused }
  if (row.missing_count != null) result.missing_count = number(row.missing_count)
  if (row.fields != null) result.fields = readFactoryFields(row.fields)
  if (row.missing_fields != null) result.missing_fields = list(row.missing_fields).map(value => { const item = object(value); return { field: text(item.field), message: text(item.message) } })
  if (row.children != null) result.children = list(row.children).flatMap(value => { const child = previewNode(value, depth + 1); return child ? [child] : [] })
  return result
}
export const emptyFactoryPreview = (): FactoryEditorPreview => ({ fields: [], items: [], dependency_tree: null })
export function readFactoryPreview(value: unknown): FactoryEditorPreview {
  const row = object(value)
  return { fields: readFactoryFields(row.fields), dependency_tree: previewNode(row.dependency_tree), items: list(row.items).map(value => { const item = object(value); return { id: factoryConfigId(item.id), name: text(item.name), template: { id: item.template && typeof item.template === 'object' ? factoryConfigId(object(item.template).id) : factoryConfigId(item.template) }, fields: readFactoryFields(item.fields) } }) }
}
