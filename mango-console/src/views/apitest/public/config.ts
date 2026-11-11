import type { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'

export const enabledSearchOptions = [
  { key: 1, title: '开启' },
  { key: 0, title: '关闭' },
]

export function createConditionItems(): FormItem[] {
  const fields: Array<Omit<FormItem, 'disabled'>> = [
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入参数ID',
      value: createIdSearchValue(),
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'project_product',
      label: '项目/产品',
      value: ref(''),
      type: 'cascader',
      placeholder: '请选择产品',
      optionItems: [],
      reset: function () {},
    },
    {
      key: 'type',
      label: '类型',
      value: ref(''),
      type: 'select',
      placeholder: '请选择类型',
      optionItems: [],
      reset: function () {},
    },
    {
      key: 'test_envs',
      label: '被测环境',
      value: ref([]),
      type: 'select',
      placeholder: '请选择被测环境',
      optionItems: [],
      reset: function () {
        this.value = []
      },
    },
    {
      key: 'status',
      label: '默认开启',
      value: ref([]),
      type: 'select',
      placeholder: '请选择开启状态',
      optionItems: [],
      reset: function () {
        this.value = []
      },
    },
    createUpdateUserCondition(),
    {
      key: 'name',
      label: '参数名称',
      type: 'input',
      placeholder: '请输入参数名称',
      value: ref(''),
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'key',
      label: 'key',
      type: 'input',
      placeholder: '请输入key',
      value: ref(''),
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'value',
      label: 'value',
      type: 'input',
      placeholder: '请输入value',
      value: ref(''),
      reset: function () {
        this.value = ''
      },
    },
  ]
  const conditionItems = reactive(fields)
  return enableMultiSelectSearch(conditionItems)
}

export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '被测环境',
    key: 'test_env',
    dataIndex: 'test_env',
    width: 120,
  },
  {
    title: '类型',
    key: 'type',
    dataIndex: 'type',
    width: 100,
  },
  {
    title: '参数名称',
    key: 'name',
    dataIndex: 'name',
    ellipsis: true,
    tooltip: true,
    align: 'left',
    width: 200,
  },
  {
    title: 'key',
    key: 'key',
    dataIndex: 'key',
    ellipsis: true,
    tooltip: true,
    align: 'left',
    width: 300,
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
    title: '默认开启',
    key: 'status',
    dataIndex: 'status',
    width: 90,
  },
  {
    title: '分类标签', key: 'tags', dataIndex: 'tags', width: 200, align: 'left', ellipsis: true, tooltip: true,
  },
  {
    title: '逻辑数据库',
    key: 'datasource_alias',
    dataIndex: 'datasource_alias',
    ellipsis: true,
    tooltip: true,
    align: 'left',
    width: 160,
  },
  { ...updateUserColumn(), key: 'update_user' },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 180,
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
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])

export const tableScrollX = tableColumns.reduce(
  (total: number, column: { width?: number }) => total + Number(column.width || 0),
  0
)
export const COMMON_ENV_VALUE = '__common__'
export const codeVariableExample = `def variable(context):
    """
    函数名字和参数不可以改。
    必须返回 dict。
    dict 的 key 会作为变量 key，value 会作为变量值。
    接口执行时可以通过 \${tenant_id}、\${user_id} 引用。
    """
    return {
        "tenant_id": "14",
        "user_id": 123
    }`
