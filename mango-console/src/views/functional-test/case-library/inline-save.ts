export const CASE_INLINE_FIELDS = [
  'case_no',
  'title',
  'category_level_1',
  'category_level_2',
  'category_level_3',
  'priority',
  'test_types',
  'precondition',
  'test_point',
  'expected_result',
  'acceptance_source',
  'test_data',
  'scenario_layer',
  'scenario_type',
  'scenario_tags',
  'automation_status',
  'remark',
  'status',
  'owner_id',
  'project_product_id',
  'module_id',
] as const

export type CaseInlineField = (typeof CASE_INLINE_FIELDS)[number]
// Sheet cells include cleared values and enum arrays before server-side field validation.
export type CaseInlineValue = string | number | null | undefined | Array<string | number>
export type CaseInlineChanges = Partial<Record<CaseInlineField, CaseInlineValue>>
export type CaseInlineRow = Record<CaseInlineField, CaseInlineValue> & {
  id: string | number
  version_no: string | number
  update_time: string
  project_product_path: string
  module_path: string
  __draft?: boolean
  __touched?: boolean
}

export type CaseInlineEvent = Omit<
  import('@/components/table/functional-case-grid').FunctionalGridCellChange,
  'row'
> & { row: CaseInlineRow }

const fields = new Set<string>(CASE_INLINE_FIELDS)
export function isCaseInlineField(field: string): field is CaseInlineField {
  return fields.has(field)
}

export function inlineCellValue(value: unknown): value is CaseInlineValue {
  return (
    value === null ||
    value === undefined ||
    typeof value === 'string' ||
    typeof value === 'number' ||
    (Array.isArray(value) &&
      value.every((item) => typeof item === 'string' || typeof item === 'number'))
  )
}

export function cloneInlineValue(value: CaseInlineValue): CaseInlineValue {
  return Array.isArray(value) ? [...value] : value
}

export function inlineValuesEqual(left: CaseInlineValue, right: CaseInlineValue) {
  return Array.isArray(left) || Array.isArray(right)
    ? JSON.stringify(left) === JSON.stringify(right)
    : left === right
}
