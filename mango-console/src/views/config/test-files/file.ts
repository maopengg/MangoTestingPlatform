import { getOptionId } from '@/utils/business-format'
import type { TestFileDraft, TestFileRecord } from './types'

export function productId(value: unknown): string | number | null {
  const id: unknown = getOptionId(value)
  return typeof id === 'number' || (typeof id === 'string' && id !== '') ? id : null
}
export function createFileDraft(record?: TestFileRecord): TestFileDraft {
  return { project_product: productId(record?.project_product), allow_download: true }
}
export function createUploadPayload(file: File, draft: TestFileDraft): FormData {
  const payload = new FormData()
  payload.append('test_file', file)
  payload.append('type', '0')
  payload.append('name', file.name)
  payload.append('project_product', String(productId(draft.project_product)))
  payload.append('allow_download', String(draft.allow_download))
  return payload
}
export function isAllowDownload(record: TestFileRecord): boolean {
  const value = record.allow_download
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value === 1
  return typeof value === 'string' && ['true', '1', 'yes', 'on'].includes(value.toLowerCase())
}
export function formatFileSize(size: number | string | null | undefined): string {
  let value = Number(size || 0)
  if (!Number.isFinite(value) || value <= 0) return '-'
  for (const unit of ['B', 'KB', 'MB', 'GB', 'TB']) {
    if (value < 1024 || unit === 'TB')
      return unit === 'B' ? `${Math.round(value)} ${unit}` : `${value.toFixed(1)} ${unit}`
    value /= 1024
  }
  return '-'
}
