export interface MethodParameter {
  f: string
  n?: string | null
  v?: unknown
}

export interface MethodItem {
  label: string
  value: string
  parameter: MethodParameter[]
}

export interface MethodClassGroup {
  label: string
  value: string
  children: MethodItem[]
}

export interface MethodTypeGroup {
  label: string
  value: string
  children: MethodClassGroup[]
}

export interface MethodMenuGroup extends MethodClassGroup {
  menuKey: string
  typeValue: string
  typeLabel: string
}
