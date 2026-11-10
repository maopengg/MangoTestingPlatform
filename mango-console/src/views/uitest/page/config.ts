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
      placeholder: '请输入页面ID',
      value: createIdSearchValue(),
    },
    { key: 'name', label: '页面名称', type: 'input', placeholder: '请输入页面名称', value: '' },
    { key: 'url', label: '页面地址', type: 'input', placeholder: '请输入页面地址', value: '' },
    { key: 'project_product', label: '项目/产品', type: 'cascader', value: null },
    { key: 'module', label: '模块名称', type: 'select', value: null },
    {
      key: 'project_product__ui_client_type',
      label: '端类型',
      type: 'select',
      placeholder: '请选择端类型',
      value: [],
    },
    createUpdateUserCondition(),
  ]
  enableMultiSelectSearch(items)
  return reactive(items)
}
export const TABLE_SCROLL_X = 1840
export const tableColumns: Array<TableColumnData & { key: string | number }> = [
  { ...useTableIndexColumn(), align: 'center' },
  { title: '页面名称', key: 'name', width: 300, align: 'left', ellipsis: true, tooltip: true },
  { title: '页面地址', key: 'url', width: 360, align: 'left', ellipsis: true, tooltip: true },
  { title: '端类型', key: 'client', width: 110, align: 'center' },
  { ...updateUserColumn(), key: 'update_user', align: 'left', ellipsis: true, tooltip: true },
  { ...updateTimeColumn(), key: 'update_time', align: 'center' },
  {
    title: '项目/产品',
    key: 'project_product',
    width: 180,
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  { title: '模块', key: 'module', width: 240, align: 'left', ellipsis: true, tooltip: true },
  { title: '操作', key: 'actions', width: 160, align: 'center', fixed: 'right' },
]
