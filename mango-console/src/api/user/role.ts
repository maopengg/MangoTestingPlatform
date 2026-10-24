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

export function getUserRolePermission(roleId: number) {
  return get({
    url: '/user/role/permission',
    data: () => {
      return {
        role_id: roleId,
      }
    },
  })
}

export function putUserRolePermission(data: object) {
  return put({
    url: '/user/role/permission',
    data: () => {
      return data
    },
  })
}
