import type { TableColumnData } from '@arco-design/web-vue'

export const configTypeOptions = [
  { label: 'YAML', value: 1 },
  { label: 'SQL', value: 2 },
  { label: '函数代码', value: 3 },
]

export const executionStatusOptions = [
  { label: '待执行', value: 0 },
  { label: '成功', value: 1 },
  { label: '失败', value: 2 },
  { label: '已恢复', value: 3 },
  { label: '恢复失败', value: 4 },
]

export const caseTypeOptions = [
  { label: 'API用例', value: 1 },
  { label: 'UI用例', value: 2 },
]

const logColumns: Array<TableColumnData & { key: string }> = [
  { title: 'ID', dataIndex: 'id', key: 'index', width: 100, align: 'center' },
  { title: '时间', dataIndex: 'create_time', key: 'create_time', width: 180, align: 'left' },
  {
    title: '灰度Key',
    dataIndex: 'feature_key',
    key: 'feature_key',
    width: 260,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '目标值',
    dataIndex: 'target_value',
    key: 'target_value',
    width: 160,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '用例',
    dataIndex: 'case',
    key: 'case',
    width: 280,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '来源分支',
    dataIndex: 'source_branch',
    key: 'source_branch',
    width: 220,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '目标分支',
    dataIndex: 'target_branch',
    key: 'target_branch',
    width: 130,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: 'PR/MR',
    dataIndex: 'merge_request_url',
    key: 'merge_request',
    width: 110,
    align: 'center',
  },
  {
    title: '合并状态',
    dataIndex: 'merge_request_state',
    key: 'merge_request_state',
    width: 100,
    align: 'center',
  },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90, align: 'center' },
  {
    title: '错误信息',
    dataIndex: 'error_message',
    key: 'error_message',
    width: 260,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '操作',
    dataIndex: 'actions',
    key: 'actions',
    width: 120,
    fixed: 'right',
    align: 'center',
  },
]

export const executionStatusColors: Record<number, string> = {
  0: 'gray',
  1: 'green',
  2: 'red',
  3: 'blue',
  4: 'red',
}
export const multiSelectKeys = ['status', 'config_type', 'case_type', 'yaml_file']

export const grayPageConfig = {
  title: '执行记录',
  columns: logColumns,
  scrollX: logColumns.reduce((width, column) => width + Number(column.width || 0), 0),
  configTypeOptions,
  executionStatusOptions,
  caseTypeOptions,
} as const
