import { reportObject, reportPayload } from './report-overview'

export interface ReportExportTask {
  id: string
  status: 'pending' | 'running' | 'success' | 'fail'
  fileName: string
}

export function parseReportExportTask(response: unknown, expectedId?: string): ReportExportTask {
  const row = reportObject(reportPayload(response))
  if (!row || typeof row.task_id !== 'string' || !row.task_id.trim()) throw new Error('导出任务格式不正确')
  if (expectedId !== undefined && row.task_id !== expectedId) throw new Error('导出任务不匹配')
  if (typeof row.status !== 'string' || !['pending', 'running', 'success', 'fail'].includes(row.status)) throw new Error('导出任务状态不正确')
  return {
    id: row.task_id,
    status: row.status as ReportExportTask['status'],
    fileName: typeof row.file_name === 'string' ? row.file_name : '',
  }
}

export function reportExportBlob(response: unknown): Blob {
  const envelope = reportObject(response), blob = envelope?.data
  if (!(blob instanceof Blob) || !blob.size || /json|html|text\//i.test(blob.type)) throw new Error('报告下载内容不正确')
  if (typeof envelope?.status === 'number' && envelope.status !== 200) throw new Error('报告下载失败')
  return blob
}

export function saveReportExport(blob: Blob, fileName: string) {
  const link = document.createElement('a'), url = URL.createObjectURL(blob)
  try {
    link.href = url
    link.download = fileName
    document.body.appendChild(link)
    link.click()
  } finally {
    try { link.remove() } finally { URL.revokeObjectURL(url) }
  }
}
