import type { AliasDraft, LogicalSource, LogicalBinding, SourceConnection } from './types'
export function createAliasDraft(record?: LogicalSource): AliasDraft {
  return {
    name: record?.name ?? '',
    sourceCategory: record?.source_category ?? 0,
    dbType: record?.db_type ?? 0,
    description: record?.description ?? '',
    status: record?.status ?? 1,
  }
}
export function aliasPayload(draft: AliasDraft, product: string | number) {
  return {
    project_product: product,
    name: draft.name.trim(),
    source_category: draft.sourceCategory,
    db_type: draft.dbType,
    description: draft.description.trim() || null,
    status: draft.status,
  }
}
export function bindingDataSource(binding: LogicalBinding): SourceConnection | null {
  return binding.data_source ?? (typeof binding.database === 'object' ? binding.database : null)
}
export function connectionName(source: SourceConnection | null) {
  if (!source) return '-'
  if (source.db_type === 2) return source.file_path || '-'
  const prefix =
    source.db_type === 20
      ? String(source.extra_config?.path_prefix || '').replace(/^\/+|\/+$/g, '')
      : ''
  return `${source.host}:${source.port}${prefix ? `/${prefix}` : ''}`
}
export function sourceLabel(source: SourceConnection | null) {
  return source?.display_name || connectionName(source)
}
export function requestError(error: unknown) {
  if (error && typeof error === 'object') {
    if ('message' in error && typeof error.message === 'string') return error.message
    if ('msg' in error && typeof error.msg === 'string') return error.msg
  }
  return '请求未确认，请重试'
}
