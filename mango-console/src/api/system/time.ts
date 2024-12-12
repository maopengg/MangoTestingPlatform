import { deleted, get, post, put } from '@/api/http'

export function getSystemTime(data: object) {
  return get({
    url: 'system/time',
    data: () => {
      return data
    },
  })
}

export function postSystemTime(data: object) {
  return post({
    url: 'system/time',
    data: () => {
      return data
    },
  })
}
export function putSystemTime(data: object) {
  return put({
    url: 'system/time',
    data: () => {
      return data
    },
  })
}

export function deleteSystemTime(id: number | string[] | number[]) {
  return deleted({
    url: 'system/time',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getSystemTimingList() {
  return get({
    url: 'system/time/name',
    data: () => {
      return {}
    },
  })
}
