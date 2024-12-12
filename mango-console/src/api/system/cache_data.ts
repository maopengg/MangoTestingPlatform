import { deleted, get, post, put } from '@/api/http'

export function postSystemCacheData(data: any) {
  return post({
    url: 'system/cache/data',
    data: () => {
      return data
    },
  })
}

export function deleteSystemCacheData(id: number) {
  return deleted({
    url: 'system/cache/data',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getSystemCacheData() {
  return get({
    url: 'system/cache/data',
    data: () => {
      return {}
    },
  })
}

export function putSystemCacheData(data: object) {
  return put({
    url: 'system/cache/data',
    data: () => {
      return data
    },
  })
}
