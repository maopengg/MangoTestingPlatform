import { deleted, get, post, put } from '@/api/http'

export function getSystemNotice(data: object) {
  return get({
    url: '/system/notice',
    data: () => {
      return data
    },
  })
}

export function postSystemNotice(data: object) {
  return post({
    url: '/system/notice',
    data: () => {
      return data
    },
  })
}

export function putSystemNotice(data: object) {
  return put({
    url: '/system/notice',
    data: () => {
      return data
    },
  })
}

export function deleteSystemNotice(id: number | string[] | number[]) {
  return deleted({
    url: '/system/notice',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function putSystemNoticePutStatus(id: number, status: number) {
  return put({
    url: '/system/notice/status',
    data: () => {
      return {
        id: id,
        status: status,
      }
    },
  })
}

export function getSystemNoticeTest(id: number) {
  return get({
    url: 'system/notice/test',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
