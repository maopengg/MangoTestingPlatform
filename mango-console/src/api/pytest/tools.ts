import { deleted, get, post, put } from '@/api/http'

export function postPytestTools(data: any) {
  return post({
    url: 'pytest/tools',
    data: () => {
      return data
    },
  })
}

export function deletePytestTools(id: any) {
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

export function getPytestToolsRead(id: any) {
  return get({
    url: 'pytest/tools/read',
    data: () => {
      return { id: id }
    },
  })
}

export function postPytestToolsWrite(id: any, file_content: any) {
  return post({
    url: 'pytest/tools/write',
    data: () => {
      return { id: id, file_content: file_content }
    },
  })
}
