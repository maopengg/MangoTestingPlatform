import { deleted, get, post, put, Response } from '@/api/http'
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
  })
}

export function putUserModule(data: object) {
  return put({
    url: '/system/module',
    data: () => {
      return data
    },
  })
}

export function deleteUserModule(id: number | string[] | number[]) {
  return deleted({
    url: '/system/module',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getUserModuleName(projectProductId: number | string | null): Promise<Response> {
  return get({
    url: '/system/module/name',
    data: () => {
      return {
        project_product_id: projectProductId,
      }
    },
  })
}
