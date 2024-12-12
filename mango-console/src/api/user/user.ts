import { deleted, get, post, put } from '@/api/http'

export function getUserName() {
  return get({
    url: '/user/info/name',
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

export function putUserInfo(data: object) {
  return put({
    url: '/user/info',
    data: () => {
      return data
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

export function putUserPutProject(userId: number, key: any) {
  return put({
    url: '/user/info/project',
    data: () => {
      return { id: userId, selected_project: key }
    },
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
