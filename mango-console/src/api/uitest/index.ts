// import { deleted, get, post, put } from '@/api/http'
//
// export function getUiPage(data: object) {
//   return get({
//     url: '/ui/page',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function postUiPage(data: object) {
//   return post({
//     url: '/ui/page',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putUiPage(data: object) {
//   return put({
//     url: '/ui/page',
//     data: () => {
//       return data
//     },
//   })
// }
// export function deleteUiPage(id: number | string[] | number[]) {
//   return deleted({
//     url: '/ui/page',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
// export function postUiPageCopy(pageId: number | string) {
//   return post({
//     url: '/ui/page/copy',
//     data: () => {
//       return {
//         page_id: pageId,
//       }
//     },
//   })
// }
// export function getUiElement(pageId: any) {
//   return get({
//     url: '/ui/element',
//     data: () => {
//       return {
//         page_id: pageId,
//       }
//     },
//   })
// }
// export function deleteUiElement(id: number | string[] | number[]) {
//   return deleted({
//     url: '/ui/element',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
// export function postUiElement(data: object) {
//   return post({
//     url: '/ui/element',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putUiElement(data: object) {
//   return put({
//     url: '/ui/element',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putUiUiElementPutIsIframe(id: number, isIframe: number) {
//   return put({
//     url: '/ui/element/put/is/iframe',
//     data: () => {
//       return {
//         id: id,
//         is_iframe: isIframe,
//       }
//     },
//   })
// }
// export function getUiPageStepsDetailedOpe(pageType: any) {
//   return get({
//     url: '/ui/page/steps/detailed/ope',
//     data: () => {
//       return {
//         page_type: pageType,
//       }
//     },
//   })
// }
// export function getUiPageStepsDetailedAss(pageType: any) {
//   return get({
//     url: '/ui/page/steps/detailed/ass',
//     data: () => {
//       return {
//         page_type: pageType,
//       }
//     },
//   })
// }
//
// export function putUiUiElementTest(data: object) {
//   return post({
//     url: '/ui/element/test',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function getUiSteps(data: object) {
//   return get({
//     url: '/ui/steps',
//     data: () => {
//       return data
//     },
//   })
// }
// export function deleteUiSteps(id: number | string[] | number[]) {
//   return deleted({
//     url: '/ui/steps',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
// export function postUiSteps(data: object) {
//   return post({
//     url: '/ui/steps',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putUiSteps(data: object) {
//   return put({
//     url: '/ui/steps',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function getUiStepsRun(id: any, testObj: number) {
//   return get({
//     url: '/ui/steps/run',
//     data: () => {
//       return {
//         page_step_id: id,
//         te: testObj,
//       }
//     },
//   })
// }
//
// export function deleteUiStepsPutType(id: number | string[] | number[]) {
//   return put({
//     url: '/ui/steps/put/type',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
//
// export function getUiPageName(moduleId: number) {
//   return get({
//     url: '/ui/page/name',
//     data: () => {
//       return {
//         module_id: moduleId,
//       }
//     },
//   })
// }
// export function getUiPageStepsCopy(pageId: number) {
//   return post({
//     url: '/ui/copy/page/steps',
//     data: () => {
//       return {
//         page_id: pageId,
//       }
//     },
//   })
// }
//
// export function getUiPageStepsDetailed(id: any) {
//   return get({
//     url: '/ui/page/steps/detailed',
//     data: () => {
//       return {
//         page_step_id: id,
//       }
//     },
//   })
// }
//
// export function postUiPageStepsDetailed(data: object) {
//   return post({
//     url: '/ui/page/steps/detailed',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putUiPageStepsDetailed(data: object) {
//   return put({
//     url: '/ui/page/steps/detailed',
//     data: () => {
//       return data
//     },
//   })
// }
// export function deleteUiPageStepsDetailed(id: number | string[] | number[], parentId: number) {
//   return deleted({
//     url: '/ui/page/steps/detailed',
//     data: () => {
//       return {
//         id: id,
//         parent_id: parentId,
//       }
//     },
//   })
// }
// export function getUiUiElementName(id: any) {
//   return get({
//     url: '/ui/element/name',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
// export function putUiPagePutStepSort(data: any) {
//   return put({
//     url: '/ui/page/put/step/sort',
//     data: () => {
//       return {
//         step_sort_list: data,
//       }
//     },
//   })
// }
//
// export function getUiCase(data: object) {
//   return get({
//     url: '/ui/case',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function postUiCase(data: object) {
//   return post({
//     url: '/ui/case',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putUiCase(data: object) {
//   return put({
//     url: '/ui/case',
//     data: () => {
//       return data
//     },
//   })
// }
// export function deleteUiCase(id: number | string[] | number[]) {
//   return deleted({
//     url: '/ui/case',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
// export function postUiCaseCopy(caseId: number) {
//   return post({
//     url: '/ui/case/copy/case',
//     data: () => {
//       return {
//         case_id: caseId,
//       }
//     },
//   })
// }
// export function postUiRunCaseBatch(caseIdList: number[] | string[], testingEnvironment: any) {
//   return get({
//     url: 'ui/case/batch',
//     data: () => {
//       return {
//         case_id_list: caseIdList,
//         test_env: testingEnvironment,
//       }
//     },
//   })
// }
// export function getUiCaseRun(caseId: any, testingEnvironment: any) {
//   return get({
//     url: '/ui/case/test',
//     data: () => {
//       return {
//         case_id: caseId,
//         test_env: testingEnvironment,
//       }
//     },
//   })
// }
// export function getUiStepsPageStepsName(pageId: number) {
//   return get({
//     url: '/ui/steps/page/steps/name',
//     data: () => {
//       return {
//         page_id: pageId,
//       }
//     },
//   })
// }
//
// export function getUiCaseStepsDetailed(caseId: any) {
//   return get({
//     url: '/ui/case/steps/detailed',
//     data: () => {
//       return {
//         case_id: caseId,
//       }
//     },
//   })
// }
//
// export function postUiCaseStepsDetailed(data: object) {
//   return post({
//     url: '/ui/case/steps/detailed',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putUiCaseStepsDetailed(data: object) {
//   return put({
//     url: '/ui/case/steps/detailed',
//     data: () => {
//       return data
//     },
//   })
// }
// export function deleteUiCaseStepsDetailed(id: number | string[] | number[], parentId: number) {
//   return deleted({
//     url: '/ui/case/steps/detailed',
//     data: () => {
//       return {
//         id: id,
//         parent_id: parentId,
//       }
//     },
//   })
// }
// export function putUiConfigPutStatus(data: object) {
//   return put({
//     url: '/ui/config/put/status',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function getUiCaseStepsRefreshCacheData(id: number) {
//   return get({
//     url: '/ui/case/steps/refresh/cache/data',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
// export function getUiConfigNewBrowserObj(id: number | null, is_recording: number) {
//   return get({
//     url: '/ui/config/new/browser/obj',
//     data: () => {
//       return {
//         id: id,
//         is_recording: is_recording,
//       }
//     },
//   })
// }
// export function getUiConfig(data: object) {
//   return get({
//     url: '/ui/config',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function postUiConfig(data: object) {
//   return post({
//     url: '/ui/config',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putUiConfig(data: object) {
//   return put({
//     url: '/ui/config',
//     data: () => {
//       return data
//     },
//   })
// }
// export function deleteUiConfig(id: number | string[] | number[]) {
//   return deleted({
//     url: '/ui/config',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
//
// export function getUiPublic(data: object) {
//   return get({
//     url: '/ui/public',
//     data: () => {
//       return data
//     },
//   })
// }
// export function postUiPublic(data: object) {
//   return post({
//     url: '/ui/public',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putUiPublic(data: object) {
//   return put({
//     url: '/ui/public',
//     data: () => {
//       return data
//     },
//   })
// }
// export function deleteUiPublic(id: number | string[] | number[]) {
//   return deleted({
//     url: '/ui/public',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
// export function putUiPublicPutStatus(id: number, status: number) {
//   return put({
//     url: '/ui/public/put/status',
//     data: () => {
//       return {
//         id: id,
//         status: status,
//       }
//     },
//   })
// }
// export function getUiPageAssMethod() {
//   return get({
//     url: '/ui/page/ass/method',
//     data: () => {
//       return {}
//     },
//   })
// }
