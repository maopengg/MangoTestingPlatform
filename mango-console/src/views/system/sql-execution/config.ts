import { reactive, ref } from 'vue'
import { FormItem } from '@/types/components'
import { useTable, useTableColumn } from '@/hooks/table'
import { createIdSearchValue } from '@/utils/id-search'

const table = useTable()
export const tableScrollX = 2450

export const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: '记录ID',
    type: 'input',
    placeholder: '请输入记录ID',
    value: createIdSearchValue(),
  },
  {
    key: 'project_product_id',
    label: '项目产品',
    type: 'select',
    placeholder: '请选择项目产品',
    value: ref(''),
  },
  {
    key: 'source_type',
    label: '来源类型',
    type: 'select',
    placeholder: '请选择来源类型',
    value: ref(''),
  },
  {
    key: 'source_id',
    label: '来源ID',
    type: 'input',
    placeholder: '请输入Case或资产ID',
    value: createIdSearchValue('', false),
  },
  {
    key: 'source_stage',
    label: '执行阶段',
    type: 'select',
    placeholder: '请选择执行阶段',
    value: ref(''),
  },
  {
    key: 'test_env',
    label: '测试环境',
    type: 'select',
    placeholder: '请选择测试环境',
    value: ref(''),
  },
  {
    key: 'datasource_alias_id',
    label: '逻辑数据源',
    type: 'select',
    placeholder: '请选择逻辑数据源',
    value: ref(''),
  },
  {
    key: 'status',
    label: '执行状态',
    type: 'select',
    placeholder: '请选择执行状态',
    value: ref(''),
  },
  {
    key: 'is_slow',
    label: '性能状态',
    type: 'select',
    placeholder: '请选择性能状态',
    value: ref(''),
  },
  {
    key: 'duration_min',
    label: '最小耗时',
    type: 'input',
    placeholder: '毫秒',
    value: ref(''),
  },
  {
    key: 'duration_max',
    label: '最大耗时',
    type: 'input',
    placeholder: '毫秒',
    value: ref(''),
  },
  {
    key: 'sql_keyword',
    label: 'SQL关键字',
    type: 'input',
    placeholder: '请输入SQL关键字',
    value: ref(''),
  },
  {
    key: 'create_time',
    label: '执行时间',
    type: 'range',
    placeholder: '请选择执行时间',
    value: ref([]),
  },
])

export const tableColumns = useTableColumn([
  table.indexColumn,
  { title: '执行时间', key: 'create_time', dataIndex: 'create_time', width: 170 },
  {
    title: '项目产品',
    key: 'project_product_name',
    dataIndex: 'project_product_name',
    align: 'left',
    width: 150,
    ellipsis: true,
    tooltip: true,
  },
  { title: '测试环境', key: 'test_env', dataIndex: 'test_env', width: 100 },
  {
    title: '逻辑数据源',
    key: 'datasource_alias_name',
    dataIndex: 'datasource_alias_name',
    align: 'left',
    width: 160,
    ellipsis: true,
    tooltip: true,
  },
  { title: '来源类型', key: 'source_type', dataIndex: 'source_type', width: 140 },
  { title: '来源ID', key: 'source_id', dataIndex: 'source_id', width: 100 },
  { title: '执行阶段', key: 'source_stage', dataIndex: 'source_stage', width: 130 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 90 },
  { title: '耗时', key: 'duration_ms', dataIndex: 'duration_ms', width: 110 },
  { title: '性能', key: 'is_slow', dataIndex: 'is_slow', width: 90 },
  { title: '返回行数', key: 'row_count', dataIndex: 'row_count', width: 100 },
  { title: '影响行数', key: 'affected_rows', dataIndex: 'affected_rows', width: 100 },
  {
    title: 'SQL',
    key: 'sql_text',
    dataIndex: 'sql_text',
    align: 'left',
    width: 360,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '错误信息',
    key: 'error_message',
    dataIndex: 'error_message',
    align: 'left',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    key: 'operations',
    dataIndex: 'operations',
    width: 160,
    fixed: 'right',
  },
])
