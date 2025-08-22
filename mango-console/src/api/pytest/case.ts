import { deleted, get, post, put } from '@/api/http'

export function postPytestCase(data: any) {
  return post({
    url: 'pytest/case',
    data: () => {
      return data
    },
  })
}

export function deletePytestCase(id: number) {
  return deleted({
    url: 'pytest/case',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getPytestCase(data: any) {
  return get({
    url: 'pytest/case',
    data: () => {
      return data
    },
  })
}

export function putPytestCase(data: object) {
  return put({
    url: 'pytest/case',
    data: () => {
      return data
    },
  })
}

export function getPytestCaseUpdate() {
  return get({
    url: 'pytest/case/update',
    data: () => {
      return {}
    },
  })
}

export function getPytestCaseRead(id: any) {
  return get({
    url: 'pytest/case/read',
    data: () => {
      return { id: id }
    },
  })
}

export function postPytestCaseWrite(id: any, file_content: any) {
  return post({
    url: 'pytest/case/write',
    data: () => {
      return { id: id, file_content: file_content }
    },
  })
}

export function getPytestCaseTest(id: any, test_env: any) {
  return get({
    url: 'pytest/case/test',
    data: () => {
      return { id: id, test_env: test_env }
    },
  })
}
