import { deleted, get, post, put } from '@/api/http'

export function getApiHeaderReferenceCounts(ids: Array<string | number>) {
  return get({ url: '/api/headers/reference-counts', data: () => ({ ids: ids.join(',') }) })
}
export function getApiHeaderReferenceCases(id: string | number, page = 1, pageSize = 20) {
  return get({ url: '/api/headers/reference-cases', data: () => ({ id, page, pageSize }) })
}

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
  return put({ url: '/api/headers',
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
