import { deleted, get, post, put } from '@/api/http'

export function getApiCaseSuiteDetailed(caseSuiteId: any) {
  return get({
    url: '/api/case/suite/detailed',
    data: () => {
      return {
        case_suite_id: caseSuiteId,
      }
    },
  })
}

export function postApiCaseSuiteDetailed(data: object, parent_id: any) {
  // @ts-ignore
  data['parent_id'] = parent_id
  return post({
    url: '/api/case/suite/detailed',
    data: () => {
      return data
    },
  })
}

export function putApiCaseSuiteDetailed(data: object, parent_id: any) {
  // @ts-ignore
  data['parent_id'] = parent_id
  return put({
    url: '/api/case/suite/detailed',
    data: () => {
      return data
    },
  })
}

export function deleteApiCaseSuiteDetailed(id: number | string[] | number[], parentId: any) {
  const data: any = {
    id: id,
  }
  if (parentId) {
    data['parent_id'] = parentId
  }
  return deleted({
    url: '/api/case/suite/detailed',
    data: () => {
      return data
    },
  })
}

export function putApiPutCaseSuiteSort(data: object) {
  return put({
    url: '/api/case/suite/detailed/sort',
    data: () => {
      return {
        case_sort_list: data,
      }
    },
  })
}
