import { useTableColumn } from '@/hooks/table'

export const tableScroll = { x: 1250, y: '100%' }
export const tableColumns = useTableColumn([
  { title: 'ID', key: 'index', dataIndex: 'id', width: 100, align: 'center' },
  {
    title: '项目绑定',
    key: 'binding',
    dataIndex: 'binding',
    ellipsis: true,
    tooltip: true,
    align: 'left',
    width: 260,
  },
  {
    title: '仓库 / 分支',
    key: 'repository',
    dataIndex: 'repository',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 210,
  },
  {
    title: '自动化类型',
    key: 'auto_type',
    dataIndex: 'auto_type',
    width: 120,
  },
  {
    title: '测试目录',
    key: 'test_dir',
    dataIndex: 'test_dir',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 260,
  },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    ellipsis: true,
    tooltip: true,
    align: 'left',
    width: 180,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 120,
  },
])
