import { deleted, get, post, put } from '@/api/http'

export function getSystemDataSource(data: object) {
  return get({ url: '/system/data-source', data: () => data })
}

export function postSystemDataSource(data: object) {
  return post({ url: '/system/data-source', data: () => data })
}

export function putSystemDataSource(data: object) {
  return put({ url: '/system/data-source', data: () => data })
}

export function deleteSystemDataSource(id: number | string[] | number[]) {
  return deleted({ url: '/system/data-source', data: () => ({ id }) })
}

export function getDataSourceDatabases(data: object) {
  return get({ url: '/system/data-source/databases', data: () => data })
}
export function queryDataSourceDatabase(data: object) {
  return post({ url: '/system/data-source/query', data: () => data })
}
export function getDataSourceBindings(data: object) {
  return get({ url: '/system/data-source/bindings', data: () => data })
}
export function getDataSourceSchemas(data: object) {
  return get({ url: '/system/data-source/schemas', data: () => data })
}
export function suggestDataSourceAlias(data: object) {
  return post({ url: '/system/data-source/suggest-alias', data: () => data })
}
