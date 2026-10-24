import { get, post } from '@/api/http'

export function getSystemWorkbenchTodos(data: {
  page: number
  pageSize: number
  status?: 'pending' | 'handled'
  source_type?: number
  event_type?: number
}) {
  return get({
    url: 'system/index/todos',
    data: () => data,
  })
}

export function postSystemWorkbenchTodoHandled(data: { id: number; handle_note?: string }) {
  return post({
    url: 'system/index/todos/handled',
    data,
  })
}

export function getSystemActivityLevel(params?: { page?: number; pageSize?: number }) {
  return get({
    url: 'system/index/activity/level',
    data: () => {
      return params || {}
    },
  })
}

export function getSystemIndexStatistics() {
  return get({
    url: 'system/index/statistics',
    data: () => {
      return {}
    },
  })
}

export function getSystemCaseResultWeekSum() {
  return get({
    url: 'system/index/result/week/sum',
    data: () => {
      return {}
    },
  })
}

export function getSystemCaseRunSum() {
  return get({
    url: 'system/index/run/sum',
    data: () => {
      return {}
    },
  })
}

export function getSystemCaseSum() {
  return get({
    url: 'system/index/sum',
    data: () => {
      return {}
    },
  })
}

export function getSystemProjectQuality() {
  return get({
    url: 'system/index/project/quality',
    data: () => {
      return {}
    },
  })
}
