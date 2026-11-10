export interface SuiteResourceForm {
  id: number | null
  suite: number
  context_key: number
  content_type: number
  url_type: number
  title: string
  content: string
  extracted_text: string
  enabled: boolean
  file: number | null
  file_name: string
  file_path: string
  mime_type: string
  file_size: number | null
}
export interface SuiteResource extends SuiteResourceForm {
  id: number
}
export interface ResourceEditorHandle {
  open(contextKey: number, title: string, resource?: SuiteResource, raw?: boolean): void
}
export interface UploadedResourceFile {
  file: number
  file_name: string
  file_path: string
  mime_type: string
  file_size: number
  parse_status: number
}
export function createResourceForm(suite = 0, contextKey = 0, title = ''): SuiteResourceForm {
  return {
    id: null,
    suite,
    context_key: contextKey,
    content_type: 0,
    url_type: 0,
    title,
    content: '',
    extracted_text: '',
    enabled: true,
    file: null,
    file_name: '',
    file_path: '',
    mime_type: '',
    file_size: null,
  }
}
export function resourceDraft(record: SuiteResource): SuiteResourceForm {
  return {
    id: record.id,
    suite: record.suite,
    context_key: record.context_key,
    content_type: record.content_type,
    url_type: record.url_type,
    title: record.title,
    content: record.content || '',
    extracted_text: record.extracted_text || '',
    enabled: record.enabled,
    file: record.file ?? null,
    file_name: record.file_name || '',
    file_path: record.file_path || '',
    mime_type: record.mime_type || '',
    file_size: record.file_size ?? null,
  }
}
export function resourceId(value: unknown): number | null {
  const id = typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : value
  return typeof id === 'number' && Number.isSafeInteger(id) && id > 0 ? id : null
}
export function objectValue(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}
