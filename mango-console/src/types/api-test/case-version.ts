import type { ApiCaseRevisionPayload } from './case-revision-payload'

export type ApiCasePublicationStatus =
  | 'unpublished'
  | 'prepublished'
  | 'published'
export type ApiCaseReleaseStatus = 'published' | 'deprecated' | 'retired'

export interface ApiCasePublicationReadModel {
  current_revision_id: number | null
  current_revision_no: number | null
  published_release_id: number | null
  published_revision_id: number | null
  published_version_label: string | null
  prepublished_revision_id: number | null
  prepublished_revision_no: number | null
  publication_status: ApiCasePublicationStatus
  has_unpublished_changes: boolean
  is_product_owner?: boolean
  has_product_owner?: boolean
}

export interface ApiCaseVersionListRow extends ApiCasePublicationReadModel {
  id: number
  name: string
  status?: number
  project_product?: {
    id: number
    name: string
    project?: {
      id: number
      name: string
    }
  }
  disabled?: boolean
}

export interface ApiCaseRelease {
  id: number
  api_case: number
  revision: number
  revision_no: number
  version_no: number
  version_label: string
  status: ApiCaseReleaseStatus
  is_current: boolean
  release_note: string | null
  published_by: number | null
  published_by_name: string | null
  published_at: string
  replaced_release: number | null
}

export interface ApiCaseRevisionListItem {
  id: number
  api_case: number
  revision_no: number
  parent_revision: number | null
  restored_from_revision: number | null
  snapshot_schema_version: number
  checksum: string
  source: string
  operator: number | null
  operator_name: string | null
  summary: string | null
  change_group_id: string | null
  create_time: string
  release: ApiCaseRelease | null
  is_prepublished: boolean
  is_active_candidate: boolean
  is_product_owner: boolean
  has_product_owner: boolean
}

export interface ApiCaseRevisionApiDependency {
  step_index: number
  step_logical_id: string
  api_info_id: number
  api_info_name: string | null
  api_info_revision_id: number
  api_info_revision_no: number | null
  status: 'available' | 'restorable' | 'blocked'
  source_available: boolean
  snapshot_available: boolean
  reason: string | null
}

export interface ApiCaseRevisionCheckoutImpact {
  case_id: number
  revision_id: number
  can_checkout: boolean
  requires_restore: boolean
  items: ApiCaseRevisionApiDependency[]
}

export interface ApiCaseRevisionDetail extends ApiCaseRevisionListItem {
  payload: ApiCaseRevisionPayload
  api_revision_dependencies: ApiCaseRevisionApiDependency[]
}

export interface ApiCaseBatchExecutionItem {
  case_id: number
  case_release_id: number
  case_revision_id: number
  version_label: string
}

export interface ApiCaseBatchRunRequestItem {
  case_id: number
  case_release_id: number
}

export interface ApiCaseTaskReleaseOption {
  release_id: number
  revision_id: number
  revision_no?: number
  version_label: string
  status: ApiCaseReleaseStatus
  is_current?: boolean
}

export interface ApiCaseTaskCandidate {
  key: number | string
  title: string
  published_release_id: number | null
  release_options: ApiCaseTaskReleaseOption[]
}

export interface ApiCaseTaskBindingPlan {
  items: ApiCaseBatchRunRequestItem[]
  blocked: ApiCaseBlockedExecutionItem[]
}

export interface ApiCaseBlockedExecutionItem {
  case_id: number
  case_name: string
  reason: string
}

export interface ApiCaseBatchExecutionPlan {
  executable: ApiCaseBatchExecutionItem[]
  blocked: ApiCaseBlockedExecutionItem[]
}

export interface ApiCasePublicationMeta {
  label: string
  color: string
}

export interface CreateApiCaseRevisionPayload {
  case_id: number
  summary?: string
  source?: string
}
