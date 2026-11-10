import { deleted, get, post, put } from '@/api/http'

export function postPytestProductImport(data: Record<string, unknown>): Promise<unknown> {
  return post({
    url: 'pytest/product/import',
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

export function getPytestProduct(data: {
  page: number
  pageSize: number
  project_product?: string | number
}): Promise<unknown> {
  return get({
    url: 'pytest/product',
    data: () => {
      return data
    },
  })
}

export function putPytestProduct(data: Record<string, unknown>): Promise<unknown> {
  return put({
    url: 'pytest/product',
    data: () => {
      return data
    },
  })
}

export function getPytestProductTestDirectories(
  id?: number,
  projectPath?: string,
  repositoryId?: number
) {
  return get({
    url: 'pytest/product/test-directories',
    data: () => {
      return { id: id, project_path: projectPath, repository_id: repositoryId }
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
