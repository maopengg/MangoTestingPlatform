export interface FunctionalGridOption {
  label: string
  value: string | number
  colorToken?: string
}

export type FunctionalGridCellValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | Array<string | number>
export type FunctionalGridDisplayChanges = Partial<
  Record<'project_product_path' | 'module_path', string>
>
export interface FunctionalGridCellChange {
  row: object
  field: string
  changes: Record<string, FunctionalGridCellValue>
  displayChanges: FunctionalGridDisplayChanges
  oldValues: Record<string, unknown>
}

// Dynamic columns read arbitrary business records; this boundary is read-only.
export type FunctionalGridRecord = Readonly<Record<string, unknown>>
export function readGridRecord(row: object): FunctionalGridRecord {
  return row as FunctionalGridRecord
}

export interface FunctionalGridColumn {
  field: string
  title: string
  width?: number
  minWidth?: number
  fixed?: 'left' | 'right'
  visible?: boolean
  editable?: boolean
  sortable?: boolean
  editor?: 'text' | 'textarea' | 'number' | 'project-product' | 'module-cascader'
  displayField?: string
  options?: FunctionalGridOption[]
  multiple?: boolean
  valueAliases?: Record<string, string | number>
  align?: 'left' | 'center'
}
