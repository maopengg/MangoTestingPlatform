import { getOptionId } from '@/utils/business-format'
import { normalizeIdSearchParams } from '@/utils/id-search'
import type { MockFilters } from './types'

export function buildMockQuery(filters: MockFilters, page: number, pageSize: number) {
  const query: Record<string, unknown> = { page, pageSize }
  const product = getOptionId(filters.project_product)
  if (product !== null && product !== '') query.project_product = product
  for (const key of ['id', 'name'] as const) {
    const value = filters[key].trim()
    if (value) query[key] = value
  }
  const path = filters.mock_key.trim().replace(/^\/+/, '').split('/')[0]
  if (path) query.mock_key = path
  for (const key of ['method', 'enabled', 'record_call_log'] as const) {
    if (filters[key].length) query[`${key}__in`] = [...new Set(filters[key])].join(',')
  }
  return normalizeIdSearchParams(query)
}
