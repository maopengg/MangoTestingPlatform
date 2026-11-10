import { get } from '@/api/http'
import request from '@/api/axios.config'
import { ApiBusinessError } from '@/api/errors'

const configBase = '/system/cache/data/report-delivery'
export type ReportSource = 'suite' | 'group'
export interface OfflineReportOption {
  id: number | string
  name: string
  test_env: number | null
  status: number | null
  started_at: string
}
export interface OfflineReportLinks {
  filename: string
  preview_url: string
  download_url: string
  expires_at: string
}
function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
function text(value: unknown) { return typeof value === 'string' ? value : '' }
export function offlineReportId(value: unknown): number | string | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? value : null
  return typeof value === 'string' && /^\d+$/.test(value) ? value : null
}
function integer(value: unknown) {
  const id = offlineReportId(value)
  return id !== null && Number.isSafeInteger(Number(id)) ? Number(id) : null
}
export function parseOfflineReportLinks(value: unknown): OfflineReportLinks {
  const row = object(value)
  const result = { filename: text(row.filename), preview_url: text(row.preview_url), download_url: text(row.download_url), expires_at: text(row.expires_at) }
  try {
    for (const link of [result.preview_url, result.download_url]) {
      const url = new URL(link)
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error()
    }
    if (!Number.isFinite(Date.parse(result.expires_at))) throw new Error()
  } catch { throw new Error('报告访问地址或有效期无效，请检查对象存储配置。') }
  return result
}
export function parseOfflineReportOptions(value: unknown): { items: OfflineReportOption[]; count: number } {
  const row = object(value), count = integer(row.count)
  if (!Array.isArray(row.items) || count === null) throw new Error('执行报告列表格式无效，请重试。')
  const items = new Map<string, OfflineReportOption>()
  for (const entry of row.items) {
    const option = object(entry), id = offlineReportId(option.id)
    if (id !== null) items.set(String(id), { id, name: text(option.name), test_env: integer(option.test_env), status: integer(option.status), started_at: text(option.started_at) })
  }
  return { items: [...items.values()], count }
}
export async function generateOfflineReport(source_kind: ReportSource, source_id: string | number, signal?: AbortSignal) {
  const response = await request.post('/system/test/suite/offline/links', { source_kind, source_id }, { signal })
  const payload = object(response.data)
  if (payload.code !== 200) throw new ApiBusinessError(text(payload.msg) || '生成报告失败，请重试。', typeof payload.code === 'number' ? payload.code : undefined)
  return parseOfflineReportLinks(payload.data)
}
export async function getOfflineReportOptions(source_kind: ReportSource, source_id: string | number, page: number, signal?: AbortSignal) {
  const response = await request.get('/system/test/suite/offline/options', {
    params: { source_kind, source_id, page, page_size: 20 }, signal,
  })
  const payload = object(response.data)
  if (payload.code !== 200) throw new Error(text(payload.msg) || '读取执行报告失败，请重试。')
  return parseOfflineReportOptions(payload.data)
}
export const getReportDeliveryMetadata = () => get({ url: `${configBase}/metadata` })

async function saveHtml(response: { data: Blob; status: number }, filename: string, signal?: AbortSignal) {
  if (signal?.aborted) return
  if (!(response.data instanceof Blob)) throw new Error('下载报告失败')
  if (response.status !== 200 || !response.data.type.includes('text/html')) {
    let message = '下载报告失败'
    try { message = text(object(JSON.parse(await response.data.text())).msg) || message } catch { /* 非 JSON 错误响应 */ }
    throw new Error(message)
  }
  if (signal?.aborted) return
  const url = URL.createObjectURL(response.data)
  try {
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
  } finally { setTimeout(() => URL.revokeObjectURL(url), 1000) }
}
export const downloadOfflineReport = async (source_kind: ReportSource, source_id: string | number, signal?: AbortSignal) => saveHtml(
  await request.post('/system/test/suite/offline', { source_kind, source_id }, { responseType: 'blob', signal }),
  `report-${source_kind}-${source_id}.html`, signal
)
export const downloadSampleReport = async (signal?: AbortSignal) => saveHtml(
  await request.post(`${configBase}/sample`, {}, { responseType: 'blob', signal }), 'sample-report.html', signal
)
