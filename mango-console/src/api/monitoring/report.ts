import { get, post } from '@/api/http'

export interface MonitoringReport {
  id: number
  create_time: string
  update_time: string
  task: number
  task_name: string
  task_notice_group?: {
    id: number
    name: string
  }
  status: number
  status_display: string
  msg: string
  send_text?: string
  is_notice: number
}

export interface CreateReportParams {
  task_id: number
  status: number // 0: 成功, 1: 失败, 2: 信息
  msg: string
  detail?: string
}

/**
 * 获取预警监控报告列表
 */
export function getMonitoringReportList(data: object) {
  return get({
    url: 'monitoring/report',
    data: () => {
      return data
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
  return get({
    url: 'monitoring/report',
    data: () => {
      return {
        id: id,
      }
    },
  }).then((res: any) => {
    // 从列表中找到对应 id 的报告
    if (res.data && Array.isArray(res.data)) {
      const report = res.data.find((item: any) => item.id === id)
      return {
        ...res,
        data: report || null,
      }
    }
    return res
  })
}

