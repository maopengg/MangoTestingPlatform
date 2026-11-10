import type { DataSourceRecord, SourceDraft, SourceExtraConfig } from './types'

export function sourceExtraConfig(
  type: number | null,
  value?: SourceExtraConfig | null
): SourceExtraConfig {
  if (type === 10) return { ssl: value?.ssl ?? false }
  if (type === 20)
    return {
      scheme: value?.scheme ?? 'http',
      path_prefix: value?.path_prefix ?? '',
      verify_certs: value?.verify_certs ?? true,
    }
  return {}
}

export function createSourceDraft(record?: DataSourceRecord): SourceDraft {
  return {
    source_category: record?.source_category ?? 0,
    db_type: record?.db_type ?? 0,
    display_name: record?.display_name ?? '',
    host: record?.host ?? '',
    port: record?.port ?? 3306,
    file_path: record?.file_path ?? '',
    user: record?.user ?? '',
    password: '',
    extra_config: sourceExtraConfig(record?.db_type ?? 0, record?.extra_config),
  }
}

export function sourcePayload(draft: SourceDraft) {
  return {
    source_category: draft.source_category,
    db_type: draft.db_type,
    display_name: draft.display_name,
    file_path: draft.db_type === 2 ? draft.file_path : '',
    ...(draft.db_type === 2
      ? {}
      : {
          host: draft.host,
          port: draft.port,
          user: draft.user,
          ...(draft.password ? { password: draft.password } : {}),
        }),
    extra_config: sourceExtraConfig(draft.db_type, draft.extra_config),
  }
}

export function sourceConnectionName(record: DataSourceRecord) {
  if (record.db_type === 2) return record.file_path || '-'
  const prefix =
    record.db_type === 20
      ? String(record.extra_config?.path_prefix || '').replace(/^\/+|\/+$/g, '')
      : ''
  return `${record.host}:${record.port}${prefix ? `/${prefix}` : ''}`
}

export function sourceDisplayLabel(record: DataSourceRecord) {
  const address = sourceConnectionName(record)
  return record.display_name && record.display_name !== address
    ? `${record.display_name}（${address}）`
    : address
}

export function sourceError(error: unknown, fallback: string) {
  if (error && typeof error === 'object') {
    if ('message' in error && typeof error.message === 'string') return error.message
    if ('msg' in error && typeof error.msg === 'string') return error.msg
  }
  return fallback
}
