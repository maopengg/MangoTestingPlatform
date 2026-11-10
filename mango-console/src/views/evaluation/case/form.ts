import type { CaseForm, CaseFilters, EvaluationRows, RelationSelection } from '../types'

export const createCaseForm = (): CaseForm => ({
  name: '',
  description: '',
  project_product: null,
  module: null,
  dataset_id: null,
  dataset_version: null,
  status: 'draft',
})
export const leafId = (value: RelationSelection) =>
  Array.isArray(value) ? value[value.length - 1] : value
export function evaluationRows<T>(response: EvaluationRows<T>): T[] {
  return Array.isArray(response.data) ? response.data : response.data?.items || []
}

export const createCaseFilters = (): CaseFilters => ({
  name: '',
  status: [],
  target_type: [],
  project_product: null,
  module: null,
})
export function navigationId(value: string | number | null): number | null {
  const id = value === null || value === '' ? NaN : Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
export function caseListQuery(
  filters: CaseFilters,
  moduleIds: number[],
  page: number,
  pageSize: number,
  environment: string | number | null | undefined
): Record<string, unknown> {
  const query = {
    page,
    pageSize,
    name: filters.name.trim() || undefined,
    status__in: filters.status.length ? filters.status.join(',') : undefined,
    target_type__in: filters.target_type.length ? filters.target_type.join(',') : undefined,
    project_product: filters.project_product ?? undefined,
    module__in: moduleIds.length ? moduleIds.join(',') : undefined,
    module: moduleIds.length ? undefined : filters.module ?? undefined,
    test_env: environment || undefined,
  }
  return Object.fromEntries(
    Object.entries(query).filter(
      ([, value]) => value !== undefined && value !== null && value !== ''
    )
  )
}
