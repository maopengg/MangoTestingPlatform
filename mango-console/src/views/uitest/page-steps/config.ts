import { reactive } from 'vue'
import type { FormItem } from '@/types/components'
import type { TableColumnData } from '@arco-design/web-vue'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { useTableIndexColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateTimeColumn, updateUserColumn } from '@/utils/update-user'

export function createConditionItems() {
  const items: Omit<FormItem, 'disabled'>[] = [
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入步骤ID',
      value: createIdSearchValue(),
    },
    { key: 'name', label: '步骤名称', type: 'input', placeholder: '请输入步骤名称', value: '' },
    { key: 'project_product', label: '项目/产品', type: 'cascader', value: null },
    { key: 'module', label: '模块名称', type: 'select', value: null },
    {
      key: 'page_id',
      label: '所属页面',
      type: 'select',
      placeholder: '请选择所属页面',
      value: [],
      multiple: true,
      searchOperator: 'in',
    },
    { key: 'status', label: '测试结果', type: 'select', placeholder: '请选择测试结果', value: [] },
    createUpdateUserCondition(),
  ]
  enableMultiSelectSearch(items)
  return reactive(items)
}
export const TABLE_SCROLL_X = 1830
export const tableColumns: Array<TableColumnData & { key: string | number }> = [
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '所属页面',
    key: 'page',
    dataIndex: 'page',
    align: 'left',
    width: 150,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '步骤名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 300,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '预估步骤顺序',
    key: 'run_flow',
    dataIndex: 'run_flow',
    width: 320,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '结果',
    key: 'status',
    dataIndex: 'status',
    align: 'center',
    width: 70,
  },
  { ...updateUserColumn(), key: 'update_user', align: 'left', ellipsis: true, tooltip: true },
  { ...updateTimeColumn(), key: 'update_time', align: 'center' },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'module',
    align: 'left',
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
    width: 160,
  },
]

export const referencedCaseColumns: Array<TableColumnData & { key: string | number }> = [
  {
    title: '用例ID',
    key: 'id',
    dataIndex: 'id',
    align: 'center',
    width: 90,
  },
  {
    title: '用例名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '负责人',
    key: 'case_people',
    dataIndex: 'case_people',
    align: 'left',
    width: 120,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '结果',
    key: 'status',
    dataIndex: 'status',
    align: 'center',
    width: 90,
  },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    align: 'center',
    width: 180,
  },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 180,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'module',
    width: 180,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
    align: 'center',
  },
]
