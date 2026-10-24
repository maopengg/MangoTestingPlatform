import { deleted, get, post, put } from '@/api/http'

export function postSystemEmailTest(recipient: string) {
  return post({ url: '/system/email/test', data: () => ({ recipient }) })
}

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

export function getSystemCacheDataGrouped() {
  return get({
    url: 'system/cache/data/grouped',
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

export function getSystemCacheDataKeyValue(key: string) {
  return get({
    url: 'system/cache/data/key/value',
    data: () => {
      return { key: key }
    },
  })
}

export function postSystemRuntimeCacheClear() {
  return post({ url: 'system/cache/runtime/clear', data: () => ({}) })
}
