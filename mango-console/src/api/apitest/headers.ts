import { deleted, get, post, put } from '@/api/http'
export function getApiHeaders(data: object) {
  return get({
    url: '/api/headers',
    data: () => {
      return data
    },
  })
}

export function postApiHeaders(data: object) {
  return post({
    url: '/api/headers',
    data: () => {
      return data
    },
  })
}
export function putApiHeaders(data: object) {
  return put({
    url: '/api/headers',
    data: () => {
      return data
    },
  })
}
export function deleteApiHeaders(id: number | string[] | number[]) {
  return deleted({
    url: '/api/headers',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function putApiHeadersPutStatus(id: number, status: number) {
  return put({
    url: '/api/headers/status',
    data: () => {
      return {
        id: id,
        status: status,
      }
    },
  })
}
