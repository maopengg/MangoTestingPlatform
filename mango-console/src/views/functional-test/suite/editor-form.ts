export type SuiteSelection = number | string | null
export type SuiteProductSelection = SuiteSelection | Array<number | string>
export type SuiteEditRelation = SuiteSelection | { id: number; name?: string; username?: string }
export interface SuiteEditRecord {
  id: number
  requirement_name?: string
  requirement?: SuiteEditRelation
  project_product?: SuiteEditRelation
  module?: SuiteEditRelation
  owner?: SuiteEditRelation
  iteration_ref?: SuiteEditRelation
  development_owner?: SuiteEditRelation
  priority?: number | null
  status?: number | null
  planned_start_date?: string | null
  planned_submit_date?: string | null
}
export interface SuiteEditorForm {
  requirement_name: string
  project_product: SuiteProductSelection
  module: SuiteSelection
  owner: SuiteSelection
  iteration_ref: SuiteSelection
  development_owner: SuiteSelection
  priority: number | null
  status: number | null
  planned_start_date: string | null
  planned_submit_date: string | null
}
export type SuiteEditorMode = 'create' | 'edit' | 'version'
export interface SuiteEditorDefaults {
  projectProduct: SuiteSelection
  module: SuiteSelection
}
export interface SuiteEditorHandle {
  open(mode: SuiteEditorMode, record?: SuiteEditRecord, defaults?: SuiteEditorDefaults): void
}
export function suiteSelectionId(
  value: SuiteEditRelation | SuiteProductSelection | undefined
): number | null {
  const leaf = Array.isArray(value) ? value[value.length - 1] : value
  const scalar = leaf !== null && typeof leaf === 'object' ? leaf.id : leaf
  if (
    (typeof scalar !== 'string' && typeof scalar !== 'number') ||
    (typeof scalar === 'string' && !/^\d+$/.test(scalar))
  )
    return null
  const id = Number(scalar)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
export function createSuiteEditorForm(
  mode: SuiteEditorMode,
  record?: SuiteEditRecord,
  defaults?: SuiteEditorDefaults
): SuiteEditorForm {
  return {
    requirement_name: record?.requirement_name ?? '',
    project_product: record
      ? suiteSelectionId(record.project_product)
      : suiteSelectionId(defaults?.projectProduct),
    module: record ? suiteSelectionId(record.module) : suiteSelectionId(defaults?.module),
    owner: suiteSelectionId(record?.owner),
    iteration_ref: suiteSelectionId(record?.iteration_ref),
    development_owner: suiteSelectionId(record?.development_owner),
    priority: record?.priority ?? 1,
    status: mode === 'version' ? 1 : record?.status ?? 1,
    planned_start_date: mode === 'version' ? null : record?.planned_start_date || null,
    planned_submit_date: mode === 'version' ? null : record?.planned_submit_date || null,
  }
}
export function suiteEditorPayload(
  form: SuiteEditorForm,
  mode: SuiteEditorMode,
  record: SuiteEditRecord | null
) {
  return {
    ...(mode === 'edit' ? { id: record!.id } : {}),
    ...(mode === 'version'
      ? {
          requirement: suiteSelectionId(record!.requirement),
          previous_version: record!.id,
          iteration: '',
        }
      : {}),
    requirement_name: form.requirement_name,
    project_product: suiteSelectionId(form.project_product),
    module: suiteSelectionId(form.module),
    owner: suiteSelectionId(form.owner),
    iteration_ref: suiteSelectionId(form.iteration_ref),
    development_owner: suiteSelectionId(form.development_owner),
    priority: form.priority,
    status: form.status,
    planned_start_date: form.planned_start_date || null,
    planned_submit_date: form.planned_submit_date || null,
  }
}
export function suiteEditorValidation(form: SuiteEditorForm): string | null {
  if (!form.requirement_name.trim()) return '请输入需求名称'
  if (!suiteSelectionId(form.project_product)) return '请选择项目产品'
  if (!suiteSelectionId(form.module)) return '请选择模块名称'
  if (!suiteSelectionId(form.iteration_ref)) return '请选择所属 Sprint'
  if (!suiteSelectionId(form.owner)) return '请选择测试负责人'
  return null
}
