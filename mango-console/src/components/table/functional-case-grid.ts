export interface FunctionalGridOption {
  label: string
  value: string | number
  colorToken?: string
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
