import { deleted, get, post, put, Response } from '@/api/http'
import { readModuleDirectory, invalidateModuleDirectoryCache } from './module-directory-cache'

function moduleChanged(response: Response) {
  if (response.code === 200) invalidateModuleDirectoryCache()
  return response
}

export function getUserModule(data: object) {
  return get({
    url: '/system/module',
    data: () => {
      return data
    },
  })
}

export function postUserModule(data: object) {
  return post({
    url: '/system/module',
    data: () => {
      return data
    },
  }).then(moduleChanged)
}

export function postUserModulePath(data: object) {
  return post({
    url: '/system/module/path',
    data: () => data,
  }).then(moduleChanged)
}

export function putUserModule(data: object) {
  return put({
    url: '/system/module',
    data: () => {
      return data
    },
  }).then(moduleChanged)
}

export function deleteUserModule(id: number | string[] | number[]) {
  return deleted({
    url: '/system/module',
    data: () => {
      return {
        id: id,
      }
    },
  }).then(moduleChanged)
}

export function getUserModuleName(projectProductId: any, force = false): Promise<Response> {
  if (Array.isArray(projectProductId)) projectProductId = projectProductId[projectProductId.length - 1] ?? null
  return readModuleDirectory('name', projectProductId, () => get({
    url: '/system/module/name',
    data: () => {
      return {
        project_product_id: projectProductId,
      }
    },
  }), force)
}

export function getUserModuleTree(projectProductId?: any, force = false): Promise<Response> {
  if (Array.isArray(projectProductId)) projectProductId = projectProductId[projectProductId.length - 1] ?? null
  return readModuleDirectory('tree', projectProductId, () => get({
    url: '/system/module/tree',
    data: () =>
      projectProductId === null || projectProductId === undefined
        ? {}
        : { project_product_id: projectProductId },
  }), force)
}
