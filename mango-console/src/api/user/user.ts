import { deleted, get, post, put } from '@/api/http'

export function getUserName() {
  return get({
    url: '/user/info/name',
    data: () => {
      return {}
    },
  })
}

export function getUserDepartmentName() {
  return get({
    url: '/user/info/department/name',
    data: () => {
      return {}
    },
  })
}

export function getUserInfo(data: object) {
  return get({
    url: '/user/info',
    data: () => {
      return data
    },
  })
}

export function postUserInfo(data: object) {
  return post({
    url: '/user/info',
    data: () => {
      return data
    },
  })
}

export function registerUser(data: object) {
  return post({
    url: '/user/info/register',
    data: () => {
      return data
    },
  })
}

export function putUserInfo(data: object) {
  return put({
    url: '/user/info',
    data: () => {
      return data
    },
  })
}

export function putUserApiKey(data: object) {
  return put({
    url: '/user/info/api-key',
    data: () => {
      return data
    },
  })
}

export function getCurrentUserApiKey() {
  return get({
    url: '/user/info/api-key',
    data: () => {
      return {}
    },
  })
}

export function deleteUserInfo(id: number | string[] | number[]) {
  return deleted({
    url: '/user/info',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postUserPassword(data: object) {
  return put({
    url: '/user/info/password',
    data: () => {
      return data
    },
  })
}

export function resetUserPassword(data: object) {
  return put({
    url: '/user/info/reset-password',
    data: () => data,
  })
}

export function resetUserApiKey(data: object) {
  return put({
    url: '/user/info/reset-api-key',
    data: () => data,
  })
}

export function putUserEnvironment(userId: number, key: any) {
  return put({
    url: '/user/info/environment',
    data: () => {
      return { id: userId, selected_environment: key }
    },
  })
}

export function getUserCacheData() {
  return get({
    url: '/user/info/cache',
    data: () => ({}),
  })
}

export function clearUserCacheData(data: object) {
  return deleted({
    url: '/user/info/cache',
    data: () => data,
  })
}
