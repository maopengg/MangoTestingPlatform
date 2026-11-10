import type { CoverageFilters, CoverageTab } from './types'
export function createCoverageFilters(): CoverageFilters {
  return {
    repository_key: '',
    branch: '',
    name: '',
    interface_name: '',
    coverage_reason: '',
    api_info_id: undefined,
    status: undefined,
    change_status: undefined,
    coverage_validity: undefined,
    interface_status: undefined,
    api_info_binding_status: undefined,
    coverage_policy: undefined,
    scenario_layer: undefined,
    scenario_type: undefined,
    scenario_tag: undefined,
    resolution_statuses: [],
    analysis_statuses: [],
    coverage_statuses: [],
    sync_actions: [],
    methods: [],
  }
}
export function coverageQuery(
  tab: CoverageTab,
  filters: CoverageFilters,
  scope: { projectProduct?: number; module?: number; moduleIds: Array<string | number> },
  page = 1,
  pageSize = 20
) {
  const query: Record<string, unknown> = {
    project_product: scope.projectProduct,
    repository_key: filters.repository_key.trim(),
    branch: filters.branch.trim(),
  }
  if (scope.moduleIds.length) query.module__in = scope.moduleIds.join(',')
  else if (scope.module != null) query.module = scope.module
  if (tab !== 'overview') Object.assign(query, { page, pageSize })
  if (tab === 'interfaces') {
    Object.assign(query, {
      name: filters.name.trim(),
      status: filters.interface_status,
      api_info_binding_status: filters.api_info_binding_status,
      coverage_policy: filters.coverage_policy,
      coverage_reason: filters.coverage_reason.trim(),
      api_info_id: filters.api_info_id,
      include_removed: filters.interface_status === 'removed' ? true : undefined,
    })
    for (const [field, key] of Object.entries({
      analysis_status__in: 'analysis_statuses',
      resolution_status__in: 'resolution_statuses',
      coverage_status__in: 'coverage_statuses',
      sync_action__in: 'sync_actions',
      method__in: 'methods',
    }) as Array<
      [
        string,
        (
          | 'analysis_statuses'
          | 'resolution_statuses'
          | 'coverage_statuses'
          | 'sync_actions'
          | 'methods'
        )
      ]
    >) {
      if (filters[key].length) query[field] = filters[key].join(',')
    }
  } else if (tab === 'cases') {
    Object.assign(query, {
      name: filters.name.trim(),
      interface_name: filters.interface_name.trim(),
      status: filters.status,
      change_status: filters.change_status,
      coverage_validity: filters.coverage_validity,
      scenario_layer: filters.scenario_layer,
      scenario_type: filters.scenario_type,
      scenario_tag: filters.scenario_tag,
      include_removed: true,
    })
  }
  return Object.fromEntries(
    Object.entries(query).filter(
      ([, value]) => value !== '' && value !== undefined && value !== null
    )
  )
}
