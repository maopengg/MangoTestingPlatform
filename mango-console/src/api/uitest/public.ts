import { deleted, get, post, put } from '@/api/http'

export function getUiPublicReferenceCounts(ids: Array<string | number>) {
  return get({ url: '/ui/public/reference-counts', data: () => ({ ids: ids.join(',') }) })
}
export function getUiPublicReferenceCases(id: string | number, page = 1, pageSize = 20) {
  return get({ url: '/ui/public/reference-cases', data: () => ({ id, page, pageSize }) })
}

export function getUiPublic(data: object) {
  return get({
    url: '/ui/public',
    data: () => {
      return data
    },
  })
}

export function postUiPublic(data: object) {
  return post({
    url: '/ui/public',
    data: () => {
      return data
    },
  })
}

export function putUiPublic(data: object) {
  return put({
    url: '/ui/public',
    data: () => {
      return data
    },
  })
}

export function deleteUiPublic(id: number | string | Array<number | string>) {
  return deleted({
    url: '/ui/public',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function putUiPublicPutStatus(id: number | string, status: number) {
  return put({
    url: '/ui/public/status',
    data: () => {
      return {
        id: id,
        status: status,
      }
    },
  })
}
