import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { createUpdateUserCondition, updateTimeColumn, updateUserColumn } from '@/utils/update-user'
import { enableMultiSelectSearch } from '@/utils/search-condition'

export const templateScrollX = 2210
export const enumFieldNames = { value: 'key', label: 'title' }
export const statusOptions = [
  { key: 1, title: '启用' },
  { key: 0, title: '禁用' },
]

export function createConditionItems() {
  const fields: Array<Omit<FormItem, 'disabled'>> = [
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入ID',
      value: createIdSearchValue(),
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
      key: 'entity',
      label: '实体名称',
      type: 'select',
      placeholder: '请选择实体名称',
      value: ref(''),
    },
    {
      key: 'name',
      label: '场景名称',
      type: 'input',
      placeholder: '请输入场景名称',
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
      key: 'usage_scope',
      label: '场景用途',
      type: 'select',
      placeholder: '请选择用途',
      value: ref(''),
    },
    {
      key: 'status',
      label: '状态',
      type: 'select',
      placeholder: '请选择状态',
      value: ref(''),
    },
    createUpdateUserCondition(),
  ]
  return enableMultiSelectSearch(reactive(fields))
}

export const templateTableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '实体名称',
    key: 'entity',
    dataIndex: 'entity',
    align: 'left',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '描述',
    key: 'description',
    dataIndex: 'description',
    align: 'left',
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
    title: '场景用途',
    key: 'usage_scope',
    dataIndex: 'usage_scope',
    width: 110,
  },
  {
    title: '配置状态',
    key: 'config_status',
    dataIndex: 'config_status',
    width: 100,
  },
  {
    title: '默认场景',
    key: 'is_default',
    dataIndex: 'is_default',
    width: 100,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 90,
  },
  { ...updateUserColumn(), key: 'update_user', align: 'left' },
  { ...updateTimeColumn(), key: 'update_time' },
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
  },
])
