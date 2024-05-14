import { deleted, get, post, put } from '@/api/http'
import * as url from './url'
export function getSystemEnumExp() {
  return get({
    url: url.systemEnumExp,
    data: () => {
      return {}
    },
  })
}
export function getSystemTestObjName() {
  return get({
    url: url.systemTestObjName,
    data: () => {
      return {}
    },
  })
}
export function getSystemSocketAllUserSum() {
  return get({
    url: url.systemSocketAllUserSum,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumEnvironment() {
  return get({
    url: url.systemEnumEnvironment,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumClient() {
  return get({
    url: url.systemEnumClient,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumAutotest() {
  return get({
    url: url.systemEnumAutotest,
    data: () => {
      return {}
    },
  })
}

export function getSystemEnumPlatform() {
  return get({
    url: url.systemEnumPlatform,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumStatus() {
  return get({
    url: url.systemEnumStatus,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumUiElementOperation() {
  return get({
    url: url.systemEnumUiElementOperation,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumApiPublic() {
  return get({
    url: url.systemEnumApiPublic,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumMethod() {
  return get({
    url: url.systemEnumMethod,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumNotice() {
  return get({
    url: url.systemEnumNotice,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumEnd() {
  return get({
    url: url.systemEnumEnd,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumApiParameterType() {
  return get({
    url: url.systemEnumApiParameterType,
    data: () => {
      return {}
    },
  })
}
export function getSystemScheduledName(caseType: number) {
  return get({
    url: url.systemScheduledName,
    data: () => {
      return {
        case_type: caseType,
      }
    },
  })
}
export function getSystemEnumCaseLevel() {
  return get({
    url: url.systemEnumCaseLevel,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumBrowser() {
  return get({
    url: url.systemEnumBrowser,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumDrive() {
  return get({
    url: url.systemEnumDrive,
    data: () => {
      return {}
    },
  })
}
export function getSystemEnumUiPublic() {
  return get({
    url: url.systemEnumUiPublic,
    data: () => {
      return {}
    },
  })
}
export function getSystemTestSuiteReport(data: object) {
  return get({
    url: url.systemTestSuiteReport,
    data: () => {
      return data
    },
  })
}
export function postSystemTasksBatchSetCases(caseIdList: string[], scheduledTasksId: any) {
  return post({
    url: url.systemTasksBatchSetCases,
    data: () => {
      return {
        case_id_list: caseIdList,
        scheduled_tasks_id: scheduledTasksId,
      }
    },
  })
}
export function getSystemSocketUserList(data: object) {
  return get({
    url: url.systemSocketUserList,
    data: () => {
      return data
    },
  })
}
export function deleteSystemSocketUserList(id: number) {
  return deleted({
    url: url.systemSocketUserList,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getSystemDatabase(data: object) {
  return get({
    url: url.systemDatabase,
    data: () => {
      return data
    },
  })
}

export function postSystemDatabase(data: object) {
  return post({
    url: url.systemDatabase,
    data: () => {
      return data
    },
  })
}
export function putSystemDatabase(data: object) {
  return put({
    url: url.systemDatabase,
    data: () => {
      return data
    },
  })
}
export function deleteSystemDatabase(id: number | string[] | number[]) {
  return deleted({
    url: url.systemDatabase,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getSystemNotice(data: object) {
  return get({
    url: url.systemNotice,
    data: () => {
      return data
    },
  })
}

export function postSystemNotice(data: object) {
  return post({
    url: url.systemNotice,
    data: () => {
      return data
    },
  })
}
export function putSystemNotice(data: object) {
  return put({
    url: url.systemNotice,
    data: () => {
      return data
    },
  })
}
export function deleteSystemNotice(id: number | string[] | number[]) {
  return deleted({
    url: url.systemNotice,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function putSystemNoticePutStatus(id: number, status: number) {
  return put({
    url: url.systemNoticePutStatus,
    data: () => {
      return {
        id: id,
        status: status,
      }
    },
  })
}
export function getSystemNoticeTest(id: number) {
  return get({
    url: url.systemNoticeTest,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getSystemTestObject(data: object) {
  return get({
    url: url.systemTestObject,
    data: () => {
      return data
    },
  })
}

export function postSystemTestObject(data: object) {
  return post({
    url: url.systemTestObject,
    data: () => {
      return data
    },
  })
}
export function putSystemTestObject(data: object) {
  return put({
    url: url.systemTestObject,
    data: () => {
      return data
    },
  })
}

export function deleteSystemTestObject(id: number | string[] | number[]) {
  return deleted({
    url: url.systemTestObject,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function putSystemTestObjectPutStatus(data: object) {
  return put({
    url: url.systemTestObjectPutStatus,
    data: () => {
      return data
    },
  })
}

export function getSystemTime(data: object) {
  return get({
    url: url.systemTime,
    data: () => {
      return data
    },
  })
}

export function postSystemTime(data: object) {
  return post({
    url: url.systemTime,
    data: () => {
      return data
    },
  })
}
export function putSystemTime(data: object) {
  return put({
    url: url.systemTime,
    data: () => {
      return data
    },
  })
}

export function deleteSystemTime(id: number | string[] | number[]) {
  return deleted({
    url: url.systemTime,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getSystemScheduledTasks(data: object) {
  return get({
    url: url.systemScheduledTasks,
    data: () => {
      return data
    },
  })
}
export function getSystemTriggerTiming(id: number) {
  return get({
    url: url.systemTriggerTiming,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function postSystemScheduledTasks(data: object) {
  return post({
    url: url.systemScheduledTasks,
    data: () => {
      return data
    },
  })
}
export function putSystemScheduledTasks(data: object) {
  return put({
    url: url.systemScheduledTasks,
    data: () => {
      return data
    },
  })
}

export function deleteSystemScheduledTasks(id: number | string[] | number[]) {
  return deleted({
    url: url.systemScheduledTasks,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getSystemTimingList() {
  return get({
    url: url.systemTimingList,
    data: () => {
      return {}
    },
  })
}
export function putSystemScheduledPutStatus(id: number, status: number) {
  return put({
    url: url.systemScheduledPutStatus,
    data: () => {
      return {
        id: id,
        status: status,
      }
    },
  })
}
export function putSystemScheduledPutNotice(id: number, status: number) {
  return put({
    url: url.systemScheduledPutNotice,
    data: () => {
      return {
        id: id,
        is_notice: status,
      }
    },
  })
}
export function getSystemCacheData() {
  return get({
    url: url.systemCacheData,
    data: () => {
      return {}
    },
  })
}

export function putSystemCacheData(data: object) {
  return put({
    url: url.systemCacheData,
    data: () => {
      return data
    },
  })
}
export function getSystemRandomList() {
  return get({
    url: url.systemRandomList,
    data: () => {
      return {}
    },
  })
}
export function getSystemRandomData(name: string) {
  return get({
    url: url.systemRandomData,
    data: () => {
      return { name: name }
    },
  })
}
export function getSystemCacheKeyValue(key: string) {
  return get({
    url: url.systemCacheKeyValue,
    data: () => {
      return { key: key }
    },
  })
}
export function getSystemActivityLevel() {
  return get({
    url: url.systemActivityLevel,
    data: () => {
      return {}
    },
  })
}
export function getSystemCaseResultWeekSum() {
  return get({
    url: url.systemCaseResultWeekSum,
    data: () => {
      return {}
    },
  })
}
export function getSystemCaseRunSum() {
  return get({
    url: url.systemCaseRunSum,
    data: () => {
      return {}
    },
  })
}
export function getSystemCaseSum() {
  return get({
    url: url.systemCaseSum,
    data: () => {
      return {}
    },
  })
}

export function getSystemTasksRunCase(data: object) {
  return get({
    url: url.systemTasksRunCase,
    data: () => {
      return data
    },
  })
}

export function postSystemTasksRunCase(data: object) {
  return post({
    url: url.systemTasksRunCase,
    data: () => {
      return data
    },
  })
}
export function putSystemTasksRunCase(data: object) {
  return put({
    url: url.systemTasksRunCase,
    data: () => {
      return data
    },
  })
}

export function deleteSystemTasksRunCase(id: number | string[] | number[]) {
  return deleted({
    url: url.systemTasksRunCase,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function putSystemTasksCaseSort(sortList: any) {
  return put({
    url: url.systemTasksCaseSort,
    data: () => {
      return {
        sort_list: sortList,
      }
    },
  })
}
export function getSystemTasksTypeCaseName(type: any, module_name: number) {
  return get({
    url: url.systemTasksTypeCaseName,
    data: () => {
      return {
        type: type,
        module_name: module_name,
      }
    },
  })
}
export function putSystemTasksCaseTestObject(caseList: any, testObj: any) {
  return put({
    url: url.systemTasksCaseTestObject,
    data: () => {
      return {
        case_list: caseList,
        test_obj_id: testObj,
      }
    },
  })
}
