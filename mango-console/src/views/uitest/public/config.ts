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
      placeholder: '请输入参数ID',
      value: createIdSearchValue(),
    },
    { key: 'project_product', label: '项目/产品', type: 'cascader', value: null },
    { key: 'type', label: '类型', type: 'select', placeholder: '请选择类型', value: [] },
    {
      key: 'test_envs',
      label: '被测环境',
      type: 'select',
      placeholder: '请选择被测环境',
      value: [],
    },
    { key: 'name', label: '参数名称', type: 'input', placeholder: '请输入参数名称', value: '' },
    { key: 'key', label: 'key', type: 'input', placeholder: '请输入 key', value: '' },
    { key: 'value', label: 'value', type: 'input', placeholder: '请输入 value', value: '' },
    createUpdateUserCondition(),
  ]
  enableMultiSelectSearch(items)
  return reactive(items)
}
export const TABLE_SCROLL_X = 2020
export const codeVariableExample = `def variable(context):
    """
    函数名字和参数不可以改。
    必须返回 dict。
    dict 的 key 会作为变量 key，value 会作为变量值。
    UI 执行时可以通过 \${tenant_id}、\${user_id} 引用。
    """
    return {
        "tenant_id": "14",
        "user_id": 123
    }`
export const tableColumns: Array<TableColumnData & { key: string | number }> = [
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '被测环境',
    key: 'test_env',
    dataIndex: 'test_env',
    width: 140,
    align: 'center',
  },
  {
    title: '类型',
    key: 'type',
    dataIndex: 'type',
    width: 120,
    align: 'center',
  },
  {
    title: '参数名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 200,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: 'key',
    key: 'key',
    dataIndex: 'key',
    align: 'left',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: 'value',
    key: 'value',
    dataIndex: 'value',
    align: 'left',
    width: 320,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '逻辑数据库',
    key: 'datasource_alias',
    dataIndex: 'datasource_alias',
    align: 'left',
    width: 180,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '默认开启',
    key: 'status',
    dataIndex: 'status',
    align: 'center',
    width: 100,
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
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    align: 'center',
    width: 160,
  },
]
