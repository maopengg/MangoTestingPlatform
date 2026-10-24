import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()

export const methodOptions = [
  { label: 'GET', value: 0 },
  { label: 'POST', value: 1 },
  { label: 'PUT', value: 2 },
  { label: 'DELETE', value: 3 },
  { label: 'OPTIONS', value: 4 },
  { label: 'PATCH', value: 6 },
]

export const booleanOptions = [
  { label: '启用', value: 1 },
  { label: '停用', value: 0 },
]

export const logOptions = [
  { label: '记录', value: 1 },
  { label: '不记录', value: 0 },
]

export const tableScrollX = 1620

export const tableColumns = useTableColumn([
  table.indexColumn,
  { title: '接口名称', key: 'name', dataIndex: 'name', align: 'left', width: 220, ellipsis: true, tooltip: true },
  { title: '方法', key: 'method_name', dataIndex: 'method_name', width: 100 },
  { title: '请求路径', key: 'mock_url', dataIndex: 'mock_url', align: 'left', width: 360, ellipsis: true, tooltip: true },
  { title: '启用', key: 'enabled', dataIndex: 'enabled', width: 90 },
  { title: '调用记录', key: 'record_call_log', dataIndex: 'record_call_log', width: 110 },
  { title: '更新人', key: 'update_user', dataIndex: 'update_user', width: 120 },
  { title: '更新时间', key: 'update_time', dataIndex: 'update_time', width: 180 },
  { title: '项目/产品', key: 'project_product', dataIndex: 'project_product', align: 'left', width: 180, ellipsis: true, tooltip: true },
  { title: '操作', key: 'actions', dataIndex: 'actions', fixed: 'right', width: 160 },
])
