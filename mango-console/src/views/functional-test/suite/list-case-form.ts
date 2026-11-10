import { suiteSelectionId } from './editor-form'
import type { SuiteEditRelation, SuiteProductSelection, SuiteSelection } from './editor-form'

export interface ListCaseRecord {
  id: number
  version_no?: number | null
  suite?: SuiteEditRelation
  case_no?: string
  title?: string
  test_point?: string
  priority?: number | null
  test_types?: number[]
  scenario_layer?: number | null
  scenario_type?: number | null
  scenario_tags?: string[]
  project_product?: SuiteEditRelation
  module?: SuiteEditRelation
  owner?: SuiteEditRelation
}
export interface ListCaseForm {
  case_no: string
  title: string
  test_point: string
  priority: number | null
  test_types: number[]
  scenario_layer: number | null
  scenario_type: number | null
  scenario_tags: string[]
  project_product: SuiteProductSelection
  module: SuiteSelection
  owner: SuiteSelection
}
export interface ListCaseEditorHandle {
  open(record: ListCaseRecord): void
}
export function createListCaseForm(record?: ListCaseRecord): ListCaseForm {
  return {
    case_no: record?.case_no ?? '',
    title: record?.title ?? '',
    test_point: record?.test_point ?? '',
    priority: record?.priority ?? null,
    test_types: [...(record?.test_types ?? [])],
    scenario_layer: record?.scenario_layer ?? null,
    scenario_type: record?.scenario_type ?? null,
    scenario_tags: [...(record?.scenario_tags ?? [])],
    project_product: suiteSelectionId(record?.project_product),
    module: suiteSelectionId(record?.module),
    owner: suiteSelectionId(record?.owner),
  }
}
export function listCaseValidation(form: ListCaseForm): string | null {
  if (!form.case_no.trim()) return '请输入用例编号'
  if (!form.title.trim()) return '请输入用例标题'
  if (!form.test_point.trim()) return '请输入测试场景'
  if (!suiteSelectionId(form.project_product)) return '请选择项目产品'
  if (!suiteSelectionId(form.module)) return '请选择模块名称'
  if (!suiteSelectionId(form.owner)) return '请选择负责人'
  if (!form.test_types.length) return '请选择测试类型'
  if (form.priority === null) return '请选择优先级'
  if (form.scenario_layer === null) return '请选择测试层级'
  if (form.scenario_type === null) return '请选择验证类型'
  if (!form.scenario_tags.length) return '请选择执行场景'
  return null
}
export function listCasePayload(form: ListCaseForm, source: ListCaseRecord) {
  return {
    id: source.id,
    ...(source.version_no == null ? {} : { version_no: source.version_no }),
    suite: suiteSelectionId(source.suite),
    case_no: form.case_no,
    title: form.title,
    test_point: form.test_point,
    priority: form.priority,
    test_types: [...form.test_types],
    scenario_layer: form.scenario_layer,
    scenario_type: form.scenario_type,
    scenario_tags: [...form.scenario_tags],
    project_product: suiteSelectionId(form.project_product),
    module: suiteSelectionId(form.module),
    owner: suiteSelectionId(form.owner),
  }
}
