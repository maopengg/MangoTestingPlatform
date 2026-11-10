import { deleted, get, post, put } from '@/api/http'

export function getUiPage(data: object) {
  return get({
    url: '/ui/page',
    data: () => {
      return data
    },
  })
}

export function postUiPage(data: object) {
  return post({
    url: '/ui/page',
    data: () => {
      return data
    },
  })
}

export function putUiPage(data: object) {
  return put({
    url: '/ui/page',
    data: () => {
      return data
    },
  })
}

export function deleteUiPage(id: number | string | Array<number | string>) {
  return deleted({
    url: '/ui/page',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getUiPageName(moduleId: number | string | null, projectProductId?: number | string) {
  return get({
    url: '/ui/page/name',
    data: () => {
      return {
        module_id: moduleId,
        project_product_id: projectProductId ?? undefined,
      }
    },
  })
}
