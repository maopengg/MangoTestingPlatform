import { get, post } from '@/api/http'

export function getSystemEnum() {
  return get({
    url: '/system/enum',
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

export function postSystemSetDebugLog(is_debug: any) {
  return post({
    url: '/system/set/debug/log',
    data: () => {
      return { is_debug: is_debug }
    },
  })
}
