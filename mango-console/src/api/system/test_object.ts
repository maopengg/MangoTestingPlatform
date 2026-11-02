import { deleted, get, post, put } from '@/api/http'

export interface TestObjectProbeResult {
  address: string
  connected: boolean
  host: string
  port: number | null
  resolved_ips: string[]
  elapsed_ms: number
  message: string
}

export function testObjectConnection(id: number, address: string) {
  return post<TestObjectProbeResult>({ url: '/system/test/object/test', data: { id, address }, timeout: 10000 })
}

export function getUserTestObject(data: object) {
  return get({
    url: '/system/test/object',
    data: () => {
      return data
    },
  })
}

export function postUserTestObject(data: object) {
  return post({
    url: '/system/test/object',
    data: () => {
      return data
    },
  })
}

export function putUserTestObject(data: object) {
  return put({ url: '/system/test/object',
    data: () => {
      return data
    },
  })
}

export function deleteUserTestObject(id: number | string[] | number[]) {
  return deleted({
    url: '/system/test/object',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function putUserTestObjectPutStatus(data: object) {
  return put({
    url: '/system/test/object/status',
    data: () => {
      return data
    },
  })
}
