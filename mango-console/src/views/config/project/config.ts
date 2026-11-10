import type { FormItem } from '@/types/components'
import type { ProjectDraft, ProjectRecord } from './types'
import { createIdSearchValue } from '@/utils/id-search'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { reactive, ref } from 'vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'
export const projectNameField = { label: '项目名称', placeholder: '请输入项目名称' }
export function createProjectDraft(record?: ProjectRecord): ProjectDraft {
  return { name: record?.name ?? '' }
}
export function createConditionItems() {
  const fields: Array<Omit<FormItem, 'disabled'>> = [
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入项目ID',
      value: createIdSearchValue(),
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'name',
      label: '项目名称',
      type: 'input',
      placeholder: '请输入项目名称',
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
    title: '项目名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  { ...updateUserColumn(), key: 'update_user' },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 180,
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 70,
    align: 'center',
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    align: 'center',
    width: 160,
  },
])
