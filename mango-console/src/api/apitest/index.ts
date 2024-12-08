// import { deleted, get, post, put } from '@/api/http'
// export function postApiImportUrl(data: object) {
//   return post({
//     url: '/api/import/api',
//     data: () => {
//       return data
//     },
//   })
// }
// export function getApiCase(data: object) {
//   return get({
//     url: '/api/case',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function postApiCase(data: object) {
//   return post({
//     url: '/api/case',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function putApiCase(data: object) {
//   return put({
//     url: '/api/case',
//     data: () => {
//       return data
//     },
//   })
// }
// export function deleteApiCase(id: number | string[] | number[]) {
//   return deleted({
//     url: '/api/case',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
//
// export function getApiCaseRun(caseId: any, test_env: any, caseSort: any) {
//   return get({
//     url: '/api/case/test',
//     data: () => {
//       return {
//         case_id: caseId,
//         test_env: test_env,
//         case_sort: caseSort,
//       }
//     },
//   })
// }
//
// export function postApiCaseBatchRun(caseIdList: string[], test_env: any) {
//   return post({
//     url: '/api/case/batch',
//     data: () => {
//       return {
//         case_id_list: caseIdList,
//         test_env: test_env,
//       }
//     },
//   })
// }
//
// export function postApiCaseCody(caseId: number) {
//   return post({
//     url: '/api/case/copy',
//     data: () => {
//       return {
//         case_id: caseId,
//       }
//     },
//   })
// }
//
// export function getApiCaseDetailed(caseId: any) {
//   return get({
//     url: '/api/case/detailed',
//     data: () => {
//       return {
//         case_id: caseId,
//       }
//     },
//   })
// }
//
// export function postApiCaseDetailed(data: object) {
//   return post({
//     url: '/api/case/detailed',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putApiCaseDetailed(data: object) {
//   return put({
//     url: '/api/case/detailed',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function deleteApiCaseDetailed(id: number | string[] | number[], parentId: any = null) {
//   const data: any = {
//     id: id,
//   }
//   if (parentId) {
//     data['parent_id'] = parentId
//   }
//   return deleted({
//     url: '/api/case/detailed',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function getApiInfoName(moduleId: any) {
//   return get({
//     url: '/api/info/name',
//     data: () => {
//       return {
//         module_id: moduleId,
//       }
//     },
//   })
// }
// export function putApiPutCaseSort(data: object) {
//   return put({
//     url: '/api/put/case/sort',
//     data: () => {
//       return {
//         case_sort_list: data,
//       }
//     },
//   })
// }
// export function putApiPutRefreshApiInfo(id: number) {
//   return put({
//     url: '/api/put/refresh/api/info',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
//
// export function getApiInfo(data: object) {
//   return get({
//     url: '/api/info',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function postApiInfo(data: object) {
//   return post({
//     url: '/api/info',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function putApiInfo(data: object) {
//   return put({
//     url: '/api/info',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function deleteApiInfo(id: number | string[] | number[]) {
//   return deleted({
//     url: '/api/info',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
// export function getApiCaseInfoRun(id: number | string[], testObj: any) {
//   return get({
//     url: '/api/info/run',
//     data: () => {
//       return {
//         id: id,
//         test_env: testObj,
//       }
//     },
//   })
// }
// export function putApiPutApiInfoType(idList: string[], type: number) {
//   return put({
//     url: '/api/put/api/info/type',
//     data: () => {
//       return {
//         id_list: idList,
//         type: type,
//       }
//     },
//   })
// }
//
// export function postApiCopyInfo(id: number) {
//   return post({
//     url: '/api/copy/info',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
//
// export function getApiPublic(data: object) {
//   return get({
//     url: '/api/public',
//     data: () => {
//       return data
//     },
//   })
// }
//
// export function postApiPublic(data: object) {
//   return post({
//     url: '/api/public',
//     data: () => {
//       return data
//     },
//   })
// }
// export function putApiPublic(data: object) {
//   return put({
//     url: '/api/public',
//     data: () => {
//       return data
//     },
//   })
// }
// export function deleteApiPublic(id: number | string[] | number[]) {
//   return deleted({
//     url: '/api/public',
//     data: () => {
//       return {
//         id: id,
//       }
//     },
//   })
// }
// export function putApiPublicPutStatus(id: number, status: number) {
//   return put({
//     url: '/api/public/put/status',
//     data: () => {
//       return {
//         id: id,
//         status: status,
//       }
//     },
//   })
// }
