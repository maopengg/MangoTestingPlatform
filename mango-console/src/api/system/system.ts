import { get, post } from '@/api/http'

export function getSystemEnum() {
  return get({
    url: '/system/enum',
    data: () => {
      return {}
    },
  })
}

export function getSystemEnumShare() {
  return get({
    url: '/system/enum/share',
    data: () => {
      return {}
    },
  })
}

export function getSystemRandomList() {
  return get({
    url: '/system/variable/random/list',
    data: () => {
      return {}
    },
  })
}

export function getSystemRandomData(name: string) {
  return get({
    url: '/system/variable/value',
    data: () => {
      return { name: name }
    },
  })
}

export function getSystemAssertionList() {
  return get({
    url: '/system/assertion/list',
    data: () => {
      return {}
    },
  })
}

export function postSystemAssertionTest(data: {
  method?: string
  actual?: unknown
  expect?: unknown
  assertions?: Array<{
    name: string
    logic: 'AND' | 'OR'
    items: Array<Record<string, unknown> & { method: string }>
  }>
}) {
  return post({
    url: '/system/assertion/test',
    data: () => data,
  })
}

export function postSystemSetDebugLog(is_debug: any) {
  return post({
    url: '/system/set/debug/log',
    data: () => {
      return { is_debug: is_debug }
    },
  })
}

export function postSystemMethodCacheRefresh(type: string) {
  return post({
    url: '/system/method/cache/refresh',
    data: () => {
      return { type }
    },
  })
}
