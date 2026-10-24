export type AssertionValueType =
  | 'string'
  | 'number'
  | 'boolean'
  | 'null'
  | 'object'
  | 'array'
  | 'json'

export type AssertionInputType =
  | 'input'
  | 'textarea'
  | 'number'
  | 'select'
  | 'json'
  | 'object'
  | 'code'
  | 'key_value'

export interface AssertionMethodParameter {
  f: string
  n?: string | null
  p?: string | null
  d?: boolean
  v?: unknown
  value_type?: AssertionValueType | null
  input_type?: AssertionInputType | null
  example_as_placeholder?: boolean
  object_fields?: AssertionObjectField[]
}

export interface AssertionObjectField {
  f: string
  n?: string | null
  p?: string | null
  value_type?: AssertionValueType | null
  input_type?: AssertionInputType | null
}

export interface AssertionMethodItem {
  label: string
  value: string
  parameter?: AssertionMethodParameter[]
  scope?: AssertionMethodScope
  testable?: boolean
  test_disabled_reason?: string
}

export interface AssertionMethodClassGroup {
  label: string
  value: string
  children: AssertionMethodItem[]
  scope?: AssertionMethodScope
  testable?: boolean
}

export interface AssertionMethodTypeGroup {
  label: string
  value: string
  children: AssertionMethodClassGroup[]
  scope?: AssertionMethodScope
  testable?: boolean
}

export type AssertionMethodScope = 'public' | 'mysql' | 'web' | 'android'

export interface AssertionTestAvailability {
  allowed: boolean
  reason: string
}

export interface AssertionEditorItem {
  id: string
  method: string
  values: Record<string, unknown>
}

export interface AssertionEditorGroup {
  id: string
  name: string
  logic: 'AND' | 'OR'
  assertions: AssertionEditorItem[]
}

export interface AssertionTestItemResult {
  method: string
  label?: string
  status: boolean
  message: string
  actual?: unknown
  expect?: unknown
}

export interface AssertionTestGroupResult {
  name: string
  logic: 'AND' | 'OR'
  status: boolean
  items: AssertionTestItemResult[]
}
