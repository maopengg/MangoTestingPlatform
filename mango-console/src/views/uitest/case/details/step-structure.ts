import { requiredUiCaseAssetId, uiCaseAssetObject, uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'

export type CaseStepStructureChange =
  | { kind: 'delete' | 'sync'; caseId: UiCaseAssetId; recordId: UiCaseAssetId }
  | { kind: 'sort'; caseId: UiCaseAssetId; order: UiCaseAssetId[] }

export function caseStepIds(value: unknown): UiCaseAssetId[] {
  if (!Array.isArray(value)) throw Error('Invalid case step IDs')
  const ids = value.map(requiredUiCaseAssetId)
  if (new Set(ids.map(String)).size !== ids.length) throw Error('Duplicate case step IDs')
  return ids
}

export function moveCaseStep(ids: UiCaseAssetId[], source: UiCaseAssetId, target: UiCaseAssetId): UiCaseAssetId[] {
  const order = caseStepIds(ids), from = order.findIndex(id => String(id) === String(source)), to = order.findIndex(id => String(id) === String(target))
  if (from < 0 || to < 0 || from === to) throw Error('Invalid case step move')
  const [id] = order.splice(from, 1); order.splice(to, 0, id)
  return order
}

export function caseStepSyncMessage(response: unknown, recordId: UiCaseAssetId): string {
  const data = uiCaseAssetResponse(response)
  if (!data || typeof data !== 'object' || Array.isArray(data)) return '同步完成'
  const rows = uiCaseAssetObject(data).updated
  if (!Array.isArray(rows)) return '同步完成'
  const row = rows.find(value => value && typeof value === 'object' && !Array.isArray(value) && String(uiCaseAssetObject(value).case_step_id) === String(recordId))
  if (!row) return '同步完成'
  const summary = uiCaseAssetObject(row)
  const fields = ['added_count', 'updated_count', 'removed_count', 'unchanged_count', 'initialized_count'] as const
  const counts = fields.map(key => summary[key])
  if (!counts.every(value => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0)) return '同步完成'
  return `同步完成：新增 ${counts[0]}，更新 ${counts[1]}，删除 ${counts[2]}，保留 ${Number(counts[3]) + Number(counts[4])}`
}
