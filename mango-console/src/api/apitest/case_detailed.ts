import { deleted, get, post, put } from '@/api/http'

export function getApiCaseDetailed(caseId: any) {
  return get({
    url: '/api/case/detailed',
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}

export function postApiCaseDetailed(data: object) {
  return post({
    url: '/api/case/detailed',
    data: () => {
      return data
    },
  })
}

export function putApiCaseDetailed(data: object) {
  return put({
    url: '/api/case/detailed',
    data: () => {
      return data
    },
  })
}

export function deleteApiCaseDetailed(id: number | string[] | number[], parentId: any = null) {
  const data: any = {
    id: id,
  }
  if (parentId) {
    data['parent_id'] = parentId
  }
  return deleted({
    url: '/api/case/detailed',
    data: () => {
      return data
    },
  })
}

export function putApiPutCaseSort(data: object) {
  return put({
    url: '/api/case/detailed/sort',
    data: () => {
      return {
        case_sort_list: data,
      }
    },
  })
}

export function putApiPutRefreshApiInfo(id: number) {
  return put({
    url: '/api/case/detailed/refresh',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
