import { deleted, get, post, put } from '@/api/http'

export function postPytestAct(data: any) {
  return post({
    url: 'pytest/act',
    data: () => {
      return data
    },
  })
}

export function deletePytestAct(id: number) {
  return deleted({
    url: 'pytest/act',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getPytestAct(data: any) {
  return get({
    url: 'pytest/act',
    data: () => {
      return data
    },
  })
}

export function putPytestAct(data: object) {
  return put({
    url: 'pytest/act',
    data: () => {
      return data
    },
  })
}

export function getPytestActUpdate() {
  return get({
    url: 'pytest/act/update',
    data: () => {
      return {}
    },
  })
}
export function getPytestActRead(id: any) {
  return get({
    url: 'pytest/act/read',
    data: () => {
      return { id: id }
    },
  })
}
export function postPytestActWrite(id: any, file_content: any) {
  return post({
    url: 'pytest/act/write',
    data: () => {
      return { id: id, file_content: file_content }
    },
  })
}
