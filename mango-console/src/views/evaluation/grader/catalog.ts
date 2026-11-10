import type { GraderFilters } from './types'

export function createGraderFilters(): GraderFilters {
  return { search: '', categories: [] }
}

export function graderQuery(filters: GraderFilters): Record<string, string> {
  const query: Record<string, string> = {}
  if (filters.search) query.search = filters.search
  if (filters.categories.length) query.category__in = filters.categories.join(',')
  return query
}
