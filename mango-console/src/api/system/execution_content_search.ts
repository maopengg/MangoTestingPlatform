import { get, post } from '@/api/http'

export type ContentSearchKind = 'automation' | 'datasource'
export interface ContentSearchQuery {
  project_product_id?: number | null
  test_env?: number | null
  day: string
  keyword: string
}
export interface ContentSearchHit {
  record_id: number
  target_type: string
  target_id: number | null
  name: string
  create_time: string
  source_type: string
  stage: string
  report_id: number | string | null
  trigger_user: string
  path: string
  snippet: string
}
export interface ContentSearchTask {
  task_id: string
  status: 'running' | 'completed' | 'partial' | 'cancelled' | 'failed'
  query: ContentSearchQuery
  scanned: number
  skipped: number
  read_bytes: number
  message: string
  count: number
  page: number
  items: ContentSearchHit[]
}
function url(kind: ContentSearchKind) {
  return kind === 'automation' ? 'system/execution/result/search' : 'system/sql-execution/search'
}
export const startContentSearch = (kind: ContentSearchKind, data: ContentSearchQuery) =>
  post<ContentSearchTask>({ url: url(kind), data })
export const getContentSearch = (kind: ContentSearchKind, task_id: string, page = 1) =>
  get<ContentSearchTask>({ url: url(kind), data: { task_id, page } })
export const cancelContentSearch = (kind: ContentSearchKind, task_id: string) =>
  post<ContentSearchTask>({ url: `${url(kind)}/cancel`, data: { task_id } })
