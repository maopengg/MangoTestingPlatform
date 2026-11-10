import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { enableMultiSelectSearch } from '@/utils/search-condition'

export const executionScrollX = 1990
export const enumFieldNames = { value: 'key', label: 'title' }

export const cleanupResourceColumns = [
  { title: '执行明细', dataIndex: 'alias', width: 160, ellipsis: true, tooltip: true },
  { title: 'ES索引', dataIndex: 'index', width: 240, ellipsis: true, tooltip: true },
  { title: '文档ID', dataIndex: 'document_id', width: 190, ellipsis: true, tooltip: true },
  { title: '数据库清理', dataIndex: 'sql_status', width: 120 },
  { title: 'ES回查', dataIndex: 'status', width: 120 },
  { title: '检查时间', dataIndex: 'checked_at', width: 200, ellipsis: true, tooltip: true },
  { title: '说明', dataIndex: 'error', width: 310, ellipsis: true, tooltip: true },
]

export function createConditionItems() {
  const fields: Array<Omit<FormItem, 'disabled'>> = [
    {
      key: 'execution_no',
      label: '执行编号',
      type: 'input',
      placeholder: '请输入执行编号',
      value: ref(''),
    },
    {
      key: 'project_product',
      label: '项目/产品',
      value: ref(''),
      type: 'cascader',
      placeholder: '请选择产品',
    },
    {
      key: 'module',
      label: '模块名称',
      type: 'select',
      placeholder: '请选择模块名称',
      value: ref(''),
    },
    {
      key: 'stage',
      label: '阶段',
      type: 'select',
      placeholder: '请选择阶段',
      value: ref(''),
    },
    {
      key: 'status',
      label: '状态',
      type: 'select',
      placeholder: '请选择状态',
      value: ref(''),
    },
    {
      key: 'cleanup_status',
      label: '清理状态',
      type: 'select',
      placeholder: '请选择清理状态',
      value: ref<number[]>([]),
      multiple: true,
      searchOperator: 'in',
    },
  ]
  return enableMultiSelectSearch(reactive(fields))
}

export const executionTableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '执行编号',
    key: 'execution_no',
    dataIndex: 'execution_no',
    width: 270,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '触发来源',
    key: 'source_display',
    dataIndex: 'source_display',
    align: 'left',
    width: 360,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '错误',
    key: 'error_message',
    dataIndex: 'error_message',
    width: 300,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: '阶段',
    key: 'stage',
    dataIndex: 'stage',
    align: 'center',
    width: 70,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    align: 'center',
    width: 70,
  },
  {
    title: '清理状态',
    key: 'cleanup_status',
    dataIndex: 'cleanup_status',
    align: 'center',
    width: 100,
  },
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
    fixed: 'right',
    width: 160,
    align: 'center',
  },
])

export const executionItemColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '别名',
    key: 'alias',
    dataIndex: 'alias',
    width: 120,
  },
  {
    title: '主键',
    key: 'primary_value',
    dataIndex: 'primary_value',
    width: 150,
  },
  {
    title: '实际落库位置',
    key: 'storage_snapshot',
    dataIndex: 'storage_snapshot',
    width: 260,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '清理顺序',
    key: 'cleanup_order',
    dataIndex: 'cleanup_order',
    align: 'center',
    width: 100,
  },
  {
    title: '清理状态',
    key: 'cleanup_status',
    dataIndex: 'cleanup_status',
    align: 'center',
    width: 120,
  },
  {
    title: '数据源执行记录',
    key: 'sql_executions',
    dataIndex: 'sql_executions',
    width: 420,
    align: 'left',
  },
  {
    title: '创建数据',
    key: 'data',
    dataIndex: 'data',
    width: 260,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
])
