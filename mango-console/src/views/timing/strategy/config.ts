import { FormItem } from '@/types/components'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'
import { enableMultiSelectSearch } from '@/utils/search-condition'

export const tableScrollX = 1200
export function createConditionItems(): FormItem[] {
  const fields: Array<Omit<FormItem, 'disabled'>> = [
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入定时策略ID',
    value: createIdSearchValue(),
    reset: function () {
      this.value = ''
    },
  },
  {
    key: 'name',
    label: '定时器介绍',
    type: 'input',
    placeholder: '请输入定时器介绍',
    value: ref(''),
    reset: function () {
      this.value = ''
    },
  },
  createUpdateUserCondition(),
  ]
  return enableMultiSelectSearch(reactive(fields))
}

export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },

  {
    title: '定时器介绍',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 250,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: 'Cron表达式',
    key: 'cron',
    dataIndex: 'cron',
    align: 'left',
    width: 220,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 180,
  },
  { ...updateUserColumn(), key: 'update_user' },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
