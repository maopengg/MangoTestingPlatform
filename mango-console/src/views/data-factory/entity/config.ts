import { useTable, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'

const table = useTable()

export const entityConditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入ID',
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
    key: 'datasource_alias',
    label: '逻辑数据源',
    type: 'select',
    placeholder: '请选择逻辑源',
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
])

export const entityTableColumns = useTableColumn([
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
    title: '逻辑数据源',
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
  },
  {
    title: '表名',
    key: 'table_name',
    dataIndex: 'table_name',
    align: 'left',
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
    width: 100,
  },
  {
    title: '创建方式',
    key: 'create_type',
    dataIndex: 'create_type',
    width: 110,
  },
  {
    title: '清理顺序',
    key: 'cleanup_order',
    dataIndex: 'cleanup_order',
    width: 100,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
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
    width: 80,
  },
  {
    title: '主键',
    key: 'primary_key',
    dataIndex: 'primary_key',
    width: 80,
  },
  {
    title: '自增',
    key: 'autoincrement',
    dataIndex: 'autoincrement',
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
    width: 120,
  },
  {
    title: '说明',
    key: 'message',
    dataIndex: 'message',
  },
])
