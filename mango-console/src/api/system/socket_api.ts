import { get } from '@/api/http'

export function getSystemSocketAllUserSum() {
  return get({
    url: '/system/socket/all/user/sum',
    data: () => {
      return {}
    },
  })
}

export function getSystemSocketUserList(data: object) {
  return get({
    url: '/system/socket/user/list',
    data: () => {
      return data
    },
  })
}
export function getSystemSocketAllUserList(data: object) {
  return get({
    url: '/system/socket/all/user/list',
    data: () => {
      return data
    },
  })
}
