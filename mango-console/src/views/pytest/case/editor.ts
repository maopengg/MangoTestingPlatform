import { batchId, batchSuccess, batchValues, readBatchRows, validateBatchRows } from './batch-editor'
import type { BatchRow, BatchValues } from './batch-editor'
import type { ProjectProductOption } from '@/store/modules/project-options'

export interface CaseEditorRecord extends BatchRow { pytestProjectId: number | null }
export interface CaseEditorDraft extends BatchValues { project_product: number | null }
export function emptyCaseDraft(): CaseEditorDraft {
  return { project_product: null, name: '', module: null, asset_status: 0, level: null,
    scenario_layer: 0, scenario_type: 0, scenario_tags: [], scenario_description: '', case_people: null }
}
export function caseEditorRecord(value: unknown): CaseEditorRecord {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('用例格式不正确')
  const raw = value as Record<string, unknown>, id = batchId(raw.id)
  const row = readBatchRows({ code: 200, data: [raw] }, [id])[0]
  const product = raw.project_product
  if (product != null && (typeof product !== 'object' || Array.isArray(product))) throw new Error('项目格式不正确')
  return { ...row, pytestProjectId: product == null ? null : batchId((product as Record<string, unknown>).id) }
}
export function caseDraft(record: CaseEditorRecord): CaseEditorDraft {
  return { ...batchValues(record), name: record.name, project_product: record.pytestProjectId }
}
export function selectedPytestProject(value: unknown, options: ProjectProductOption[]): number {
  const id = batchId(Array.isArray(value) ? value[value.length - 1] : value)
  if (!options.some(project => project.children?.some(product => String(product.value) === String(id)))) throw new Error('请选择有效的项目/产品')
  return id
}
export function caseEditorPayload(draft: CaseEditorDraft, record: CaseEditorRecord, options: ProjectProductOption[]) {
  const project_product = selectedPytestProject(draft.project_product, options)
  const row = { ...record, ...draft }
  const error = validateBatchRows([row])
  if (error) throw new Error(error)
  return { id: record.id, project_product, ...batchValues(row) }
}
export function checkCaseSave(value: unknown): void { batchSuccess(value) }
