import { deleted, get, post, put } from '@/api/http'

export function getUserAllRole() {
  return get({
    url: '/user/role/all',
    data: () => {
      return {}
    },
  })
}

export function getUserRoleList(data: object) {
  return get({
    url: '/user/role',
    data: () => {
      return data
    },
  })
}

export function postUserRoleList(data: object) {
  return post({
    url: '/user/role',
    data: () => {
      return data
    },
  })
}

export function putUserRoleList(data: object) {
  return put({
    url: '/user/role',
    data: () => {
      return data
    },
  })
}

export function deleteUserRoleList(id: number | string[] | number[]) {
  return deleted({
    url: '/user/role',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
