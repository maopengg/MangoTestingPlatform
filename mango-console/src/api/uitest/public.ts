import { deleted, get, post, put } from '@/api/http'

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

export function deleteUiPublic(id: number | string[] | number[]) {
  return deleted({
    url: '/ui/public',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function putUiPublicPutStatus(id: number, status: number) {
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
