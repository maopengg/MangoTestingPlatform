import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { updateTimeColumn, updateUserColumn } from '@/utils/update-user'

export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '元素名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 250, ellipsis: true, tooltip: true,
  },
  {
    title: '分类',
    key: 'category',
    dataIndex: 'category',
    width: 90,
  },
  {
    title: 'AI自愈',
    key: 'ai_heal_status',
    dataIndex: 'ai_heal_status',
    width: 90,
  },
  {
    title: '等待时间',
    key: 'sleep',
    dataIndex: 'sleep',
    width: 100,
  },
  {
    title: '预期事件/输入',
    key: 'expected_event',
    dataIndex: 'expected_event',
    align: 'left',
    width: 260,
  },
  {
    title: '第一组元素',
    key: 'locator_group_1',
    dataIndex: 'locator_group_1',
    align: 'left',
    width: 360,
  },
  {
    title: '第二组元素',
    key: 'locator_group_2',
    dataIndex: 'locator_group_2',
    align: 'left',
    width: 360,
  },
  {
    title: '第三组元素',
    key: 'locator_group_3',
    dataIndex: 'locator_group_3',
    align: 'left',
    width: 360,
  },
  {
    title: '元素描述',
    width: 240,
    key: 'prompt',
    dataIndex: 'prompt',
    align: 'left',
    ellipsis: true,
    tooltip: true,
  },
  { ...updateUserColumn(), key: 'update_user' },
  { ...updateTimeColumn(), key: 'update_time' },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])

export const TABLE_SCROLL_X = 2760
export function aiHealStatusMeta(status: number) {
  const values: Record<number, { label: string; color: string }> = {
    0: { label: '无基线', color: 'gray' }, 1: { label: '已有基线', color: 'green' },
    2: { label: '待确认', color: 'orange' }, 3: { label: '已修复', color: 'blue' }, 4: { label: '修复失败', color: 'red' },
  }
  return values[status] || values[0]
}
