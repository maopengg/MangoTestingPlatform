import { get, post, put } from '@/api/http'

export interface PageResult<T = any> {
  items: T[]
  count: number
  page: number
  page_size: number
}

const base = '/api/module-coverage'

export interface CoverageOverviewCounts {
  analyzed_interface_count: number
  pending_analysis_count: number
  analysis_gap_count: number
  deferred_analysis_count: number
  analysis_rate: number | null
  excluded_interface_count?: number
  interface_count: number
  bound_count: number
  target_count: number
  completed_count: number
  deferred_count: number
  incomplete_interface_count: number
  covered_interface_count: number
  partial_interface_count: number
  uncovered_interface_count: number
  deferred_interface_count: number
  interface_coverage_rate: number | null
  binding_rate: number | null
  automation_rate: number | null
}

export interface CoverageModuleOverview extends CoverageOverviewCounts {
  id: number
  parent_id: number | null
  project_product_id: number
  project_name: string
  product_name: string
  name: string
  full_path: string
  is_leaf: boolean
  scan_completed: boolean
  inventory_completed: boolean
  inventory_scan_ids: number[]
  latest_scan_id: number | null
  applied_scan_id: number | null
  latest_scan_status: string | null
}

export interface CoverageOverview {
  project_inventory_summary: { leaf_count: number; inventoried_count: number; uninventoried_count: number; inventory_rate: number | null }
  project_scan_summary?: { leaf_count: number; scanned_count: number; unscanned_count: number }
  summary: CoverageOverviewCounts & {
    module_count: number
    leaf_count: number
    scanned_count: number
    unscanned_count: number
  }
  modules: CoverageModuleOverview[]
  interface_gaps: Array<{
    id: number
    module_id: number
    project_product_id: number
    module_path: string
    name: string
    method: string
    url: string
    bound: boolean
    incomplete: boolean
    target_count: number
    completed_count: number
    deferred_count: number
  }>
  interface_gap_count: number
}

export function getCoverageOverview(data: Record<string, unknown>) {
  return get<CoverageOverview>({ url: `${base}/overview`, data: () => data })
}

export function getCoverageMetrics(data: {
  project_product?: number
  module?: number
  module__in?: string
  repository_key?: string
  branch?: string
}) {
  return get({ url: `${base}/metrics`, data: () => data })
}

export function getCoverageCases(data: Record<string, unknown>) {
  return get<PageResult>({ url: `${base}/cases`, data: () => data })
}

export function getCoverageInterfaces(data: Record<string, unknown>) {
  return get<PageResult>({ url: `${base}/interfaces`, data: () => data })
}

export function updateCoverageInterfacePolicy(interfaceIds: number[], policy: string, reason = '') {
  return post({ url: `${base}/interfaces/policy`, data: () => ({ interface_ids: interfaceIds, policy, reason }) })
}

export function getCoverageInterfaceDetail(data: Record<string, unknown>) {
  return get({ url: `${base}/interfaces/detail`, data: () => data })
}

export function getCoverageInterfaceSnapshots(id: number, page = 1, pageSize = 10) {
  return get<PageResult>({
    url: `${base}/interfaces/snapshots`,
    data: () => ({ id, page, pageSize }),
  })
}

export function getCoverageInterfaceDiff(
  id: number,
  currentSnapshotId?: number,
  previousSnapshotId?: number
) {
  return get({
    url: `${base}/interfaces/diff`,
    data: () => ({
      id,
      current_snapshot_id: currentSnapshotId,
      previous_snapshot_id: previousSnapshotId,
    }),
  })
}

export function getCoverageCaseDetail(id: number) {
  return get({ url: `${base}/cases/detail`, data: () => ({ id }) })
}

export function getCoverageCaseFlow(id: number) {
  return get({ url: `${base}/cases/flow`, data: () => ({ id }) })
}

export function getCoverageCaseDiff(id: number) {
  return get({ url: `${base}/cases/diff`, data: () => ({ id }) })
}

export function getCoverageCaseSnapshots(id: number, page = 1, pageSize = 10) {
  return get<PageResult>({
    url: `${base}/cases/snapshots`,
    data: () => ({ id, page, pageSize }),
  })
}

export function bindCoverageApiCase(id: number, apiCaseId: number) {
  return put({ url: `${base}/cases/binding`, data: () => ({ id, api_case_id: apiCaseId }) })
}

export function archiveCoverageCases(ids: number[]) {
  return post({ url: `${base}/cases/archive/batch`, data: () => ({ ids }) })
}

export function getCoverageScans(data: Record<string, unknown>) {
  return get<PageResult>({ url: `${base}/scans`, data: () => data })
}

export function getCoverageScanDetail(id: number) {
  return get({ url: `${base}/scans/detail`, data: () => ({ id }) })
}

export function getCoverageScanValidation(id: number) {
  return get({ url: `${base}/scans/validation`, data: () => ({ id }) })
}

export function getCoverageScanUploadStatus(id: number, page = 1, pageSize = 100) {
  return get({ url: `${base}/scans/upload-status`, data: () => ({ id, page, pageSize }) })
}
