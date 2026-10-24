import { useTableColumn } from '@/hooks/table'

export const tableColumns = useTableColumn([
  {
    title: '仓库',
    key: 'repository',
    dataIndex: 'repository',
    align: 'left',
    width: 220,
  },
  {
    title: '代码源',
    key: 'source',
    dataIndex: 'source',
    align: 'left',
    width: 360,
  },
  { title: '资产概览', key: 'assets', dataIndex: 'assets', width: 160 },
  { title: '同步信息', key: 'sync', dataIndex: 'sync', align: 'left', width: 230 },
  { title: '操作', key: 'actions', dataIndex: 'actions', fixed: 'right', width: 160 },
])
