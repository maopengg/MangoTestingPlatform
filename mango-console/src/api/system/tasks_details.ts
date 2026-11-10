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

export function deleteSystemTasksRunCase(id: number | string | string[] | number[]) {
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
  caseIdList: Array<string | number>,
  scheduledTasksId: string | number,
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

export function postSystemTasksBatchSetCaseVersions(
  caseItems: Array<{ case_id: number; case_release_id: number }>,
  scheduledTasksId: any,
  type: number
) {
  return post({
    url: 'system/tasks/details/batch/set/cases',
    data: () => ({
      case_items: caseItems,
      scheduled_tasks_id: scheduledTasksId,
      type,
    }),
  })
}

export function getSystemTasksTypeCaseName(
  type: any,
  moduleId?: number | string,
  projectProductId?: any,
  moduleIds?: Array<number | string>,
  filters: Record<string, any> = {},
  taskId?: number | string
) {
  return get({
    url: 'system/tasks/details/type/case/name',
    data: () => {
      return {
        type: type,
        module_id: moduleId,
        project_product_id: projectProductId,
        module_ids: moduleIds?.join(','),
        task_id: taskId,
        ...filters,
      }
    },
  })
}
