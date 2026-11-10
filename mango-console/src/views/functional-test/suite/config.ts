import type { TableColumnData } from '@arco-design/web-vue'
import type { FormItem } from '@/types/components'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'
import { enableMultiSelectSearch } from '@/utils/search-condition'

export type SuiteSearchCondition = Omit<FormItem, 'key' | 'value'> & {
  key: 'requirement_name' | 'sync_status' | 'update_user'
  value: string | Array<string | number> | undefined
}
export function createSuiteConditions(): SuiteSearchCondition[] {
  const conditionItems: SuiteSearchCondition[] = [
    {
      key: 'requirement_name',
      label: '需求名称',
      type: 'input',
      value: '',
      placeholder: '请输入需求名称',
    },
    {
      key: 'sync_status',
      label: '同步状态',
      type: 'select',
      value: undefined as string | undefined,
      placeholder: '请选择同步状态',
    },
    { ...createUpdateUserCondition(), key: 'update_user', value: [] },
  ]
  enableMultiSelectSearch(conditionItems)
  return conditionItems
}

export const suiteColumns: Array<TableColumnData & { key: string }> = [
  { title: 'ID', key: 'id', dataIndex: 'id', width: 72, align: 'center' },
  {
    title: '需求名称',
    key: 'requirement_name',
    dataIndex: 'requirement_name',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '所属 Sprint',
    key: 'iteration_ref',
    dataIndex: 'iteration_ref',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  { title: '优先级', key: 'priority', dataIndex: 'priority', width: 90, align: 'center' },
  {
    title: '开发负责人',
    key: 'development_owner',
    dataIndex: 'development_owner',
    width: 120,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '计划开始',
    key: 'planned_start_date',
    dataIndex: 'planned_start_date',
    width: 120,
    align: 'center',
  },
  {
    title: '计划提测',
    key: 'planned_submit_date',
    dataIndex: 'planned_submit_date',
    width: 120,
    align: 'center',
  },
  { title: '交付状态', key: 'status', dataIndex: 'status', width: 110, align: 'center' },
  {
    title: '测试负责人',
    key: 'owner',
    dataIndex: 'owner',
    width: 120,
    ellipsis: true,
    tooltip: true,
  },
  { title: '用例数', key: 'case_count', dataIndex: 'case_count', width: 90, align: 'center' },
  { title: '测试进度', key: 'test_progress', dataIndex: 'test_metrics', width: 170 },
  { title: '通过率', key: 'pass_rate', dataIndex: 'test_metrics', width: 100, align: 'center' },
  {
    title: '未关闭缺陷',
    key: 'open_defect_count',
    dataIndex: 'open_defect_count',
    width: 110,
    align: 'center',
  },
  {
    title: '自动化数',
    key: 'automated_case_count',
    dataIndex: 'automated_case_count',
    width: 100,
    align: 'center',
  },
  { title: '完成百分比', key: 'coverage', dataIndex: 'automation_coverage_percent', width: 160 },
  { title: '同步状态', key: 'sync_status', dataIndex: 'sync_status', width: 110, align: 'center' },
  {
    title: '最近同步',
    key: 'last_sync_time',
    dataIndex: 'last_sync_time',
    width: 180,
    align: 'center',
  },
  { ...updateUserColumn(120), key: 'update_user', ellipsis: true, tooltip: true },
  { title: '更新时间', key: 'update_time', dataIndex: 'update_time', width: 180, align: 'center' },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'module',
    width: 240,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    align: 'center',
    fixed: 'right',
    width: 140,
  },
]
export const caseColumns: Array<TableColumnData & { key: string }> = [
  { title: 'ID', key: 'id', dataIndex: 'id', width: 72, align: 'center' },
  {
    title: '需求名称',
    key: 'suite',
    dataIndex: 'suite',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '所属 Sprint',
    key: 'suite_iteration',
    dataIndex: 'suite_iteration',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '用例编号',
    key: 'case_no',
    dataIndex: 'case_no',
    width: 130,
    ellipsis: true,
    tooltip: true,
  },
  { title: '标题', key: 'title', dataIndex: 'title', width: 220, ellipsis: true, tooltip: true },
  {
    title: '前置条件',
    key: 'precondition',
    dataIndex: 'precondition',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '测试场景',
    key: 'test_point',
    dataIndex: 'test_point',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '测试数据',
    key: 'test_data',
    dataIndex: 'test_data',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  { title: '测试类型', key: 'test_types', dataIndex: 'test_types', width: 150 },
  { title: '优先级', key: 'priority', dataIndex: 'priority', width: 90, align: 'center' },
  {
    title: '测试层级',
    key: 'scenario_layer',
    dataIndex: 'scenario_layer',
    width: 120,
    align: 'center',
  },
  {
    title: '验证类型',
    key: 'scenario_type',
    dataIndex: 'scenario_type',
    width: 110,
    align: 'center',
  },
  { title: '执行场景', key: 'scenario_tags', dataIndex: 'scenario_tags', width: 220 },
  {
    title: '自动化用例 ID',
    key: 'automation_case_ids',
    dataIndex: 'automation_case_ids',
    width: 150,
  },
  { title: '变更', key: 'change_status', dataIndex: 'change_status', width: 90, align: 'center' },
  {
    title: '自动化影响',
    key: 'automation_impact_status',
    dataIndex: 'automation_impact_status',
    width: 120,
    align: 'center',
  },
  {
    title: '备注',
    key: 'remark',
    dataIndex: 'remark',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'module',
    width: 240,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    align: 'center',
    fixed: 'right',
    width: 120,
  },
]

export const suiteScrollWidth = suiteColumns.reduce(
  (width, column) => width + Number(column.width || 0),
  0
)
export const caseScrollWidth = caseColumns.reduce(
  (width, column) => width + Number(column.width || 0),
  0
)
