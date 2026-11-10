import { getOptionId } from '@/utils/business-format'
import type {
  LogicalSource,
  AliasDraft,
  LogicalBinding,
  BindingDraft,
  SourceConnection,
} from './types'
export function productId(value: unknown): string | number | null {
  const id: unknown = getOptionId(value)
  return typeof id === 'number' || (typeof id === 'string' && id !== '') ? id : null
}
export function createAliasDraft(
  record?: LogicalSource,
  product: string | number | null = null
): AliasDraft {
  return {
    project_product: record ? productId(record.project_product) : product,
    name: record?.name ?? '',
    source_category: record?.source_category ?? 0,
    db_type: record?.db_type ?? 0,
    description: record?.description ?? '',
    status: record?.status ?? 1,
  }
}
export function aliasPayload(draft: AliasDraft) {
  return {
    project_product: productId(draft.project_product),
    name: draft.name,
    source_category: draft.source_category,
    db_type: draft.db_type,
    description: draft.description,
    status: draft.status,
  }
}
export function bindingSourceId(record?: LogicalBinding): number | null {
  if (!record) return null
  const source = record.data_source ?? record.database
  return typeof source === 'number' ? source : source?.id ?? null
}
export function createBindingDraft(record?: LogicalBinding): BindingDraft {
  return {
    environment: record?.environment ?? null,
    data_source: bindingSourceId(record),
    target: {
      database_name: record?.database_name ?? '',
      schema_name: record?.schema_name ?? '',
      redis_db: record?.redis_db ?? null,
    },
    allowQuery: record?.db_c_status === 1,
    allowWrite: record?.db_rud_status === 1,
    description: record?.description ?? '',
  }
}
export const isProduction = (environment: unknown) =>
  environment !== null && environment !== '' && Number(environment) === 2
export function bindingPayload(draft: BindingDraft, aliasId: number) {
  return {
    datasource_alias: aliasId,
    environment: draft.environment,
    data_source: draft.data_source,
    database_name: draft.target.database_name,
    schema_name: draft.target.schema_name,
    redis_db: draft.target.redis_db,
    description: draft.description,
    db_c_status: draft.allowQuery ? 1 : 0,
    db_rud_status: isProduction(draft.environment) ? 0 : draft.allowWrite ? 1 : 0,
  }
}
export function displayDataSource(
  source: SourceConnection | number | null | undefined
): string | number {
  if (source == null) return '-'
  if (typeof source === 'number') return source
  const prefix =
    source.db_type === 20
      ? String(source.extra_config?.path_prefix ?? '').replace(/^\/+|\/+$/g, '')
      : ''
  const technical =
    source.file_path ||
    (source.host ? `${source.host}:${source.port}${prefix ? `/${prefix}` : ''}` : '-')
  return source.display_name && source.display_name !== technical
    ? `${source.display_name} · ${technical}`
    : technical
}
