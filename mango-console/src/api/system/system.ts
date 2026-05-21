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
  method: string
  actual?: string | number | boolean | null
  expect?: string | number | boolean | null
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
