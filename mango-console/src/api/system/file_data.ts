import { deleted, get, post, put } from '@/api/http'

export function getUserFile(type = 0) {
  return get({
    url: '/system/file',
    data: () => {
      return {
        type: type,
      }
    },
  })
}

export function postUserFile(data: object) {
  return post({
    url: '/system/file',
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    data: () => {
      return data
    },
  })
}

export function putUserFile(data: object) {
  return put({
    url: '/system/file',
    data: () => {
      return data
    },
  })
}

export function deleteUserFile(id: number | string[] | number[]) {
  return deleted({
    url: '/system/file',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
