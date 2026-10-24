import { useTable, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { createUpdateUserCondition, updateTimeColumn, updateUserColumn } from '@/utils/update-user'
import { enableMultiSelectSearch } from '@/utils/search-condition'

const table = useTable()

export const datasourceAliasConditionItems: Array<FormItem> = reactive([
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
])
enableMultiSelectSearch(datasourceAliasConditionItems)

export const datasourceAliasColumns = useTableColumn([
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
    title: '名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
  },
  {
    title: '类型',
    key: 'db_type',
    dataIndex: 'db_type',
    width: 120,
  },
  {
    title: '描述',
    key: 'description',
    dataIndex: 'description',
    align: 'left',
  },
  updateUserColumn(),
  updateTimeColumn(),
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])

export const datasourceBindingColumns = useTableColumn([
  table.indexColumn,
  {
    title: '测试环境',
    key: 'environment',
    dataIndex: 'environment',
    width: 180,
  },
  { title: '读取权限', key: 'db_c_status', dataIndex: 'db_c_status', width: 100 },
  { title: '写入权限', key: 'db_rud_status', dataIndex: 'db_rud_status', width: 110 },
  {
    title: '数据库配置',
    key: 'data_source',
    dataIndex: 'data_source',
  },
  {
    title: '描述',
    key: 'description',
    dataIndex: 'description',
  },
  updateUserColumn(),
  updateTimeColumn(),
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    width: 120,
  },
])
