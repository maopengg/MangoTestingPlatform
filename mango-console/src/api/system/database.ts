import { deleted, get, post, put } from '@/api/http'

export function getSystemDatabase(data: object) {
  return get({
    url: '/system/database',
    data: () => {
      return data
    },
  })
}

export function postSystemDatabase(data: object) {
  return post({
    url: '/system/database',
    data: () => {
      return data
    },
  })
}
export function putSystemDatabase(data: object) {
  return put({
    url: '/system/database',
    data: () => {
      return data
    },
  })
}
export function deleteSystemDatabase(id: number | string[] | number[]) {
  return deleted({
    url: '/system/database',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getSystemDatabaseTest(data: object) {
  return get({
    url: '/system/database/test',
    data: () => {
      return data
    },
  })
}
export function putSystemDatabaseStatus(data: object) {
  return put({
    url: '/system/database/status',
    data: () => {
      return data
    },
  })
}
