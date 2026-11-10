import type { DiagnosticMarkdownResult } from '@/api/system/tasks'

export type DiagnosticTargetType = DiagnosticMarkdownResult['target_type']
export type DiagnosticDocument = Omit<DiagnosticMarkdownResult, 'target_id'> & { target_id: string }
const object = (value: unknown): Record<string, unknown> | null => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
export function diagnosticTargetId(value: unknown): string | null {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? String(value) : null
  return typeof value === 'string' && /^\d+$/.test(value.trim()) ? value.trim() : null
}
// The backend's explicit missing-binding code is an empty state; missing files and other errors remain failures.
export function isMissingDiagnostic(value: unknown): boolean { return object(value)?.code === 38005 }
export function parseDiagnosticDocument(response: unknown, type: DiagnosticTargetType, id: string): DiagnosticDocument | null {
  const envelope = object(response)
  if (isMissingDiagnostic(envelope)) return null
  if (!envelope || envelope.code !== 200) throw new Error('排查结果读取失败')
  if (envelope.data === null) return null
  const row = object(envelope.data)
  if (!row || row.target_type !== type || diagnosticTargetId(row.target_id) !== id || typeof row.content !== 'string') throw new Error('排查文档与当前对象不匹配')
  return {
    target_type: type, target_id: id, content: row.content,
    file_path: typeof row.file_path === 'string' ? row.file_path : '',
    file_name: typeof row.file_name === 'string' ? row.file_name : null,
    download_url: typeof row.download_url === 'string' ? row.download_url : null,
    update_time: typeof row.update_time === 'string' ? row.update_time : '',
  }
}
