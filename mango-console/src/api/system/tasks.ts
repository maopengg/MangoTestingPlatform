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

export function getSystemTasksName() {
  return get({
    url: 'system/tasks/name',
    data: () => {
      return {}
    },
  })
}

export function getSystemTaskFireRecord(data: object) {
  return get({
    url: 'system/tasks/fire-record',
    data: () => {
      return data
    },
  })
}

export function getSystemTaskSystemJobs(data: object = {}) {
  return get({
    url: 'system/tasks/system/jobs',
    data: () => {
      return data
    },
  })
}

export function postSystemTaskSystemJobTrigger(jobKey: string) {
  return post({
    url: 'system/tasks/system/jobs/trigger',
    data: () => {
      return {
        job_key: jobKey,
      }
    },
  })
}
