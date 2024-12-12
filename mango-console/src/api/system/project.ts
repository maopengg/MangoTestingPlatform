import { deleted, get, post, put } from '@/api/http'
export function getUserDepartmentList(data: object) {
  return get({
    url: '/system/project',
    data: () => {
      return data
    },
  })
}

export function postUserDepartmentList(data: object) {
  return post({
    url: '/system/project',
    data: () => {
      return data
    },
  })
}

export function putUserDepartmentList(data: object) {
  return put({
    url: '/system/project',
    data: () => {
      return data
    },
  })
}

export function deleteUserDepartmentList(id: number | string[] | number[]) {
  return deleted({
    url: '/system/project',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getUserProjectAll() {
  return get({
    url: '/system/project/all',
    data: () => {
      return {}
    },
  })
}
export function getUserProjectProductName() {
  return get({
    url: '/system/project/product/name',
    data: () => {
      return {}
    },
  })
}
export function getUserTestObjName() {
  return get({
    url: '/system/project/environment/name',
    data: () => {
      return {}
    },
  })
}
