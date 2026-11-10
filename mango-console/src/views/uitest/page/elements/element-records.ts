import { readElementEditor, type ElementEditorDraft } from '@/components/business/ui-element-editor'
import { liveId, liveObject, readLiveResult, type LiveId } from '@/components/business/ui-live-workbench'

export type ElementRow = Omit<ElementEditorDraft, 'id'> & { id: LiveId; ai_heal_status: number; update_user: { name: string; username: string } | null; update_time: string }
export interface ElementPage { id: LiveId; name: string; url: string; project_product: { id: LiveId; ui_client_type: LiveId } | null }
export interface ElementCategory { key: string; title: string; count: number }
export interface ElementScope { available: () => boolean; capture: () => () => boolean }
export function elementId(value: unknown): LiveId | null {
  return liveId(Array.isArray(value) ? value[0] : value)
}
export function requiredElementId(value: unknown): LiveId {
  const id = liveId(value); if (id === null) throw Error('返回记录缺少有效ID'); return id
}
export function elementResponse(response: unknown): unknown {
  const row = liveObject(response)
  if (row.code != null && row.code !== 200) throw Error('请求未成功，请重试')
  return row.data
}
export function readElementRow(value: unknown): ElementRow {
  const row = liveObject(value), user = liveObject(row.update_user)
  return { ...readElementEditor(row), id: requiredElementId(row.id), ai_heal_status: Number(row.ai_heal_status ?? 0), update_user: row.update_user ? { name: String(user.name ?? ''), username: String(user.username ?? '') } : null, update_time: String(row.update_time ?? '') }
}
export function readElementPage(value: unknown, expected: LiveId): ElementPage {
  const row = liveObject(value), product = liveObject(row.project_product), id = requiredElementId(row.id)
  if (String(id) !== String(expected)) throw Error('页面数据与当前页面不匹配')
  return { id, name: String(row.name ?? ''), url: String(row.url ?? ''), project_product: liveId(product.id) === null ? null : { id: requiredElementId(product.id), ui_client_type: liveId(product.ui_client_type) ?? 0 } }
}
export function readElementList(response: unknown) {
  const data = elementResponse(response), total = liveObject(response).totalSize
  if (!Array.isArray(data) || typeof total !== 'number' || !Number.isSafeInteger(total) || total < 0) throw Error('元素列表返回格式不正确')
  const rows = data.map(readElementRow)
  if (new Set(rows.map(row => String(row.id))).size !== rows.length) throw Error('元素列表存在重复ID')
  return { rows, total }
}
export function readElementCategories(response: unknown): ElementCategory[] {
  const rows = elementResponse(response)
  if (!Array.isArray(rows)) throw Error('元素分类返回格式不正确')
  return rows.map(value => { const row = liveObject(value); if (typeof row.key !== 'string' || typeof row.title !== 'string') throw Error('元素分类返回格式不正确'); return { key: row.key, title: row.title, count: Number(row.count ?? 0) } })
}
export function elementDescriptionSummary(record: ElementRow) {
  return [record.location_description ? `识别线索：${record.location_description.trim()}` : '', record.surrounding_text ? `排除：${record.surrounding_text.trim()}` : ''].filter(Boolean).join('；') || record.prompt.trim() || '-'
}
export function getLocatorGroup(row: ElementRow, group: number) {
  return group === 2 ? { exp: row.exp2, loc: row.loc2, sub: row.sub2 } : group === 3 ? { exp: row.exp3, loc: row.loc3, sub: row.sub3 } : { exp: row.exp, loc: row.loc, sub: row.sub }
}
export function getLocatorRuntime(row: ElementRow, group: number) {
  const snapshot = readLiveResult(row.latest_runtime_snapshot)
  const runtime = snapshot.locator_groups?.find((item, index) => Number(item.group ?? index + 1) === group)
  return { count: runtime?.count ?? (group === 1 ? row.latest_match_count : null), elementText: runtime?.element_text || (group === 1 ? row.latest_element_text : '') }
}
export function expectedEventParamSummary(event: ElementEditorDraft['expected_event']) {
  return event.ope_value.filter(item => item.v !== undefined && item.v !== null && item.v !== '').map(item => `${item.n || item.f}=${typeof item.v === 'object' ? JSON.stringify(item.v) : String(item.v)}`).join('；')
}
