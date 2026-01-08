import { deleted, get, post, put } from '@/api/http'

export function getMonitoringTask(data: object) {
  return get({
    url: 'monitoring/task',
    data: () => {
      return data
    },
  })
}

export function postMonitoringTask(data: object) {
  return post({
    url: 'monitoring/task',
    data: () => {
      return data
    },
  })
}

export function putMonitoringTask(data: object) {
  return put({
    url: 'monitoring/task',
    data: () => {
      return data
    },
  })
}

export function deleteMonitoringTask(id: number | string[] | number[]) {
  return deleted({
    url: 'monitoring/task',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postMonitoringTaskStart(id: number) {
  return post({
    url: 'monitoring/task/start',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postMonitoringTaskStop(id: number) {
  return post({
    url: 'monitoring/task/stop',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getMonitoringTaskLogs(id: number, limit: number = 200) {
  return get({
    url: 'monitoring/task/logs',
    data: () => {
      return {
        id: id,
        limit: limit,
      }
    },
  })
}

