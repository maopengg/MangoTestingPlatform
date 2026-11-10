import { idOf, object } from './editor-form'
import type { FeatureRow } from './records'

export interface PathDraft {
  path: string[]
  value_type: string
  original_value: string
  value: unknown
}
export interface PathOption {
  value: string
  label: string
  children?: PathOption[]
}
export interface PreviewHandle {
  open(record: FeatureRow): void
}
export const COMMON_ENV = '__common__'
export function environment(value: string | number | null): string | number | null {
  if (value === COMMON_ENV || value == null || value === '') return null
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : value
}
function pathValue(value: unknown): string {
  const leaf = Array.isArray(value) ? value[value.length - 1] : value
  return leaf == null ? '' : String(leaf).trim()
}
export function normalizePaths(value: unknown) {
  return (Array.isArray(value) ? value : [])
    .map((value) => {
      const row = object(value)
      return {
        path: pathValue(row.path),
        value_type:
          typeof row.value_type === 'string' && row.value_type ? row.value_type : 'number',
        original_value: row.original_value == null ? '' : String(row.original_value).trim(),
        value: row.value,
      }
    })
    .filter((row) => row.path)
}
export function pathDrafts(value: unknown): PathDraft[] {
  return normalizePaths(value).map((row) => {
    const parts = row.path.split('.').filter(Boolean)
    return { ...row, path: parts.map((_, index) => parts.slice(0, index + 1).join('.')) }
  })
}
export function hasVariables(value: unknown): boolean {
  return normalizePaths(value).some((row) =>
    [row.value, row.original_value].some(
      (value) => typeof value === 'string' && /\$\{\{[^}]+}}|\$\{[^}]+}/.test(value)
    )
  )
}
export function pathTree(value: unknown, prefix = ''): PathOption[] {
  return Object.entries(object(value)).map(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key,
      children = pathTree(child, path)
    return { value: path, label: key, ...(children.length ? { children } : {}) }
  })
}
export function inputValue(value: unknown): string {
  return value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value)
}
export function previewResult(value: unknown, record: FeatureRow) {
  const response = object(value),
    data = object(response.data)
  const type = ({ 1: 'yaml', 2: 'sql', 3: 'code' } as const)[record.config_type]
  if (
    response.code !== 200 ||
    idOf(data.feature_id) !== record.id ||
    data.feature_key !== record.feature_key ||
    data.action !== 'enable' ||
    data.config_type !== type
  )
    throw Error('Invalid preview acknowledgment')
  function text(key: 'before' | 'after'): string {
    const value = data[`${key}_text`]
    if (typeof value === 'string') return value
    if (type !== 'yaml' || data[`${key}_snapshot`] === undefined)
      throw Error('Missing preview text')
    return JSON.stringify(data[`${key}_snapshot`], null, 2)
  }
  return {
    before: text('before'),
    after: text('after'),
    filePath: typeof data.file_path === 'string' ? data.file_path : '',
    paths: pathTree(data.before_snapshot),
  }
}
