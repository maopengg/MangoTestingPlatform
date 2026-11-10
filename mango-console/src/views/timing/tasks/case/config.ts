import { useTableColumn, useTableIndexColumn } from '@/hooks/table'

export type CandidateExecutionVersion = 'published' | 'unpublished'

export const candidateExecutionVersionOptions = [
  { value: 'published', label: '当前已发布' },
  { value: 'unpublished', label: '暂无已发布版本' },
]

export const candidateColumns = [
  { title: '', dataIndex: 'selected', width: 54 },
  { title: '用例名称', dataIndex: 'title' },
  { title: '状态', dataIndex: 'status', width: 86 },
]

export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 160,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '用例名称',
    key: 'case_id',
    dataIndex: 'case_id',
    align: 'left',
    width: 240,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '测试类型',
    key: 'type',
    dataIndex: 'type',
    width: 116,
  },
  {
    title: '模块名称',
    key: 'module',
    dataIndex: 'module',
    align: 'left',
    width: 150,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '用例负责人',
    key: 'case_people',
    dataIndex: 'case_people',
    align: 'left',
    width: 120,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '测试层级',
    key: 'scenario_layer',
    dataIndex: 'scenario_layer',
    align: 'left',
    width: 120,
  },
  {
    title: '执行场景',
    key: 'scenario_tags',
    dataIndex: 'scenario_tags',
    align: 'left',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '验证类型',
    key: 'scenario_type',
    dataIndex: 'scenario_type',
    align: 'left',
    width: 110,
  },
  {
    title: '优先级',
    key: 'level',
    dataIndex: 'level',
    width: 100,
  },
  {
    title: '执行版本',
    key: 'api_case_version',
    dataIndex: 'api_case_version',
    width: 170,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
