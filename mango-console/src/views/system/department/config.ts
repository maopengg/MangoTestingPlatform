import { useTable, useTableColumn } from '@/hooks/table'
import { updateUserColumn } from '@/utils/update-user'

const table = useTable()
export const tableScrollX = 1280

export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '部门名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 220,
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
    title: '部门描述',
    key: 'description',
    dataIndex: 'description',
    align: 'left',
    width: 280,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '创建时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 180,
  },
  { ...updateUserColumn(), key: 'update_user' },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 180,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
