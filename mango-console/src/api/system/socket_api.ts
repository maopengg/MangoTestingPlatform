import { get, post, put } from '@/api/http'

export function getSystemSocketAllUserSum() {
  return get({
    url: '/system/socket/all/user/sum',
    data: () => {
      return {}
    },
  })
}

export function getSystemSocketUserList(data: object) {
  return get({
    url: '/system/socket/user/list',
    data: () => {
      return data
    },
  })
}

export function getSystemSocketCurrentActuatorStatus() {
  return get({
    url: '/system/socket/current/actuator/status',
    data: () => {
      return {}
    },
  })
}

export function getSystemSocketAllUserList(data: object) {
  return get({
    url: '/system/socket/all/user/list',
    data: () => {
      return data
    },
  })
}

export function getSystemSocketPutOpenStatus(username: string, status: number) {
  return put({
    url: '/system/socket/put/user/open/status',
    data: () => {
      return {
        username: username,
        status: status,
      }
    },
  })
}

export function getSystemSocketPutDebug(username: string, status: number) {
  return put({
    url: '/system/socket/put/user/debug',
    data: () => {
      return {
        username: username,
        status: status,
      }
    },
  })
}

export function postSystemSocketActuatorConfigRequest(username: string) {
  return post({
    url: '/system/socket/actuator/config/request',
    data: () => ({ username }),
  })
}

export function getSystemSocketActuatorConfigResult(requestId: string) {
  return get({
    url: '/system/socket/actuator/config/result',
    data: () => ({ request_id: requestId }),
  })
}

export function putSystemSocketActuatorConfig(username: string, config: Record<string, any>) {
  return put({
    url: '/system/socket/actuator/config',
    data: () => ({ username, config }),
  })
}

export function getSystemSocketActuatorConfigSaveResult(requestId: string) {
  return get({
    url: '/system/socket/actuator/config/save-result',
    data: () => ({ request_id: requestId }),
  })
}

export function getSystemSocketNewBrowser(id: number | null, is_recording: number) {
  return get({
    url: '/system/socket/new/browser',
    data: () => {
      return {
        id: id,
        is_recording: is_recording,
      }
    },
  })
}
