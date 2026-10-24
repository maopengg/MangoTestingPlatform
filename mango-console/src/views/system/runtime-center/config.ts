import { useTableColumn } from '@/hooks/table'

export const tableScrollX = 1220

export const serviceColumns = useTableColumn([
  { title: '服务名称', key: 'service_name', dataIndex: 'service_name', width: 150 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 100 },
  { title: '在线实例', key: 'online_count', dataIndex: 'online_count', width: 100 },
  { title: '最近心跳', key: 'last_seen_at', dataIndex: 'last_seen_at', width: 170 },
  { title: '当前实例', key: 'instances', dataIndex: 'instances', width: 280 },
  { title: '关键参数', key: 'metadata', dataIndex: 'metadata', width: 260 },
  { title: '操作', key: 'actions', dataIndex: 'actions', fixed: 'right', width: 160 },
])
