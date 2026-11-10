import { deleted, get, post, put } from '@/api/http'
import { readUserNames, invalidateUserNames } from './user-name-cache'
import type { Response } from '@/api/http'

function userNamesChanged(response: Response) {
  if (response.code === 200) invalidateUserNames()
  return response
}

export function getUserName(force = false) {
  return readUserNames(() => get({
    url: '/user/info/name',
    data: () => {
      return {}
    },
  }), force)
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
  }).then(userNamesChanged)
}

export function registerUser(data: object) {
  return post({
    url: '/user/info/register',
    data: () => {
      return data
    },
  }).then(userNamesChanged)
}

export function putUserInfo(data: object) {
  return put({
    url: '/user/info',
    data: () => {
      return data
    },
  }).then(userNamesChanged)
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

export function deleteUserInfo(id: number | string | string[] | number[]) {
  return deleted({
    url: '/user/info',
    data: () => {
      return {
        id: id,
      }
    },
  }).then(userNamesChanged)
}

export function postUserPassword(data: object) {
  return put<unknown>({
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
  return get<unknown>({
    url: '/user/info/cache',
    data: () => ({}),
  })
}

export function clearUserCacheData(data: object) {
  return deleted<unknown>({
    url: '/user/info/cache',
    data: () => data,
  })
}
