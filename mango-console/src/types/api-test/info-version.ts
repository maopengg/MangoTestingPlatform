import type { ApiCaseReleaseStatus } from './case-version'
import type { ApiInfoRevisionPayload } from './info-revision-payload'

export interface ApiInfoRelease {
  id: number
  api_info: number
  revision: number
  revision_no: number
  version_no: number
  version_label: string
  status: ApiCaseReleaseStatus
  is_current: boolean
  release_note: string | null
  published_by_name: string | null
  published_at: string
}

export interface ApiInfoRevisionListItem {
  id: number
  api_info: number
  revision_no: number
  parent_revision: number | null
  restored_from_revision: number | null
  checksum: string
  source: string
  operator_name: string | null
  summary: string | null
  create_time: string
  release: ApiInfoRelease | null
}

export interface ApiInfoRevisionDetail extends ApiInfoRevisionListItem {
  payload: ApiInfoRevisionPayload
}
