import { deleted, get, post, put } from '@/api/http'

export function postApiImportUrl(data: object) {
  return post({
    url: '/api/import/api',
    data: () => {
      return data
    },
  })
}

export function getApiCase(data: object) {
  return get({
    url: '/api/case',
    data: () => {
      return data
    },
  })
}

export function postApiCase(data: object) {
  return post({
    url: '/api/case',
    data: () => {
      return data
    },
  })
}

export function putApiCase(data: object) {
  return put({
    url: '/api/case',
    data: () => {
      return data
    },
  })
}

export function deleteApiCase(id: number | string[] | number[]) {
  return deleted({
    url: '/api/case',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getApiCaseRun(caseId: any, test_env: any, caseSort: any) {
  return get({
    url: '/api/case/test',
    data: () => {
      return {
        case_id: caseId,
        test_env: test_env,
        case_sort: caseSort,
      }
    },
  })
}

export function postApiCaseBatchRun(caseIdList: string[], test_env: any) {
  return post({
    url: '/api/case/batch',
    data: () => {
      return {
        case_id_list: caseIdList,
        test_env: test_env,
      }
    },
  })
}

export function postApiCaseCody(caseId: number) {
  return post({
    url: '/api/case/copy',
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}

export function getApiCaseName(moduleId: any) {
  return get({
    url: '/api/case/name',
    data: () => {
      return {
        module_id: moduleId,
      }
    },
  })
}
