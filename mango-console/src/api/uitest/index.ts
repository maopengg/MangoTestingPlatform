import { deleted, get, post, put } from '@/api/http'
import * as url from './url'

export function getUiPage(data: object) {
  return get({
    url: url.uiPage,
    data: () => {
      return data
    },
  })
}

export function postUiPage(data: object) {
  return post({
    url: url.uiPage,
    data: () => {
      return data
    },
  })
}
export function putUiPage(data: object) {
  return put({
    url: url.uiPage,
    data: () => {
      return data
    },
  })
}
export function deleteUiPage(id: number | string[] | number[]) {
  return deleted({
    url: url.uiPage,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function postUiPageCopy(pageId: number | string) {
  return post({
    url: url.uiPageCopy,
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}
export function getUiElement(pageId: any) {
  return get({
    url: url.uiUiElement,
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}
export function deleteUiElement(id: number | string[] | number[]) {
  return deleted({
    url: url.uiUiElement,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function postUiElement(data: object) {
  return post({
    url: url.uiUiElement,
    data: () => {
      return data
    },
  })
}
export function putUiElement(data: object) {
  return put({
    url: url.uiUiElement,
    data: () => {
      return data
    },
  })
}
export function putUiUiElementPutIsIframe(id: number, isIframe: number) {
  return put({
    url: url.uiUiElementPutIsIframe,
    data: () => {
      return {
        id: id,
        is_iframe: isIframe,
      }
    },
  })
}
export function getUiPageStepsDetailedOpe(pageType: any) {
  return get({
    url: url.uiPageStepsDetailedOpe,
    data: () => {
      return {
        page_type: pageType,
      }
    },
  })
}
export function getUiPageStepsDetailedAss(pageType: any) {
  return get({
    url: url.uiPageStepsDetailedAss,
    data: () => {
      return {
        page_type: pageType,
      }
    },
  })
}

export function putUiUiElementTest(data: object) {
  return post({
    url: url.uiUiElementTest,
    data: () => {
      return data
    },
  })
}

export function getUiSteps(data: object) {
  return get({
    url: url.uiSteps,
    data: () => {
      return data
    },
  })
}
export function deleteUiSteps(id: number | string[] | number[]) {
  return deleted({
    url: url.uiSteps,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function postUiSteps(data: object) {
  return post({
    url: url.uiSteps,
    data: () => {
      return data
    },
  })
}
export function putUiSteps(data: object) {
  return put({
    url: url.uiSteps,
    data: () => {
      return data
    },
  })
}

export function getUiStepsRun(id: any, testObj: number) {
  return get({
    url: url.uiStepsRun,
    data: () => {
      return {
        page_step_id: id,
        te: testObj,
      }
    },
  })
}

export function deleteUiStepsPutType(id: number | string[] | number[]) {
  return deleted({
    url: url.uiStepsPutType,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getUiPageName(moduleId: number) {
  return get({
    url: url.uiPageName,
    data: () => {
      return {
        module_name: moduleId,
      }
    },
  })
}
export function getUiPageStepsCopy(pageId: number) {
  return post({
    url: url.uiPageStepsCopy,
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}

export function getUiPageStepsDetailed(id: any) {
  return get({
    url: url.uiPageStepsDetailed,
    data: () => {
      return {
        page_step_id: id,
      }
    },
  })
}

export function postUiPageStepsDetailed(data: object) {
  return post({
    url: url.uiPageStepsDetailed,
    data: () => {
      return data
    },
  })
}
export function putUiPageStepsDetailed(data: object) {
  return put({
    url: url.uiPageStepsDetailed,
    data: () => {
      return data
    },
  })
}
export function deleteUiPageStepsDetailed(id: number | string[] | number[], parentId: number) {
  return deleted({
    url: url.uiPageStepsDetailed,
    data: () => {
      return {
        id: id,
        parent_id: parentId,
      }
    },
  })
}
export function getUiUiElementName(id: any) {
  return get({
    url: url.uiUiElementName,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function putUiPagePutStepSort(data: any) {
  return put({
    url: url.uiPagePutStepSort,
    data: () => {
      return {
        step_sort_list: data,
      }
    },
  })
}

export function getUiCase(data: object) {
  return get({
    url: url.uiCase,
    data: () => {
      return data
    },
  })
}

export function postUiCase(data: object) {
  return post({
    url: url.uiCase,
    data: () => {
      return data
    },
  })
}
export function putUiCase(data: object) {
  return put({
    url: url.uiCase,
    data: () => {
      return data
    },
  })
}
export function deleteUiCase(id: number | string[] | number[]) {
  return deleted({
    url: url.uiCase,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function postUiCaseCopy(caseId: number) {
  return post({
    url: url.uiCaseCopy,
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}
export function postUiRunCaseBatch(caseIdList: number[] | string[], testingEnvironment: any) {
  return post({
    url: url.uiRunCaseBatch,
    data: () => {
      return {
        case_id_list: caseIdList,
        testing_environment: testingEnvironment,
      }
    },
  })
}
export function getUiCaseRun(caseId: any, testingEnvironment: any) {
  return get({
    url: url.uiCaseRun,
    data: () => {
      return {
        case_id: caseId,
        testing_environment: testingEnvironment,
      }
    },
  })
}
export function getUiStepsPageStepsName(pageId: number) {
  return get({
    url: url.uiStepsPageStepsName,
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}
export function putUiCasePutCaseSort(caseSortList: any) {
  return put({
    url: url.uiCasePutCaseSort,
    data: () => {
      return {
        case_sort_list: caseSortList,
      }
    },
  })
}

export function getUiCaseStepsDetailed(caseId: any) {
  return get({
    url: url.uiCaseStepsDetailed,
    data: () => {
      return {
        case_id: caseId,
      }
    },
  })
}

export function postUiCaseStepsDetailed(data: object) {
  return post({
    url: url.uiCaseStepsDetailed,
    data: () => {
      return data
    },
  })
}
export function putUiCaseStepsDetailed(data: object) {
  return put({
    url: url.uiCaseStepsDetailed,
    data: () => {
      return data
    },
  })
}
export function putUiConfigPutStatus(data: object) {
  return put({
    url: url.uiConfigPutStatus,
    data: () => {
      return data
    },
  })
}
export function deleteUiCaseStepsDetailed(id: number | string[] | number[], parentId: number) {
  return deleted({
    url: url.uiCaseStepsDetailed,
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
    url: url.uiCaseStepsRefreshCacheData,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getUiConfigNewBrowserObj(id: number) {
  return get({
    url: url.uiConfigNewBrowserObj,
    data: () => {
      return { id: id }
    },
  })
}
export function getUiConfig(data: object) {
  return get({
    url: url.uiConfig,
    data: () => {
      return data
    },
  })
}

export function postUiConfig(data: object) {
  return post({
    url: url.uiConfig,
    data: () => {
      return data
    },
  })
}
export function putUiConfig(data: object) {
  return put({
    url: url.uiConfig,
    data: () => {
      return data
    },
  })
}
export function deleteUiConfig(id: number | string[] | number[]) {
  return deleted({
    url: url.uiConfig,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getUiPublic(data: object) {
  return get({
    url: url.uiPublic,
    data: () => {
      return data
    },
  })
}
export function getUiCaseResultWeekSum() {
  return get({
    url: url.uiCaseResultWeekSum,
    data: () => {
      return {}
    },
  })
}

export function postUiPublic(data: object) {
  return post({
    url: url.uiPublic,
    data: () => {
      return data
    },
  })
}
export function putUiPublic(data: object) {
  return put({
    url: url.uiPublic,
    data: () => {
      return data
    },
  })
}
export function deleteUiPublic(id: number | string[] | number[]) {
  return deleted({
    url: url.uiPublic,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function putUiPublicPutStatus(id: number, status: number) {
  return put({
    url: url.uiPublicPutStatus,
    data: () => {
      return {
        id: id,
        status: status,
      }
    },
  })
}
export function getUiPageAssMethod() {
  return get({
    url: url.uiPageAssMethod,
    data: () => {
      return {}
    },
  })
}
export function getUiCaseResultSuiteGetCase(testSuiteId: any) {
  return get({
    url: url.uiCaseResultSuiteGetCase,
    data: () => {
      return {
        test_suite_id: testSuiteId,
      }
    },
  })
}
export function getUiEleResultEle(testSuiteId: any, pageStepId: number, caseId: number) {
  return get({
    url: url.uiEleResultEle,
    data: () => {
      return {
        test_suite_id: testSuiteId,
        page_step_id: pageStepId,
        case_id: caseId,
      }
    },
  })
}
