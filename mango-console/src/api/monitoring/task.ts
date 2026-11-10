import { deleted, get, post, put } from '@/api/http'
import request from '@/api/axios.config'
import type { Response } from '@/api/http'

export interface MonitoringTaskConfiguration {
  project_product: number
  name: string
  description: string | null
  test_env: number | null
  is_notice: 0 | 1
  notice_group: number | null
}
export interface MonitoringTaskCreate extends MonitoringTaskConfiguration { script_content: string }
export type MonitoringTaskUpdate = Partial<MonitoringTaskCreate> & { id: number }

export interface MonitoringTaskQuery { page: number; pageSize: number; name?: string; project_product?: number }

export function getMonitoringTask(data: MonitoringTaskQuery) {
  return get<unknown>({
    url: 'monitoring/task',
    data: () => {
      return data
    },
  })
}

export function postMonitoringTask(data: MonitoringTaskCreate): Promise<Response<unknown>> {
  return post({
    url: 'monitoring/task',
    data: () => {
      return data
    },
  })
}

export function putMonitoringTask(data: MonitoringTaskUpdate): Promise<Response<unknown>> {
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

export function postMonitoringTaskStart(id: number): Promise<Response<unknown>> {
  return post({
    url: 'monitoring/task/start',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postMonitoringTaskStop(id: number): Promise<Response<unknown>> {
  return post({
    url: 'monitoring/task/stop',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getMonitoringTaskLogs(id: number, limit = 200) {
  return get<unknown>({
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
  return get<unknown>({
    url: 'monitoring/task',
    data: () => {
      return {
        id: id,
      }
    },
  }).then((res) => {
    // 从列表中找到对应 id 的任务
    if (res.data && Array.isArray(res.data)) {
      const task = res.data.find((item: unknown) => item !== null && typeof item === 'object' && 'id' in item && item.id === id)
      return {
        ...res,
        data: task || null,
      }
    }
    return res
  })
}
