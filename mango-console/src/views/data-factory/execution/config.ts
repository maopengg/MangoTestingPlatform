import { useTable, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'

const table = useTable()

export const executionConditionItems: Array<FormItem> = reactive([
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
    label: '模块',
    type: 'select',
    placeholder: '请选择模块',
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
    value: ref(''),
  },
])

export const executionTableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 150,
    ellipsis: true,
    tooltip: true,
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
    width: 70,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 70,
  },
  {
    title: '清理状态',
    key: 'cleanup_status',
    dataIndex: 'cleanup_status',
    width: 100,
  },

  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 170,
  },
])

export const executionItemColumns = useTableColumn([
  table.indexColumn,
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
    title: '清理顺序',
    key: 'cleanup_order',
    dataIndex: 'cleanup_order',
    width: 100,
  },
  {
    title: '清理状态',
    key: 'cleanup_status',
    dataIndex: 'cleanup_status',
    width: 120,
  },
  {
    title: '清理SQL',
    key: 'cleanup_sql',
    dataIndex: 'cleanup_sql',
    width: 320,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '插入SQL',
    key: 'insert_sql',
    dataIndex: 'insert_sql',
    width: 320,
    align: 'left',
    ellipsis: true,
    tooltip: true,
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
