import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { createUpdateUserCondition, updateTimeColumn, updateUserColumn } from '@/utils/update-user'
import { enableMultiSelectSearch } from '@/utils/search-condition'

export const aliasScrollX = 1260
export const bindingScrollX = 1460
export const enumFieldNames = { value: 'key', label: 'title' }

export function createConditionItems() {
  const fields: Array<Omit<FormItem, 'disabled'>> = [
    {
      key: 'project_product',
      label: '项目/产品',
      value: ref(''),
      type: 'cascader',
      placeholder: '请选择产品',
    },
    {
      key: 'name',
      label: '名称',
      type: 'input',
      placeholder: '请输入名称',
      value: ref(''),
    },
    {
      key: 'db_type',
      label: '数据库类型',
      type: 'select',
      placeholder: '请选择类型',
      value: ref(''),
    },
    createUpdateUserCondition(),
  ]
  return enableMultiSelectSearch(reactive(fields))
}

export const datasourceAliasColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '类型',
    key: 'db_type',
    dataIndex: 'db_type',
    align: 'center',
    width: 120,
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
  { ...updateUserColumn(), key: 'update_user', align: 'left' },
  { ...updateTimeColumn(), key: 'update_time' },
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
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    align: 'center',
    fixed: 'right',
    width: 160,
  },
])

export const datasourceBindingColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '测试环境',
    key: 'environment',
    dataIndex: 'environment',
    align: 'center',
    width: 180,
  },
  { title: '读取权限', key: 'db_c_status', dataIndex: 'db_c_status', align: 'center', width: 100 },
  {
    title: '写入权限',
    key: 'db_rud_status',
    dataIndex: 'db_rud_status',
    align: 'center',
    width: 110,
  },
  {
    title: '数据库配置',
    key: 'data_source',
    dataIndex: 'data_source',
    align: 'left',
    width: 300,
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
  { ...updateUserColumn(), key: 'update_user', align: 'left' },
  { ...updateTimeColumn(), key: 'update_time' },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    align: 'center',
    width: 160,
    fixed: 'right',
  },
])
