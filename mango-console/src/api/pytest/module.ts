import { deleted, get, post, put } from '@/api/http'

export function postPytestModule(data: any) {
  return post({
    url: 'pytest/module',
    data: () => {
      return data
    },
  })
}

export function deletePytestModule(id: number) {
  return deleted({
    url: 'pytest/module',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getPytestModule(data: any) {
  return get({
    url: 'pytest/module',
    data: () => {
      return data
    },
  })
}

export function putPytestModule(data: object) {
  return put({
    url: 'pytest/module',
    data: () => {
      return data
    },
  })
}

export function getPytestModuleName(pytest_project_id: any) {
  return get({
    url: 'pytest/module/name',
    data: () => {
      return { pytest_project_id: pytest_project_id }
    },
  })
}
