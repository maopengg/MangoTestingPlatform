import { objectValue, resourceId } from './resource-form'

export type CaseSelection = number | string | null
export type ProductSelection = CaseSelection | Array<number | string>
export type SuiteRelation = CaseSelection | { id: number; name?: string; username?: string }
export interface SuiteCaseForm {
  id: number | null
  version_no: number | null
  case_no: string
  title: string
  project_product: ProductSelection
  module: CaseSelection
  owner: CaseSelection
  priority: number | null
  test_types: number[]
  scenario_layer: number | null
  scenario_type: number | null
  scenario_tags: string[]
  precondition: string
  test_point: string
  test_data: string
  remark: string
}
export type SuiteCaseRecord = Partial<
  Omit<SuiteCaseForm, 'project_product' | 'module' | 'owner'>
> & {
  id: number
  suite: SuiteRelation
  project_product?: SuiteRelation
  module?: SuiteRelation
  owner?: SuiteRelation
}
export interface SuiteCaseDefaults {
  productId: number | null
  moduleId: number | null
  ownerId: number | null
}
export interface SuiteCaseEditorHandle {
  open(record?: SuiteCaseRecord): void
}
export interface SuiteBindingHandle {
  open(record: SuiteCaseRecord, type: number): void
}
export function relationId(value: SuiteRelation | ProductSelection | undefined): number | null {
  if (Array.isArray(value)) return resourceId(value[value.length - 1])
  if (value !== null && typeof value === 'object') return resourceId(value.id)
  return resourceId(value)
}
export function createSuiteCaseForm(
  defaults?: SuiteCaseDefaults,
  record?: SuiteCaseRecord
): SuiteCaseForm {
  return {
    id: record?.id ?? null,
    version_no: record?.version_no ?? null,
    case_no: record?.case_no ?? '',
    title: record?.title ?? '',
    project_product: record ? relationId(record.project_product) : defaults?.productId ?? null,
    module: record ? relationId(record.module) : defaults?.moduleId ?? null,
    owner: record ? relationId(record.owner) : defaults?.ownerId ?? null,
    priority: record?.priority ?? 1,
    test_types: [...(record?.test_types ?? [0])],
    scenario_layer: record?.scenario_layer ?? 0,
    scenario_type: record?.scenario_type ?? 0,
    scenario_tags: [...(record?.scenario_tags ?? [])],
    precondition: record?.precondition ?? '',
    test_point: record?.test_point ?? '',
    test_data: record?.test_data ?? '',
    remark: record?.remark ?? '',
  }
}
export function suiteCasePayload(form: SuiteCaseForm, suiteId: number) {
  // Keep unexposed asset fields unchanged by submitting only this editor's fields.
  return {
    ...(form.id === null ? {} : { id: form.id }),
    ...(form.id === null || form.version_no === null ? {} : { version_no: form.version_no }),
    suite: suiteId,
    case_no: form.case_no,
    title: form.title,
    project_product: relationId(form.project_product),
    module: relationId(form.module),
    owner: relationId(form.owner),
    priority: form.priority,
    test_types: [...form.test_types],
    scenario_layer: form.scenario_layer,
    scenario_type: form.scenario_type,
    scenario_tags: [...form.scenario_tags],
    precondition: form.precondition,
    test_point: form.test_point,
    test_data: form.test_data,
    remark: form.remark,
  }
}
export function suiteCaseValidation(form: SuiteCaseForm): string | null {
  if (!form.case_no.trim()) return '请输入用例编号'
  if (!form.title.trim()) return '请输入用例标题'
  if (!form.test_point.trim()) return '请输入测试场景'
  if (!relationId(form.project_product)) return '请选择项目产品'
  if (!relationId(form.module)) return '请选择模块名称'
  if (!relationId(form.owner)) return '请选择负责人'
  if (!form.test_types.length) return '请选择测试类型'
  if (form.priority === null) return '请选择优先级'
  if (form.scenario_layer === null) return '请选择测试层级'
  if (form.scenario_type === null) return '请选择验证类型'
  if (!form.scenario_tags.length) return '请选择执行场景'
  return null
}
export function savedCaseMatches(value: unknown, suiteId: number, id: number | null) {
  const saved = objectValue(value)
  return (
    resourceId(saved.id) !== null &&
    (id === null || resourceId(saved.id) === id) &&
    resourceId(saved.suite) === suiteId
  )
}
