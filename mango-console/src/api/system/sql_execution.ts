import { get } from '@/api/http'

export interface SqlExecutionQuery {
  case_id?: number | string
  case_detail_id?: number | string
  test_suite_id?: number | string
  operation?: string
  id?: number | string
  id__in?: string
  source_type?: string
  source_type__in?: string
  source_id?: number | string
  source_id__in?: string
  source_stage?: string
  source_stage__in?: string
  project_product_id?: number | string
  project_product_id__in?: string
  test_env?: number | string
  test_env__in?: string
  datasource_alias_id?: number | string
  datasource_alias_id__in?: string
  datasource_type?: number | string
  datasource_type__in?: string
  database_id?: number | string
  database_id__in?: string
  status?: string
  status__in?: string
  is_slow?: boolean | string
  is_slow__in?: string
  duration_min?: number | string
  duration_max?: number | string
  sql_keyword?: string
  create_time_start?: string
  create_time_end?: string
  page?: number
  pageSize?: number
}

export function getSqlExecutionList(data: SqlExecutionQuery) {
  return get({
    url: 'system/sql-execution',
    data: () => data,
  })
}

export function getSqlExecutionOptions() {
  return get({
    url: 'system/sql-execution/options',
    data: () => ({}),
  })
}
