import { get } from '@/api/http'
import request from '@/api/axios.config'
import { ApiBusinessError } from '@/api/errors'

const configBase = '/system/cache/data/report-delivery'
export type ReportSource = 'suite' | 'group'
export interface OfflineReportOption {
  id: number | string
  name: string
  test_env: number
  status: number
  started_at: string
}
export interface OfflineReportLinks {
  filename: string
  preview_url: string
  download_url: string
  expires_at: string
}
export async function generateOfflineReport(source_kind: ReportSource, source_id: string | number, signal?: AbortSignal) {
  const response = await request.post('/system/test/suite/offline/links', { source_kind, source_id }, { signal })
  if (response.data.code !== 200) throw new ApiBusinessError(response.data.msg || '生成报告失败，请重试。', response.data.code)
  const result = response.data.data as OfflineReportLinks
  try {
    for (const link of [result.preview_url, result.download_url]) {
      const url = new URL(link)
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error()
    }
    if (!Number.isFinite(Date.parse(result.expires_at))) throw new Error()
  } catch {
    throw new Error('报告访问地址或有效期无效，请检查对象存储配置。')
  }
  return result
}
export async function getOfflineReportOptions(source_kind: ReportSource, source_id: string | number, page: number, signal?: AbortSignal) {
  const response = await request.get('/system/test/suite/offline/options', {
    params: { source_kind, source_id, page, page_size: 20 }, signal,
  })
  if (response.data.code !== 200) throw new Error(response.data.msg || '读取执行报告失败，请重试。')
  return response.data.data as { items: OfflineReportOption[]; count: number }
}
export const getReportDeliveryMetadata = () => get({ url: `${configBase}/metadata` })

async function saveHtml(response: { data: Blob; status: number }, filename: string) {
  if (response.status !== 200 || !response.data.type.includes('text/html')) {
    let message = '下载报告失败'
    try { message = JSON.parse(await response.data.text()).msg || message } catch { /* 非 JSON 错误响应 */ }
    throw new Error(message)
  }
  const url = URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
export const downloadOfflineReport = async (source_kind: ReportSource, source_id: string | number, signal?: AbortSignal) => saveHtml(
  await request.post('/system/test/suite/offline', { source_kind, source_id }, { responseType: 'blob', signal }),
  `report-${source_kind}-${source_id}.html`
)
export const downloadSampleReport = async () => saveHtml(
  await request.post(`${configBase}/sample`, {}, { responseType: 'blob' }), 'sample-report.html'
)
