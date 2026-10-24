export const cacheColumns = [
  { title: '缓存名称', dataIndex: 'title', width: 180, ellipsis: true, tooltip: true },
  { title: '缓存标识', dataIndex: 'cache_key', width: 190, ellipsis: true, tooltip: true },
  { title: '当前值', dataIndex: 'display_value', slotName: 'display_value', width: 240, ellipsis: true, tooltip: true },
  { title: '说明', dataIndex: 'description', width: 320, ellipsis: true, tooltip: true },
  { title: '更新时间', dataIndex: 'updated_at', slotName: 'updated_at', width: 180, align: 'center' },
  { title: '操作', slotName: 'actions', width: 120, fixed: 'right', align: 'center' },
]

export interface UserCacheItem {
  cache_key: string
  title: string
  value: any
  display_value: any
  value_type: 'string' | 'number' | 'boolean' | 'json' | 'environment'
  description: string
  clearable: boolean
  updated_at?: string
  has_value: boolean
}

export interface UserCacheGroup {
  group_key: string
  title: string
  count: number
  value_count: number
  items: UserCacheItem[]
}
