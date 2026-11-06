import { get } from '@/api/http'

export interface SqlExecutionQuery {
  id?: number | string
  source_type?: string
  source_id?: number | string
  source_stage?: string
  project_product_id?: number | string
  test_env?: number | string
  datasource_alias_id?: number | string
  datasource_type?: number | string
  datasource_type__in?: string
  database_id?: number | string
  status?: string
  is_slow?: boolean | string
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
