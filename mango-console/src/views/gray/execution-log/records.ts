import { normalizeEmptyListTotal } from '@/utils/api-response'
import { normalizeMultiSelectSearchParams } from '@/utils/search-condition'
import { multiSelectKeys } from './config'

export interface ExecutionQuery {
  feature_key: string
  target_value: string
  status: number[]
  config_type: number[]
  case_type: number[]
  case_name: string
  test_suite_id: string
  case_id: string
  yaml_file: number[]
  source_branch: string
  target_branch: string
}
export interface ExecutionRow {
  id: number
  status: number
  create_time: string
  feature_key: string
  target_value: string | null
  case_name: string | null
  case_id: string | number | null
  source_branch: string | null
  target_branch: string | null
  merge_request_url: string | null
  merge_request_id: string | null
  merge_request_iid: string | null
  merge_request_state: string | null
  error_message: string | null
  detail: string
}
export interface YamlOption {
  label: string
  value: number
}
export const createQuery = (): ExecutionQuery => ({
  feature_key: '',
  target_value: '',
  status: [],
  config_type: [],
  case_type: [],
  case_name: '',
  test_suite_id: '',
  case_id: '',
  yaml_file: [],
  source_branch: '',
  target_branch: '',
})
export function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}
export function positiveId(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0
}
export const isStatus = (value: unknown): value is number =>
  typeof value === 'number' && [0, 1, 2, 3, 4].includes(value)
export const canRestore = (status: number) => [1, 2, 4].includes(status)
export function requestParams(query: ExecutionQuery, page: number, pageSize: number) {
  const params = normalizeMultiSelectSearchParams(
    {
      page,
      pageSize,
      feature_key: query.feature_key,
      target_value: query.target_value,
      status: query.status,
      config_type: query.config_type,
      case_type: query.case_type,
      case_name: query.case_name,
      test_suite_id: query.test_suite_id,
      case_id: query.case_id,
      yaml_file: query.yaml_file,
      source_branch: query.source_branch,
      target_branch: query.target_branch,
    },
    multiSelectKeys
  )
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value != null)
  )
}
function nullableText(value: unknown): string | null {
  if (value === null) return null
  if (typeof value !== 'string') throw Error('Invalid execution text')
  return value
}
export function executionPage(value: unknown) {
  value = normalizeEmptyListTotal(value)

  const response = object(value),
    list = response.data
  const total =
    response.totalSize === undefined && Array.isArray(list) && !list.length ? 0 : response.totalSize
  if (
    response.code !== 200 ||
    !Array.isArray(list) ||
    typeof total !== 'number' ||
    !Number.isSafeInteger(total) ||
    total < list.length
  )
    throw Error('Invalid execution page')
  const seen = new Set<number>()
  const rows: ExecutionRow[] = list.map((value) => {
    const row = object(value)
    if (
      !positiveId(row.id) ||
      seen.has(row.id) ||
      !isStatus(row.status) ||
      typeof row.create_time !== 'string' ||
      typeof row.feature_key !== 'string' ||
      (row.case_id !== null &&
        typeof row.case_id !== 'string' &&
        (typeof row.case_id !== 'number' || !Number.isFinite(row.case_id)))
    )
      throw Error('Invalid execution record')
    seen.add(row.id)
    return {
      id: row.id,
      status: row.status,
      create_time: row.create_time,
      feature_key: row.feature_key,
      case_id: row.case_id as string | number | null,
      target_value: nullableText(row.target_value),
      case_name: nullableText(row.case_name),
      source_branch: nullableText(row.source_branch),
      target_branch: nullableText(row.target_branch),
      merge_request_url: nullableText(row.merge_request_url),
      merge_request_id: nullableText(row.merge_request_id),
      merge_request_iid: nullableText(row.merge_request_iid),
      merge_request_state: nullableText(row.merge_request_state),
      error_message: nullableText(row.error_message),
      detail: JSON.stringify(row, null, 2),
    }
  })
  return { rows, total }
}
export function yamlOptions(value: unknown): YamlOption[] {
  const response = object(value)
  if (response.code !== 200 || !Array.isArray(response.data))
    throw Error('Invalid configuration options')
  const seen = new Set<number>()
  return response.data.map((value) => {
    const row = object(value)
    if (!positiveId(row.id) || seen.has(row.id) || typeof row.name !== 'string')
      throw Error('Invalid configuration option')
    seen.add(row.id)
    return { value: row.id, label: row.name }
  })
}
export function externalUrl(value: string | null) {
  if (!value) return null
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}
