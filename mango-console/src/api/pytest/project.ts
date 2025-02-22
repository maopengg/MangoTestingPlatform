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

export function getPytestPush() {
  return get({
    url: 'pytest/project/push',
    data: () => {
      return {}
    },
  })
}

export function getPytestProjectRead(id: any) {
  return get({
    url: 'pytest/project/read',
    data: () => {
      return { id: id }
    },
  })
}

export function postPytestProjectWrite(id: any, file_content: any) {
  return post({
    url: 'pytest/project/write',
    data: () => {
      return { id: id, file_content: file_content }
    },
  })
}

export function getPytestProjectName(projectProductId: any) {
  return get({
    url: 'pytest/project/name',
    data: () => {
      return { project_product_id: projectProductId }
    },
  })
}
