import { requiredUiCaseAssetId, uiCaseAssetId, uiCaseAssetObject, uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'

interface NamedAsset { id: UiCaseAssetId; name: string }
export interface CasePageStep extends NamedAsset {
  page: NamedAsset | null
  module: { id: UiCaseAssetId; name: string; full_path: string } | null
  project_product: (NamedAsset & { project: NamedAsset | null; ui_client_type: number | null }) | null
}
export interface CaseStepRow {
  id: UiCaseAssetId
  name: string
  page_step: CasePageStep | null
  case_data: unknown[]
  status: number
  error_message: string | null
  error_retry: number | null
  switch_step_open_url: 0 | 1
}
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid step text'); return value }
function integer(value: unknown): number { const number = typeof value === 'number' ? value : typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : NaN; if (!Number.isSafeInteger(number) || number < 0) throw Error('Invalid step number'); return number }
function named(value: unknown): NamedAsset | null {
  if (value == null) return null
  if (typeof value !== 'object') { const id = uiCaseAssetId(value); return id === null ? null : { id, name: '' } }
  const row = uiCaseAssetObject(value)
  return { id: requiredUiCaseAssetId(row.id), name: text(row.name) }
}
export function readCasePageStep(value: unknown): CasePageStep | null {
  const asset = named(value)
  if (!asset) return null
  const row = typeof value === 'object' ? uiCaseAssetObject(value) : {}
  const product = named(row.project_product), module = named(row.module)
  const productRow = product && typeof row.project_product === 'object' ? uiCaseAssetObject(row.project_product) : {}
  const moduleRow = module && typeof row.module === 'object' ? uiCaseAssetObject(row.module) : {}
  return {
    ...asset, page: named(row.page),
    module: module ? { ...module, full_path: text(moduleRow.full_path) || module.name } : null,
    project_product: product ? { ...product, project: named(productRow.project), ui_client_type: productRow.ui_client_type == null ? null : integer(productRow.ui_client_type) } : null,
  }
}
export function readCaseStepRows(response: unknown, caseId: UiCaseAssetId): CaseStepRow[] {
  const data = uiCaseAssetResponse(response)
  if (!Array.isArray(data)) throw Error('Invalid case steps')
  const rows = data.map((value): CaseStepRow => {
    const row = uiCaseAssetObject(value), owner = named(row.case)
    if (!owner || String(owner.id) !== String(caseId)) throw Error('Unexpected case steps')
    const status = integer(row.status), switchValue = integer(row.switch_step_open_url)
    if (switchValue !== 0 && switchValue !== 1) throw Error('Invalid case step status')
    if (row.case_data != null && !Array.isArray(row.case_data)) throw Error('Invalid case step inputs')
    return {
      id: requiredUiCaseAssetId(row.id), name: text(row.name), page_step: readCasePageStep(row.page_step),
      case_data: row.case_data == null ? [] : row.case_data.slice(), status,
      error_message: row.error_message == null ? null : text(row.error_message),
      error_retry: row.error_retry == null ? null : integer(row.error_retry), switch_step_open_url: switchValue,
    }
  })
  if (new Set(rows.map(row => String(row.id))).size !== rows.length) throw Error('Duplicate case steps')
  return rows
}
export function mergeActiveCaseSteps(incoming: CaseStepRow[], previous: CaseStepRow[]): CaseStepRow[] {
  const currentById = new Map(previous.map(row => [String(row.id), row]))
  return incoming.map(row => {
    const current = currentById.get(String(row.id))
    if (!current) return row
    const incomingTerminal = [0, 1].includes(row.status)
    const status = [0, 1].includes(current.status) ? current.status
      : current.status === 3 && incomingTerminal ? row.status
      : current.status === 3 || row.status === 3 ? 3 : 2
    return { ...row, status, error_message: current.status === 3 && incomingTerminal && row.error_message ? row.error_message : current.error_message || row.error_message }
  })
}
