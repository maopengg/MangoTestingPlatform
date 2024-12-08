import { deleted, get, post, put } from '@/api/http'

export function getUserLogs(data: object) {
  return get({
    url: '/user/user/logs',
    data: () => {
      return data
    },
  })
}

export function postUserLogs(data: object) {
  return post({
    url: '/user/user/logs',
    data: () => {
      return data
    },
  })
}

export function putUserLogs(data: object) {
  return put({
    url: '/user/user/logs',
    data: () => {
      return data
    },
  })
}

export function deleteUserLogs(id: number | string[] | number[]) {
  return deleted({
    url: '/user/user/logs',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
