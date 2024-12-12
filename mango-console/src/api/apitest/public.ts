import { deleted, get, post, put } from '@/api/http'
export function getApiPublic(data: object) {
  return get({
    url: '/api/public',
    data: () => {
      return data
    },
  })
}

export function postApiPublic(data: object) {
  return post({
    url: '/api/public',
    data: () => {
      return data
    },
  })
}
export function putApiPublic(data: object) {
  return put({
    url: '/api/public',
    data: () => {
      return data
    },
  })
}
export function deleteApiPublic(id: number | string[] | number[]) {
  return deleted({
    url: '/api/public',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function putApiPublicPutStatus(id: number, status: number) {
  return put({
    url: '/api/public/status',
    data: () => {
      return {
        id: id,
        status: status,
      }
    },
  })
}
