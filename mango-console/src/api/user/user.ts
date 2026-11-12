import { deleted, get, post, put } from '@/api/http'
import { readUserNames, invalidateUserNames } from './user-name-cache'
import type { Response } from '@/api/http'
import type { UserConfigUpdate } from '@/types/user-config'

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

export function resetOwnPassword() {
  return put<unknown>({ url: '/user/info/reset-own-password', data: () => ({}) })
}

export function resetUserApiKey(data: object) {
  return put({
    url: '/user/info/reset-api-key',
    data: () => data,
  })
}

export function getUserConfig(key?: string) {
  return get<unknown>({
    url: '/user/info/config',
    data: () => key === undefined ? {} : { key },
  })
}

export function updateUserConfig(data: UserConfigUpdate) {
  return put<unknown>({ url: '/user/info/config', data: () => data })
}

export function clearUserConfig(data: { key: string }) {
  return deleted<unknown>({
    url: '/user/info/config',
    data: () => data,
  })
}
