import { deleted, get, post, put } from '@/api/http'

export function postPytestProject(data: any) {
  return post({
    url: 'pytest/project',
    data: () => {
      return data
    },
  })
}

export function deletePytestProject(id: number) {
  return deleted({
    url: 'pytest/project',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getPytestProject(data: any) {
  return get({
    url: 'pytest/project',
    data: () => {
      return data
    },
  })
}

export function putPytestProject(data: object) {
  return put({
    url: 'pytest/project',
    data: () => {
      return data
    },
  })
}
export function getPytestUpdate() {
  return get({
    url: 'pytest/project/update',
    data: () => {
      return {}
    },
  })
}
