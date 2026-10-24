import { post } from '@/api/http'

export interface DataSourceOperationPayload {
  action?: 'execute'
  project_product_id: number | string
  datasource_alias_id: number | string
  test_env: number | string
  operation_config: string | Record<string, unknown>
  confirm_write?: boolean
}

export interface DataSourceConnectionTestPayload {
  action: 'test_connection'
  data_source_id: number | string
  target?: { database_name: string; schema_name: string; redis_db: number | null }
}

export interface LogicalDataSourceConnectionTestPayload {
  action: 'test_connection'
  datasource_alias_id: number | string
  project_product_id: number | string
  test_env: number | string
}

export type DataSourceExecutionPayload =
  | DataSourceOperationPayload
  | DataSourceConnectionTestPayload
  | LogicalDataSourceConnectionTestPayload

export function postDataSourceExecution(data: DataSourceExecutionPayload) {
  return post({
    url: '/data-factory/data-source/execute',
    data: () => data,
    silentError: true,
  })
}
export function queryLogicalDataSource(data: object) {
  return post({url: '/data-factory/data-source/query', data: () => data})
}
