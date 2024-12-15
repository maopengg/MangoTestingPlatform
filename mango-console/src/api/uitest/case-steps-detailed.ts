import { deleted, get, post, put } from '@/api/http'

export function getUiCaseStepsDetailed(caseId: any) {
  return get({
    url: '/ui/case/steps/detailed',
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}

export function postUiCaseStepsDetailed(data: object, parent_id: any) {
  // @ts-ignore
  data['parent_id'] = parent_id
  return post({
    url: '/ui/case/steps/detailed',
    data: () => {
      return data
    },
  })
}
export function putUiCaseStepsDetailed(data: object, parent_id: any) {
  // @ts-ignore
  data['parent_id'] = parent_id
  return put({
    url: '/ui/case/steps/detailed',
    data: () => {
      return data
    },
  })
}
export function deleteUiCaseStepsDetailed(id: number | string[] | number[], parentId: number) {
  return deleted({
    url: '/ui/case/steps/detailed',
    data: () => {
      return {
        id: id,
        parent_id: parentId,
      }
    },
  })
}

export function getUiCaseStepsRefreshCacheData(id: number) {
  return get({
    url: '/ui/case/steps/detailed/refresh',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function putUiCasePutCaseSort(caseSortList: any) {
  return put({
    url: '/ui/case/steps/detailed/sort',
    data: () => {
      return {
        case_sort_list: caseSortList,
      }
    },
  })
}
