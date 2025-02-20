import { deleted, get, post, put } from '@/api/http'

export function postPytestTools(data: any) {
  return post({
    url: 'pytest/tools',
    data: () => {
      return data
    },
  })
}

export function deletePytestTools(id: number) {
  return deleted({
    url: 'pytest/tools',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getPytestTools(data: any) {
  return get({
    url: 'pytest/tools',
    data: () => {
      return data
    },
  })
}

export function putPytestTools(data: object) {
  return put({
    url: 'pytest/tools',
    data: () => {
      return data
    },
  })
}
export function getPytestToolsUpdate() {
  return get({
    url: 'pytest/tools/update',
    data: () => {
      return {}
    },
  })
}
