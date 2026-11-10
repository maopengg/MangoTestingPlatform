import { cloneLosslessJson } from '@/utils/lossless-json'
import { exampleParameterValues } from './config'
import type { MethodItem, MethodParameter, MethodTypeGroup } from './types'

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid method object')
  return value as Record<string, unknown>
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw Error('Invalid method text')
  return value
}
function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw Error('Invalid method collection')
  return value
}
function parameters(value: unknown): MethodParameter[] {
  if (value == null) return []
  if (!Array.isArray(value)) {
    return Object.entries(object(value)).map(([f, v]) => {
      if (v !== null && typeof v !== 'string') throw Error('Invalid legacy parameter')
      return { f, v }
    })
  }
  return value.map(value => {
    const row = object(value)
    return { f: text(row.f), n: row.n == null ? row.n : text(row.n), v: cloneLosslessJson(row.v) }
  })
}
export function readCatalog(value: unknown): MethodTypeGroup[] {
  const response = object(value)
  if (response.code !== 200) throw Error('Invalid catalog response')
  return array(response.data).map(value => {
    const row = object(value)
    return {
      label: text(row.label), value: text(row.value),
      children: array(row.children).map(value => {
        const row = object(value)
        return {
          label: text(row.label), value: text(row.value),
          children: array(row.children).map(value => {
            const row = object(value)
            return { label: text(row.label), value: text(row.value), parameter: parameters(row.parameter) }
          }),
        }
      }),
    }
  })
}
export function readGeneratedValue(value: unknown): string {
  const response = object(value)
  if (response.code !== 200 || typeof response.data !== 'string') throw Error('Invalid generation response')
  return response.data
}
export function wrapExpression(value: string): string {
  return '${{' + value + '}}'
}
export function normalizeExpression(value: string): string {
  return value.replace(/^\$\{\{/, '').replace(/\}\}$/, '').trim()
}
export function buildExample(record: MethodItem): string {
  const params = record.parameter.map(item => item.v ?? exampleParameterValues[item.f] ?? item.f).join(', ')
  return `${record.value}(${params})`
}
