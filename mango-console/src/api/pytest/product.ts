import { deleted, get, post, put } from '@/api/http'

export function postPytestProduct(data: any) {
  return post({
    url: 'pytest/product',
    data: () => {
      return data
    },
  })
}

export function deletePytestProduct(id: number) {
  return deleted({
    url: 'pytest/product',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getPytestProduct(data: any) {
  return get({
    url: 'pytest/product',
    data: () => {
      return data
    },
  })
}

export function putPytestProduct(data: object) {
  return put({
    url: 'pytest/product',
    data: () => {
      return data
    },
  })
}

export function getPytestUpdate() {
  return get({
    url: 'pytest/product/update',
    data: () => {
      return {}
    },
  })
}

export function getPytestPush() {
  return get({
    url: 'pytest/product/push',
    data: () => {
      return {}
    },
  })
}

export function getPytestProductRead(id: any) {
  return get({
    url: 'pytest/product/read',
    data: () => {
      return { id: id }
    },
  })
}

export function postPytestProductWrite(id: any, file_content: any) {
  return post({
    url: 'pytest/product/write',
    data: () => {
      return { id: id, file_content: file_content }
    },
  })
}

export function getPytestProductName(projectProductId: any) {
  return get({
    url: 'pytest/product/name',
    data: () => {
      return { project_product_id: projectProductId }
    },
  })
}
