import { deleted, get, post, put } from '@/api/http'

export function getApiCaseSuite(data: object) {
  return get({
    url: '/api/case/suite',
    data: () => {
      return data
    },
  })
}

export function postApiCaseSuite(data: object) {
  return post({
    url: '/api/case/suite',
    data: () => {
      return data
    },
  })
}

export function putApiCaseSuite(data: object) {
  return put({
    url: '/api/case/suite',
    data: () => {
      return data
    },
  })
}
export function deleteApiCaseSuite(id: number | string[] | number[]) {
  return deleted({
    url: '/api/case/suite',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getApiCaseSuiteRun(caseId: any, test_env: any, caseSort: any) {
  return get({
    url: '/api/case/suite/test',
    data: () => {
      return {
        case_id: caseId,
        test_env: test_env,
        case_sort: caseSort,
      }
    },
  })
}

export function postApiCaseSuiteBatchRun(caseIdList: string[], test_env: any) {
  return post({
    url: '/api/case/suite/batch',
    data: () => {
      return {
        case_id_list: caseIdList,
        test_env: test_env,
      }
    },
  })
}
