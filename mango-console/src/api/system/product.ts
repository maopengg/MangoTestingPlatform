import { deleted, get, post, put, Response } from '@/api/http'

export function getUserProductAllModuleName(projectId: number | string | null): Promise<Response> {
  return get({
    url: '/system/product/all/module/name',
    data: () => {
      return {
        project_id: projectId,
      }
    },
  })
}
export function getUserProductName(projectId: number | null = null) {
  return get({
    url: '/system/product/name',
    data: () => {
      return {
        project_id: projectId,
      }
    },
  })
}
export function getUserProduct(data: object) {
  return get({
    url: '/system/product',
    data: () => {
      return data
    },
  })
}
export function postUserProduct(data: object) {
  return post({
    url: '/system/product',
    data: () => {
      return data
    },
  })
}

export function putUserProduct(data: object) {
  return put({
    url: '/system/product',
    data: () => {
      return data
    },
  })
}

export function deleteUserProduct(id: number | string[] | number[]) {
  return deleted({
    url: '/system/product',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
