import { deleted, get, post, put } from '@/api/http'
import request from '@/api/axios.config'

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

export function downloadMonitoringTaskLog(id: number) {
  return request.get('monitoring/task/download/log', {
    params: { id },
    responseType: 'blob',
  })
}

export function getMonitoringTaskDetail(id: number) {
  return get({
    url: 'monitoring/task',
    data: () => {
      return {
        id: id,
      }
    },
  }).then((res: any) => {
    // 从列表中找到对应 id 的任务
    if (res.data && Array.isArray(res.data)) {
      const task = res.data.find((item: any) => item.id === id)
      return {
        ...res,
        data: task || null,
      }
    }
    return res
  })
}

