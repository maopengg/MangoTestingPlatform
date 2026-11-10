import type { ReportSearchItem } from './types'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { reactive } from 'vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'

export const reportTableScrollX = 1250

// 搜索条件
export function createConditionItems() {
  const items: ReportSearchItem[] = reactive([
    {
      key: 'task_name',
      label: '任务名称',
      type: 'input',
      placeholder: '请输入任务名称',
      value: '',
      reset() {
        this.value = ''
      },
    },
    {
      key: 'status',
      label: '状态',
      type: 'select',
      placeholder: '请选择状态',
      value: [],
      reset() {
        this.value = []
      },
    },
  ])
  enableMultiSelectSearch(items)
  return items
}

// 表格列
export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '任务名称',
    key: 'task_name',
    dataIndex: 'task_name',
    align: 'left',
    width: 200,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    align: 'center',
    width: 100,
  },
  {
    title: '消息内容',
    key: 'msg',
    dataIndex: 'msg',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 300,
  },
  {
    title: '是否通知',
    key: 'is_notice',
    dataIndex: 'is_notice',
    align: 'center',
    width: 100,
  },
  {
    title: '通知组',
    key: 'notice_group',
    dataIndex: 'notice_group',
    align: 'left',
    width: 150,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    align: 'center',
    width: 180,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 120,
    align: 'center',
  },
])
