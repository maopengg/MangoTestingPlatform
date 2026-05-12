import { useTable, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'

const table = useTable()

export const templateConditionItems: Array<FormItem> = reactive([
  {
    key: 'project_product',
    label: '项目/产品',
    value: ref(''),
    type: 'cascader',
    placeholder: '请选择产品',
  },
  {
    key: 'entity',
    label: '实体',
    type: 'select',
    placeholder: '请选择实体',
    value: ref(''),
  },
  {
    key: 'module',
    label: '模块',
    type: 'select',
    placeholder: '请选择模块',
    value: ref(''),
  },
  {
    key: 'name',
    label: '模板名称',
    type: 'input',
    placeholder: '请输入模板名称',
    value: ref(''),
  },
  {
    key: 'cleanup_strategy',
    label: '清理策略',
    type: 'select',
    placeholder: '请选择策略',
    value: ref(''),
  },
  {
    key: 'status',
    label: '状态',
    type: 'select',
    placeholder: '请选择状态',
    value: ref(''),
  },
])

export const templateTableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'module',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '实体',
    key: 'entity',
    dataIndex: 'entity',
    width: 180,
  },
  {
    title: '描述',
    key: 'description',
    dataIndex: 'description',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '清理策略',
    key: 'cleanup_strategy',
    dataIndex: 'cleanup_strategy',
    width: 120,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 90,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 190,
  },
])
