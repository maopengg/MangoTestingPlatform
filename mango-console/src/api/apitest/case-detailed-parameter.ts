import { deleted, get, post, put } from '@/api/http'

export function getApiCaseDetailedParameter(caseId: any) {
  return get({
    url: '/api/case/detailed/parameter',
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}

export function postApiCaseDetailedParameter(data: object) {
  // @ts-ignore
  return post({
    url: '/api/case/detailed/parameter',
    data: () => {
      return data
    },
  })
}

export function putApiCaseDetailedParameter(data: object) {
  // @ts-ignore
  return put({
    url: '/api/case/detailed/parameter',
    data: () => {
      return data
    },
  })
}

export function deleteApiCaseDetailedParameter(id: number | string[] | number[], parentId: any) {
  const data: any = {
    id: id,
  }
  if (parentId) {
    data['parent_id'] = parentId
  }
  return deleted({
    url: '/api/case/detailed/parameter',
    data: () => {
      return data
    },
  })
}
