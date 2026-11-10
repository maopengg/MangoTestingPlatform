import { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { reactive, ref } from 'vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'

export const tableScrollX = 1800
export const requestMethodOptions = [
  { key: 'GET', title: 'GET' },
  { key: 'POST', title: 'POST' },
  { key: 'PUT', title: 'PUT' },
  { key: 'PATCH', title: 'PATCH' },
  { key: 'DELETE', title: 'DELETE' },
  { key: 'OPTIONS', title: 'OPTIONS' },
  { key: 'HEAD', title: 'HEAD' },
]

export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '昵称',
    key: 'user',
    dataIndex: 'user',
    align: 'left',
    width: 110,
    ellipsis: true,
    tooltip: true,
  },

  {
    title: 'IP',
    key: 'ip',
    dataIndex: 'ip',
    align: 'left',
    width: 150,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '来源',
    key: 'source_type',
    dataIndex: 'source_type',
    width: 90,
  },
  {
    title: '访问时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: 'url',
    key: 'url',
    dataIndex: 'url',
    align: 'left',
    width: 300,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: 'method',
    key: 'method',
    dataIndex: 'method',
    width: 100,
  },
  {
    title: '请求数据',
    key: 'request_data',
    dataIndex: 'request_data',
    align: 'left',
    width: 300,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: 'status_code',
    key: 'status_code',
    dataIndex: 'status_code',
    width: 90,
  },
  {
    title: '响应数据',
    key: 'response_data',
    dataIndex: 'response_data',
    align: 'left',
    width: 300,
    ellipsis: true,
    tooltip: true,
  },
])

export function createConditionItems(): FormItem[] {
  const items: FormItem[] = reactive([
  {
    key: 'user',
    label: '筛选用户',
    value: ref([]),
    type: 'select',
    multiple: true,
    searchOperator: 'in',
    placeholder: '请选择用户',
    optionItems: [],
    reset: function () { this.value = [] },
  },
  {
    key: 'source_type',
    label: '筛选来源',
    type: 'select',
    placeholder: '请选择来源',
    value: ref(''),
    optionItems: [],
    reset: function () { this.value = [] },
  },
  {
    key: 'method',
    label: '请求方法',
    type: 'select',
    placeholder: '请选择请求方法',
    value: ref(''),
    optionItems: [],
    reset: function () { this.value = [] },
  },
  {
    key: 'url',
    label: 'url',
    type: 'input',
    placeholder: '请输入url',
    value: ref(''),
    optionItems: [],
    reset: function () { this.value = '' },
  },
  {
    key: 'request_data',
    label: '请求数据',
    type: 'input',
    placeholder: '请输入请求数据',
    value: ref(''),
    optionItems: [],
    reset: function () { this.value = '' },
  },
  {
    key: 'response_data',
    label: '响应数据',
    type: 'input',
    placeholder: '请输入响应数据',
    value: ref(''),
    optionItems: [],
    reset: function () { this.value = '' },
  },
  ])
  return enableMultiSelectSearch(items)
}
