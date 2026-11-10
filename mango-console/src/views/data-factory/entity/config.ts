import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { createUpdateUserCondition, updateTimeColumn, updateUserColumn } from '@/utils/update-user'
import { enableMultiSelectSearch } from '@/utils/search-condition'

export const entityScrollX = 2340
export const enumFieldNames = { value: 'key', label: 'title' }
export const statusOptions = [
  { key: 1, title: '启用' },
  { key: 0, title: '禁用' },
]
export const sqlOperationOptions = [{ key: 2, title: 'SQL' }]

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
      key: 'datasource_alias',
      label: '逻辑数据库',
      type: 'select',
      placeholder: '请选择逻辑源',
      value: ref(''),
    },
    {
      key: 'name',
      label: '实体名称',
      type: 'input',
      placeholder: '请输入实体名称',
      value: ref(''),
    },
    {
      key: 'table_name',
      label: '表名',
      type: 'input',
      placeholder: '请输入表名',
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

export const entityTableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '逻辑数据库',
    key: 'datasource_alias',
    dataIndex: 'datasource_alias',
    align: 'left',
    width: 160,
    ellipsis: true,
    tooltip: true,
  },
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
    title: '表名',
    key: 'table_name',
    dataIndex: 'table_name',
    align: 'left',
    width: 180,
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
    title: '主键',
    key: 'primary_key',
    dataIndex: 'primary_key',
    align: 'center',
    width: 100,
  },
  {
    title: '创建方式',
    key: 'create_type',
    dataIndex: 'create_type',
    align: 'center',
    width: 110,
  },
  {
    title: '删除方式',
    key: 'delete_type',
    dataIndex: 'delete_type',
    align: 'center',
    width: 110,
  },
  {
    title: '清理顺序',
    key: 'cleanup_order',
    dataIndex: 'cleanup_order',
    align: 'center',
    width: 100,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    align: 'center',
    width: 100,
  },
  {
    title: '状态变更来源',
    key: 'status_change_source',
    dataIndex: 'status_change_source',
    align: 'center',
    width: 150,
  },
  { ...updateUserColumn(), key: 'update_user' },
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
    align: 'center',
  },
])

export const entityStatusLogColumns = useTableColumn([
  {
    title: '变更时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: '状态变更',
    key: 'status_change',
    dataIndex: 'status_change',
    align: 'center',
    width: 150,
  },
  {
    title: '变更来源',
    key: 'source_name',
    dataIndex: 'source_name',
    align: 'center',
    width: 150,
  },
  {
    title: '原因',
    key: 'reason',
    dataIndex: 'reason',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作人',
    key: 'operator',
    dataIndex: 'operator',
    width: 130,
  },
  {
    title: '关联记录',
    key: 'reference',
    dataIndex: 'reference',
    width: 160,
  },
])

export const fieldRuleColumns = useTableColumn([
  {
    title: '字段',
    key: 'name',
    dataIndex: 'name',
    fixed: 'left',
    align: 'left',
    width: 200,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '说明',
    key: 'label',
    dataIndex: 'label',
    width: 160,
  },
  {
    title: '生成方式',
    key: 'generator_type',
    dataIndex: 'generator_type',
    width: 180,
  },
  {
    title: '生成配置',
    key: 'generator_config',
    dataIndex: 'generator_config',
    width: 280,
  },
  {
    title: '实际值',
    key: 'preview_value',
    dataIndex: 'preview_value',
    width: 220,
  },
  {
    title: '可空',
    key: 'nullable',
    dataIndex: 'nullable',
    align: 'center',
    width: 80,
  },
  {
    title: '主键',
    key: 'primary_key',
    dataIndex: 'primary_key',
    align: 'center',
    width: 80,
  },
  {
    title: '自增',
    key: 'autoincrement',
    dataIndex: 'autoincrement',
    align: 'center',
    width: 80,
  },
  {
    title: 'DB类型',
    key: 'db_type',
    dataIndex: 'db_type',
    width: 130,
  },
  {
    title: '平台类型',
    key: 'platform_type',
    dataIndex: 'platform_type',
    width: 110,
  },
  {
    title: '排序',
    key: 'sort',
    dataIndex: 'sort',
    align: 'center',
    width: 100,
  },
])

export const batchEntityTableColumns = useTableColumn([
  {
    title: '表名',
    key: 'table_name',
    dataIndex: 'table_name',
    width: 180,
  },
  {
    title: '表注释',
    key: 'table_comment',
    dataIndex: 'table_comment',
    width: 180,
  },
  {
    title: '实体名称',
    key: 'name',
    dataIndex: 'name',
    width: 220,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    align: 'center',
    width: 120,
  },
  {
    title: '说明',
    key: 'message',
    dataIndex: 'message',
  },
])
