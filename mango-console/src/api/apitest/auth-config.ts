import { deleted, get, post, put } from '@/api/http'

export function getApiAuthConfig(data: object) {
  return get({
    url: '/api/auth/config',
    data: () => data,
  })
}

export function postApiAuthConfig(data: object) {
  return post({
    url: '/api/auth/config',
    data: () => data,
  })
}

export function putApiAuthConfig(data: object) {
  return put({
    url: '/api/auth/config',
    data: () => data,
  })
}

export function deleteApiAuthConfig(id: number | string[] | number[]) {
  return deleted({
    url: '/api/auth/config',
    data: () => ({ id }),
  })
}

export function putApiAuthConfigStatus(id: number, status: number) {
  return put({
    url: '/api/auth/config/status',
    data: () => ({ id, status }),
  })
}

export function postApiAuthConfigRefresh(id: number) {
  return post({
    url: '/api/auth/config/refresh',
    data: () => ({ id }),
  })
}

export function postApiAuthConfigClear(id: number) {
  return post({
    url: '/api/auth/config/clear',
    data: () => ({ id }),
  })
}

export function getApiAuthConfigCache(id: number) {
  return get({
    url: '/api/auth/config/cache',
    data: () => ({ id }),
  })
}
