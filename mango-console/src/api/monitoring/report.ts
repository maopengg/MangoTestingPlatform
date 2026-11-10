import { get, post } from '@/api/http'

export interface MonitoringReport {
  id: number
  create_time: string
  update_time: string
  task: number | null
  task_name: string
  task_notice_group?: {
    id: number
    name: string
  } | null
  status: number
  status_display: string
  msg: string | null
  send_text?: string | null
  is_notice: number
}

export interface MonitoringReportQuery {
  page: number
  pageSize: number
  task__name__contains?: string
  status__in?: string
}

export interface CreateReportParams {
  task_id: number
  status: number // 0: 信息，1: 失败，2: 警告，3: 调试
  msg: string
  detail?: string
}

/**
 * 获取预警监控报告列表
 */
export function getMonitoringReportList(data: MonitoringReportQuery) {
  return get<unknown>({
    url: 'monitoring/report',
    data: () => {
      return { ...data }
    },
  })
}

/**
 * 创建预警监控报告（供监控脚本调用）
 */
export function createMonitoringReport(data: CreateReportParams) {
  return post({
    url: 'monitoring/report/create',
    data: () => {
      return data
    },
  })
}

/**
 * 获取预警监控报告详情
 */
export function getMonitoringReportDetail(id: number) {
  return get<MonitoringReport[] | MonitoringReport | null>({
    url: 'monitoring/report',
    data: () => {
      return {
        id: id,
      }
    },
  }).then((res) => {
    // 从列表中找到对应 id 的报告
    if (res.data && Array.isArray(res.data)) {
      const report = res.data.find((item) => item.id === id)
      return {
        ...res,
        data: report || null,
      }
    }
    return res
  })
}
