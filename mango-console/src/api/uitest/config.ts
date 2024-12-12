import { deleted, get, post, put } from '@/api/http'

export function putUiConfigPutStatus(data: object) {
  return put({
    url: '/ui/config/status',
    data: () => {
      return data
    },
  })
}

export function getUiConfigNewBrowserObj(id: number | null, is_recording: number) {
  return get({
    url: '/ui/config/new/browser',
    data: () => {
      return {
        id: id,
        is_recording: is_recording,
      }
    },
  })
}
export function getUiConfig(data: object) {
  return get({
    url: '/ui/config',
    data: () => {
      return data
    },
  })
}

export function postUiConfig(data: object) {
  return post({
    url: '/ui/config',
    data: () => {
      return data
    },
  })
}
export function putUiConfig(data: object) {
  return put({
    url: '/ui/config',
    data: () => {
      return data
    },
  })
}
export function deleteUiConfig(id: number | string[] | number[]) {
  return deleted({
    url: '/ui/config',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
