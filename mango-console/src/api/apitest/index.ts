import { deleted, get, post, put } from '@/api/http'
import * as url from './url'
export function getApiCase(data: object) {
  return get({
    url: url.apiCase,
    data: () => {
      return data
    },
  })
}

export function postApiCase(data: object) {
  return post({
    url: url.apiCase,
    data: () => {
      return data
    },
  })
}
export function putApiCase(data: object) {
  return put({
    url: url.apiCase,
    data: () => {
      return data
    },
  })
}
export function deleteApiCase(id: number | string[] | number[]) {
  return deleted({
    url: url.apiCase,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getApiCaseRun(caseId: any, testObj: any, caseSort: any) {
  return get({
    url: url.apiCaseRun,
    data: () => {
      return {
        case_id: caseId,
        test_obj_id: testObj,
        case_sort: caseSort,
      }
    },
  })
}

export function postApiCaseBatchRun(caseIdList: string[], testObj: any) {
  return post({
    url: url.apiCaseBatchRun,
    data: () => {
      return {
        case_id_list: caseIdList,
        test_obj_id: testObj,
      }
    },
  })
}

export function postApiCaseCody(caseId: number) {
  return post({
    url: url.apiCaseCody,
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}
export function getApiInfoCaseResult(id: any) {
  return get({
    url: url.apiInfoCaseResult,
    data: () => {
      return {
        case_detailed_id: id,
      }
    },
  })
}

export function getApiCaseDetailed(caseId: any) {
  return get({
    url: url.apiCaseDetailed,
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}

export function postApiCaseDetailed(data: object) {
  return post({
    url: url.apiCaseDetailed,
    data: () => {
      return data
    },
  })
}
export function putApiCaseDetailed(data: object) {
  return put({
    url: url.apiCaseDetailed,
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
    url: url.apiCaseDetailed,
    data: () => {
      return data
    },
  })
}

export function getApiInfoName(moduleId: any) {
  return get({
    url: url.apiInfoName,
    data: () => {
      return {
        module_id: moduleId,
      }
    },
  })
}
export function putApiPutCaseSort(data: object) {
  return put({
    url: url.apiPutCaseSort,
    data: () => {
      return {
        case_sort_list: data,
      }
    },
  })
}
export function putApiPutRefreshApiInfo(id: number) {
  return put({
    url: url.apiPutRefreshApiInfo,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getApiInfo(data: object) {
  return get({
    url: url.apiInfo,
    data: () => {
      return data
    },
  })
}

export function postApiInfo(data: object) {
  return post({
    url: url.apiInfo,
    data: () => {
      return data
    },
  })
}

export function putApiInfo(data: object) {
  return put({
    url: url.apiInfo,
    data: () => {
      return data
    },
  })
}

export function deleteApiInfo(id: number | string[] | number[]) {
  return deleted({
    url: url.apiInfo,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getApiCaseInfoRun(id: number | string[], testObj: any) {
  return get({
    url: url.apiInfoRun,
    data: () => {
      return {
        id: id,
        test_obj_id: testObj,
      }
    },
  })
}
export function putApiPutApiInfoType(idList: string[], type: number) {
  return put({
    url: url.apiPutApiInfoType,
    data: () => {
      return {
        id_list: idList,
        type: type,
      }
    },
  })
}

export function postApiCopyInfo(id: number) {
  return post({
    url: url.apiCopyInfo,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getApiPublic(data: object) {
  return get({
    url: url.apiPublic,
    data: () => {
      return data
    },
  })
}

export function postApiPublic(data: object) {
  return post({
    url: url.apiPublic,
    data: () => {
      return data
    },
  })
}
export function putApiPublic(data: object) {
  return put({
    url: url.apiPublic,
    data: () => {
      return data
    },
  })
}
export function deleteApiPublic(id: number | string[] | number[]) {
  return deleted({
    url: url.apiPublic,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function putApiPublicPutStatus(id: number, status: number) {
  return put({
    url: url.apiPublicPutStatus,
    data: () => {
      return {
        id: id,
        status: status,
      }
    },
  })
}

export function getApiResultWeek() {
  return get({
    url: url.apiResultWeek,
    data: () => {
      return {}
    },
  })
}
export function getApiResultSuiteCase(testSuiteId: any) {
  return get({
    url: url.apiResultSuiteCase,
    data: () => {
      return {
        test_suite_id: testSuiteId,
      }
    },
  })
}
export function getApiInfoResult(id: any) {
  return get({
    url: url.apiInfoResult,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
