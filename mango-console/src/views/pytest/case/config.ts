import { reactive } from 'vue'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import type { BatchOptionId } from './batch-editor'

export type TextSearchKey = 'id' | 'name' | 'file_path'
export type MultiSearchKey = 'publication_status' | 'status' | 'source_status' | 'asset_status' | 'level' | 'case_people'
export type SearchItem = { key: TextSearchKey; label: string; type: 'input'; placeholder: string; value: string } |
  { key: MultiSearchKey; label: string; type: 'select'; placeholder: string; value: BatchOptionId[]; multiple: true; searchOperator: 'in' }
export type CaseQuery = Partial<Record<TextSearchKey | 'id__in' | `${MultiSearchKey}__in` | 'module_ids', string>> & { project_product_id?: BatchOptionId }
const textFields: Array<{ key: TextSearchKey; label: string }> = [
  { key: 'id', label: 'ID' }, { key: 'name', label: '用例名称' }, { key: 'file_path', label: '文件路径' },
]
const selectFields: Array<{ key: MultiSearchKey; label: string }> = [
  { key: 'publication_status', label: '发布状态' }, { key: 'status', label: '测试结果' },
  { key: 'source_status', label: '源码状态' }, { key: 'asset_status', label: '资产状态' },
  { key: 'level', label: '优先级' }, { key: 'case_people', label: '用例负责人' },
]
export function createSearchItems(): SearchItem[] {
  const items: SearchItem[] = reactive([
    ...textFields.map(field => ({ ...field, type: 'input' as const, placeholder: `请输入${field.label}`, value: field.key === 'id' ? createIdSearchValue() : '' })),
    ...selectFields.map(field => ({ ...field, type: 'select' as const, placeholder: `请选择${field.label}`, value: [] as BatchOptionId[], multiple: true as const, searchOperator: 'in' as const })),
  ])
  enableMultiSelectSearch(items)
  return items
}
export function searchQuery(items: SearchItem[]): CaseQuery {
  const query: CaseQuery = {}
  for (const item of items) {
    if (item.type === 'input') { if (item.value !== '') query[item.key] = item.value }
    else if (item.value.length) query[`${item.key}__in`] = [...new Set(item.value)].join(',')
  }
  if (typeof query.id === 'string' && query.id.includes(',')) { query.id__in = [...new Set(query.id.split(',').filter(Boolean))].join(','); delete query.id }
  return query
}
export function resetSearchItems(items: SearchItem[]): void {
  for (const item of items) { if (item.type === 'input') item.value = ''; else item.value = [] }
}
