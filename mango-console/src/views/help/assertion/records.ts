import { cloneLosslessJson } from '@/utils/lossless-json'
import type {
  AssertionEditorGroup,
  AssertionMethodTypeGroup,
  AssertionMethodParameter,
  AssertionObjectField,
  AssertionTestGroupResult,
  AssertionTestItemResult,
} from '@/types/assertion'
export interface AssertionTestResult {
  status: boolean
  message: string
  groups: AssertionTestGroupResult[]
}
export function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw Error('Invalid assertion text')
  return value
}
function optionalText(value: unknown): string | undefined {
  return value == null ? undefined : text(value)
}
function optionalBoolean(value: unknown): boolean | undefined {
  if (value === undefined) return undefined
  if (typeof value !== 'boolean') throw Error('Invalid assertion boolean')
  return value
}
function scope(value: unknown) {
  if (value === undefined) return undefined
  if (!['public', 'mysql', 'web', 'android'].includes(String(value)))
    throw Error('Invalid assertion scope')
  return value as AssertionMethodTypeGroup['scope']
}
function valueType(value: unknown): AssertionMethodParameter['value_type'] {
  if (value == null) return undefined
  if (!['string', 'number', 'boolean', 'null', 'object', 'array', 'json'].includes(String(value)))
    throw Error('Invalid parameter type')
  return value as AssertionMethodParameter['value_type']
}
function inputType(value: unknown): AssertionMethodParameter['input_type'] {
  if (value == null) return undefined
  if (
    !['input', 'textarea', 'number', 'select', 'json', 'object', 'code', 'key_value'].includes(
      String(value)
    )
  )
    throw Error('Invalid parameter input')
  return value as AssertionMethodParameter['input_type']
}
function parameter(value: unknown): AssertionMethodParameter {
  const row = object(value)
  const fields: AssertionObjectField[] | undefined = Array.isArray(row.object_fields)
    ? row.object_fields.map((value) => {
        const field = object(value)
        return {
          f: text(field.f),
          n: optionalText(field.n),
          p: optionalText(field.p),
          value_type: valueType(field.value_type),
          input_type: inputType(field.input_type),
        }
      })
    : undefined
  return {
    f: text(row.f),
    n: optionalText(row.n),
    p: optionalText(row.p),
    d: optionalBoolean(row.d),
    v: cloneLosslessJson(row.v),
    value_type: valueType(row.value_type),
    input_type: inputType(row.input_type),
    example_as_placeholder: optionalBoolean(row.example_as_placeholder),
    object_fields: fields,
  }
}
export function catalog(value: unknown): AssertionMethodTypeGroup[] {
  const response = object(value)
  if (response.code !== 200 || !Array.isArray(response.data))
    throw Error('Invalid assertion catalog')
  return response.data
    .map((value) => {
      const row = object(value)
      if (!Array.isArray(row.children)) throw Error('Invalid assertion categories')
      return {
        label: text(row.label),
        value: text(row.value),
        scope: scope(row.scope),
        testable: optionalBoolean(row.testable),
        children: row.children.map((value) => {
          const row = object(value)
          if (!Array.isArray(row.children)) throw Error('Invalid assertion methods')
          const seen = new Set<string>()
          return {
            label: text(row.label),
            value: text(row.value),
            scope: scope(row.scope),
            testable: optionalBoolean(row.testable),
            children: row.children.map((value) => {
              const row = object(value),
                method = text(row.value)
              if (seen.has(method)) throw Error('Duplicate assertion method')
              seen.add(method)
              if (row.parameter !== undefined && !Array.isArray(row.parameter))
                throw Error('Invalid assertion parameters')
              return {
                label: text(row.label),
                value: method,
                scope: scope(row.scope),
                testable: optionalBoolean(row.testable),
                test_disabled_reason: optionalText(row.test_disabled_reason),
                parameter: (Array.isArray(row.parameter) ? row.parameter : []).map(parameter),
              }
            }),
          }
        }),
      }
    })
    .sort((left, right) =>
      left.value === '函数断言' && right.value !== '函数断言'
        ? 1
        : right.value === '函数断言' && left.value !== '函数断言'
        ? -1
        : 0
    )
}
export function testPayload(groups: AssertionEditorGroup[]) {
  return cloneLosslessJson({
    assertions: groups.map((group) => ({
      name: group.name,
      logic: group.logic,
      items: group.assertions.map((item) => ({ ...item.values, method: item.method })),
    })),
  })
}
export function testResult(
  value: unknown,
  request: ReturnType<typeof testPayload>
): AssertionTestResult {
  const response = object(value),
    data = object(response.data)
  if (
    response.code !== 200 ||
    typeof data.status !== 'boolean' ||
    typeof data.message !== 'string' ||
    !Array.isArray(data.groups) ||
    data.groups.length !== request.assertions.length
  )
    throw Error('Invalid assertion result')
  const groups: AssertionTestGroupResult[] = data.groups.map((value, index) => {
    const row = object(value),
      source = request.assertions[index]
    if (
      row.name !== (source.name || `断言组${index + 1}`) ||
      row.logic !== source.logic ||
      typeof row.status !== 'boolean' ||
      !Array.isArray(row.items) ||
      row.items.length !== source.items.length
    )
      throw Error('Mismatched assertion group')
    const items: AssertionTestItemResult[] = row.items.map((value, index) => {
      const item = object(value)
      if (item.method !== source.items[index].method || typeof item.status !== 'boolean')
        throw Error('Mismatched assertion item')
      return {
        method: text(item.method),
        label: optionalText(item.label),
        status: item.status,
        message: text(item.message),
        actual: cloneLosslessJson(item.actual),
        expect: cloneLosslessJson(item.expect),
      }
    })
    return { name: text(row.name), logic: source.logic, status: row.status, items }
  })
  return { status: data.status, message: data.message, groups }
}
