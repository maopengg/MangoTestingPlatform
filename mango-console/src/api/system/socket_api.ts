import { get, put } from '@/api/http'

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

export function getSystemSocketPutOpenStatus(username: string, status: number) {
  return put({
    url: '/system/socket/put/user/open/status',
    data: () => {
      return {
        username: username,
        status: status,
      }
    },
  })
}

export function getSystemSocketNewBrowser(id: number | null, is_recording: number) {
  return get({
    url: '/system/socket/new/browser',
    data: () => {
      return {
        id: id,
        is_recording: is_recording,
      }
    },
  })
}
