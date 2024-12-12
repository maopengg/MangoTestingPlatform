import { deleted, get, post, put } from '@/api/http'

export function getSystemTasks(data: object) {
  return get({
    url: 'system/tasks',
    data: () => {
      return data
    },
  })
}

export function postSystemTasks(data: object) {
  return post({
    url: 'system/tasks',
    data: () => {
      return data
    },
  })
}
export function putSystemTasks(data: object) {
  return put({
    url: 'system/tasks',
    data: () => {
      return data
    },
  })
}

export function deleteSystemTasks(id: number | string[] | number[]) {
  return deleted({
    url: 'system/tasks',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getSystemTriggerTiming(id: number) {
  return get({
    url: 'system/tasks/trigger/timing',
    data: () => {
      return {
        id: id,
      }
    },
  })
}
export function getSystemTasksName(case_type: number) {
  return get({
    url: 'system/tasks/name',
    data: () => {
      return { case_type: case_type }
    },
  })
}
export function putSystemScheduledPutStatus(id: number, status: number) {
  return put({
    url: 'system/tasks/status',
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
    url: 'system/tasks/notice',
    data: () => {
      return {
        id: id,
        is_notice: status,
      }
    },
  })
}
