import { get } from '@/api/http'

export interface SystemErrorRecordQuery {
  category?: string
  source?: string
  keyword?: string
  page?: number
  pageSize?: number
}

export function getSystemErrorRecordList(data: SystemErrorRecordQuery) {
  return get({
    url: 'system/runtime/recent-errors',
    data: () => data,
  })
}
