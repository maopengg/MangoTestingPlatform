import { deleted, get, post, put } from '@/api/http'

export function getSystemTestSuite(data: object) {
  return get({
    url: 'system/test/suite',
    data: () => {
      return data
    },
  })
}
export function postSystemTestSuite(data: object) {
  return post({
    url: 'system/test/suite',
    data: () => {
      return data
    },
  })
}
export function putSystemTestSuite(data: object) {
  return put({
    url: 'system/test/suite',
    data: () => {
      return data
    },
  })
}

export function deleteSystemTestSuite(id: number | string[] | number[]) {
  return deleted({
    url: 'system/test/suite',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
