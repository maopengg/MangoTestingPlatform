import { CASE_SPREADSHEET_FIELDS, formatAutomationBindings } from './config'

// Workbook cells and backend export records are external data, narrowed only at this boundary.
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('数据行格式不正确')
  return value as Record<string, unknown>
}

const blank = (value: unknown) => value === '' || value === null || value === undefined
function text(value: unknown): string {
  if (blank(value)) return ''
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  throw Error('文本字段格式不正确')
}
function number(value: unknown, fallback?: number): number {
  if (blank(value) && fallback !== undefined) return fallback
  if (typeof value !== 'number' && typeof value !== 'string') throw Error('数字字段格式不正确')
  const parsed = Number(value)
  if (!Number.isSafeInteger(parsed)) throw Error('数字字段必须为整数')
  return parsed
}
function list(value: unknown): unknown[] {
  if (blank(value)) return []
  if (Array.isArray(value)) return value
  if (typeof value === 'string') {
    try {
      const parsed: unknown = JSON.parse(value)
      return Array.isArray(parsed) ? parsed : [parsed]
    } catch {
      return [value]
    }
  }
  return [value]
}

export function caseImportPayload(record: unknown) {
  const source = object(record)
  const fields = Object.fromEntries(
    CASE_SPREADSHEET_FIELDS.map(([key, title]) => [key, source[title]])
  )
  return {
    case_no: text(fields.case_no),
    title: text(fields.title),
    project_product: number(fields.project_product_id),
    module: number(fields.module_id),
    owner: number(fields.owner_id),
    category_level_1: text(fields.category_level_1),
    category_level_2: text(fields.category_level_2),
    category_level_3: text(fields.category_level_3),
    priority: number(fields.priority, 1),
    test_types: list(fields.test_types).map((item) => number(item)),
    story_refs: list(fields.story_refs).map(text),
    precondition: text(fields.precondition),
    test_point: text(fields.test_point),
    test_steps: list(fields.test_steps).map((value) => {
      const step = object(value)
      return { action: text(step.action), expected: text(step.expected) }
    }),
    expected_result: text(fields.expected_result),
    acceptance_source: text(fields.acceptance_source),
    test_data: text(fields.test_data),
    automation_status: text(fields.automation_status),
    scenario_layer: number(fields.scenario_layer, 0),
    scenario_type: number(fields.scenario_type, 0),
    scenario_tags: blank(fields.scenario_tags)
      ? ['routine_regression']
      : list(fields.scenario_tags).map(text),
    status: number(fields.status, 1),
    remark: text(fields.remark),
  }
}

export function caseExportRows(records: unknown): Array<Record<string, string | number | boolean>> {
  if (!Array.isArray(records)) throw Error('导出数据格式不正确')
  return records.map((record) => {
    const source = object(record)
    return Object.fromEntries(
      CASE_SPREADSHEET_FIELDS.map(([field, title]) => {
        let value = source[field]
        if (field === 'bindings') {
          value = formatAutomationBindings(Array.isArray(value) ? value : [])
        }
        const relation =
          field === 'project_product_id'
            ? 'project_product'
            : field === 'module_id'
            ? 'module'
            : field === 'owner_id'
            ? 'owner'
            : null
        if (relation && blank(value)) {
          const related = source[relation]
          if (related && typeof related === 'object' && !Array.isArray(related))
            value = object(related).id
          else if (typeof related === 'number') value = related
        }
        if (value && typeof value === 'object') value = JSON.stringify(value)
        return [
          title,
          typeof value === 'number' || typeof value === 'boolean' ? value : text(value),
        ]
      })
    )
  })
}
