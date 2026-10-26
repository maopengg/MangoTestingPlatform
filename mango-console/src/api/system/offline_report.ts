import { get } from '@/api/http'
import request from '@/api/axios.config'

const configBase = '/system/cache/data/report-delivery'
export type ReportSource = 'suite' | 'group'
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
