import { deleted, get, post, put } from '@/api/http'
import type { UiAuthConfigPayload } from '@/types/ui-test/case'

export function getUiAuthConfig(data: Record<string, unknown>) {
  return get({
    url: '/ui/auth/config',
    data: () => data,
  })
}

export function postUiAuthConfig(data: UiAuthConfigPayload) {
  return post({
    url: '/ui/auth/config',
    data: () => data,
  })
}

export function putUiAuthConfig(data: UiAuthConfigPayload) {
  return put({ permissionKey: 'ui.auth_config',
    url: '/ui/auth/config',
    data: () => data,
  })
}

export function deleteUiAuthConfig(id: number | string[] | number[]) {
  return deleted({
    url: '/ui/auth/config',
    data: () => ({ id }),
  })
}

export function putUiAuthConfigStatus(id: number, status: number) {
  return put({
    url: '/ui/auth/config/status',
    data: () => ({ id, status }),
  })
}

export function postUiAuthConfigRefresh(id: number) {
  return post({
    url: '/ui/auth/config/refresh',
    data: () => ({ id }),
  })
}

export function postUiAuthConfigClear(id: number) {
  return post({
    url: '/ui/auth/config/clear',
    data: () => ({ id }),
  })
}

export function getUiAuthConfigCache(id: number) {
  return get({
    url: '/ui/auth/config/cache',
    data: () => ({ id }),
  })
}

export function postUiAuthConfigAutoStart(id: number) {
  return post({
    url: '/ui/auth/config/auto/start',
    data: () => ({ id }),
  })
}

export function postUiAuthConfigAutoCapture(id: number) {
  return post({
    url: '/ui/auth/config/auto/capture',
    data: () => ({ id }),
  })
}
