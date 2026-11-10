export type UiCaseAssetId = number | string
export interface UiCaseAssetOption { value: UiCaseAssetId; label: string; children?: UiCaseAssetOption[] }
export interface UiCaseAssetStep { stepId: UiCaseAssetId; stepName: string; pageId: UiCaseAssetId; pageName: string; moduleId: UiCaseAssetId; productId: UiCaseAssetId }
export function uiCaseAssetObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid case step asset')
  return value as Record<string, unknown>
}
export function uiCaseAssetId(value: unknown): UiCaseAssetId | null {
  if (Array.isArray(value)) return uiCaseAssetId(value[value.length - 1])
  if (value == null || value === '') return null
  if (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) return value
  if (typeof value === 'string' && /^\d+$/.test(value)) return value
  throw Error('Invalid case step asset ID')
}
export function requiredUiCaseAssetId(value: unknown): UiCaseAssetId {
  const id = uiCaseAssetId(value)
  if (id === null) throw Error('Missing case step asset ID')
  return id
}
export function uiCaseAssetResponse(response: unknown): unknown {
  const value = uiCaseAssetObject(response)
  if (value.code !== 200) throw Error('Case step request failed')
  return value.data
}
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid asset name'); return value }
function list(value: unknown): unknown[] { if (!Array.isArray(value)) throw Error('Invalid asset list'); return value }
export function readUiCaseAssetProducts(response: unknown): UiCaseAssetOption[] {
  return list(uiCaseAssetResponse(response)).map(value => {
    const row = uiCaseAssetObject(value), key = row.value ?? row.key
    if (typeof key !== 'string' || !/^project:\d+$/.test(key)) throw Error('Invalid project option')
    return { value: key, label: text(row.label ?? row.title), children: list(row.children).map(value => {
      const child = uiCaseAssetObject(value)
      return { value: requiredUiCaseAssetId(child.value ?? child.key), label: text(child.label ?? child.title) }
    }) }
  })
}
export function readUiCaseAssetModules(response: unknown, productId: UiCaseAssetId): UiCaseAssetOption[] {
  return list(uiCaseAssetResponse(response)).map(value => {
    const row = uiCaseAssetObject(value)
    if (String(requiredUiCaseAssetId(row.project_product_id)) !== String(productId)) throw Error('Unexpected module product')
    return { value: requiredUiCaseAssetId(row.value ?? row.key), label: text(row.label ?? row.title) }
  })
}
export function readUiCaseAssetSteps(response: unknown, productId: UiCaseAssetId, moduleId: UiCaseAssetId): UiCaseAssetStep[] {
  const rows = list(uiCaseAssetResponse(response)).map(value => {
    const row = uiCaseAssetObject(value), product = requiredUiCaseAssetId(row.project_product_id), module = requiredUiCaseAssetId(row.module_id)
    if (String(product) !== String(productId) || String(module) !== String(moduleId)) throw Error('Unexpected step scope')
    return { stepId: requiredUiCaseAssetId(row.step_id), stepName: text(row.step_name), pageId: requiredUiCaseAssetId(row.page_id), pageName: text(row.page_name), moduleId: module, productId: product }
  })
  if (new Set(rows.map(row => String(row.stepId))).size !== rows.length) throw Error('Duplicate step options')
  return rows
}
export function uiCaseAssetStepOptions(steps: UiCaseAssetStep[]): UiCaseAssetOption[] {
  const pages = new Map<string, UiCaseAssetOption>()
  for (const step of steps) {
    const key = `page:${step.pageId}`
    if (!pages.has(key)) pages.set(key, { value: key, label: step.pageName, children: [] })
    pages.get(key)?.children?.push({ value: step.stepId, label: step.stepName })
  }
  return [...pages.values()]
}
export function uiCaseAssetCreatePayload(caseId: UiCaseAssetId, step: UiCaseAssetStep, count: number) {
  if (!Number.isSafeInteger(count) || count < 0) throw Error('Invalid case step count')
  return { case: requiredUiCaseAssetId(caseId), module: step.moduleId, page: step.pageId, page_step: step.stepId, case_cache_data: [], case_cache_ass: [], case_sort: count }
}
