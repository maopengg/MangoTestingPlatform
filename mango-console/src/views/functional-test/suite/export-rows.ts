import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
import { readListPage } from './list-page'

export interface CaseExportOption {
  key: string | number
  title: string
}
export interface CaseExportEnums {
  testTypes: CaseExportOption[]
  priorities: CaseExportOption[]
  layers: CaseExportOption[]
  types: CaseExportOption[]
  tags: CaseExportOption[]
  changes: CaseExportOption[]
  impacts: CaseExportOption[]
}
type ExportCell = string | number
export type CaseExportRow = Record<string, ExportCell>

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
  return value as Record<string, unknown>
}
function text(value: unknown) {
  return typeof value === 'string' ? value : ''
}
function positiveId(value: unknown): number | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0 ? value : null
}
function enumTitle(options: CaseExportOption[], value: unknown): ExportCell {
  return (
    options.find((item) => item.key === value)?.title ??
    (typeof value === 'string' || typeof value === 'number' ? value : '-')
  )
}
function enumTitles(options: CaseExportOption[], value: unknown) {
  return Array.isArray(value) && value.length
    ? value.map((item) => enumTitle(options, item)).join('、')
    : '-'
}
function bindingId(value: unknown, type: number): ExportCell {
  if (!Array.isArray(value)) return ''
  const binding = value.map(object).find((item) => item.automation_type === type)
  if (!binding) return ''
  return (
    positiveId(type === 0 ? binding.api_case : binding.ui_case) ??
    positiveId(binding.automation_case_id) ??
    ''
  )
}

export const caseExportPage = readListPage

export function caseExportRows(
  rows: Record<string, unknown>[],
  enums: CaseExportEnums
): CaseExportRow[] {
  return rows.map((record) => {
    const suite = object(record.suite)
    return {
      ID: positiveId(record.id) ?? '',
      '项目/产品': formatProjectProductPath(record.project_product),
      模块: formatModulePath(record.module),
      用例编号: text(record.case_no),
      标题: text(record.title),
      需求名称: text(suite.requirement_name),
      所属Sprint: text(object(suite.iteration_ref).name) || text(suite.iteration),
      前置条件: text(record.precondition),
      测试场景: text(record.test_point),
      测试数据: text(record.test_data),
      测试类型: enumTitles(enums.testTypes, record.test_types),
      优先级: enumTitle(enums.priorities, record.priority),
      测试层级: enumTitle(enums.layers, record.scenario_layer),
      验证类型: enumTitle(enums.types, record.scenario_type),
      执行场景: enumTitles(enums.tags, record.scenario_tags),
      'API 用例 ID': bindingId(record.bindings, 0),
      'UI 用例 ID': bindingId(record.bindings, 1),
      变更: enumTitle(enums.changes, record.change_status),
      自动化影响: enumTitle(enums.impacts, record.automation_impact_status),
      备注: text(record.remark),
    }
  })
}
