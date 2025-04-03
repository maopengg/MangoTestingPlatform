import { deleted, get, post, put } from '@/api/http'

export function getSystemTasksRunCase(data: object) {
  return get({
    url: 'system/tasks/details',
    data: () => {
      return data
    },
  })
}

export function postSystemTasksRunCase(data: object) {
  return post({
    url: 'system/tasks/details',
    data: () => {
      return data
    },
  })
}
export function putSystemTasksRunCase(data: object) {
  return put({
    url: 'system/tasks/details',
    data: () => {
      return data
    },
  })
}

export function deleteSystemTasksRunCase(id: number | string[] | number[]) {
  return deleted({
    url: 'system/tasks/details',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function postSystemTasksBatchSetCases(
  caseIdList: string[],
  scheduledTasksId: any,
  type: number
) {
  return post({
    url: 'system/tasks/details/batch/set/cases',
    data: () => {
      return {
        case_id_list: caseIdList,
        scheduled_tasks_id: scheduledTasksId,
        type: type,
      }
    },
  })
}

export function getSystemTasksTypeCaseName(type: any, moduleId: number) {
  return get({
    url: 'system/tasks/details/type/case/name',
    data: () => {
      return {
        type: type,
        module_id: moduleId,
      }
    },
  })
}
