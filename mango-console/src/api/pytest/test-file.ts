import { deleted, get, post, put } from '@/api/http'

export function postPytestFile(data: any) {
  return post({
    url: 'pytest/file',
    data: () => {
      return data
    },
  })
}

export function deletePytestFile(id: number) {
  return deleted({
    url: 'pytest/file',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getPytestFile(data: any) {
  return get({
    url: 'pytest/file',
    data: () => {
      return data
    },
  })
}

export function putPytestFile(data: object) {
  return put({
    url: 'pytest/file',
    data: () => {
      return data
    },
  })
}

export function getPytestFileUpdate() {
  return get({
    url: 'pytest/file/update',
    data: () => {
      return {}
    },
  })
}
