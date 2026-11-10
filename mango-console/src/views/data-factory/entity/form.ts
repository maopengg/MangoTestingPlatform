import { getOptionId } from '@/utils/business-format'
import type {
  EntityRecord,
  EntityDraft,
  NavigationDefaults,
  TableInfo,
  TableOption,
  FieldRecord,
  BatchDraft,
} from './types'
export function optionId(value: unknown): string | number | null {
  const id: unknown = getOptionId(value)
  return typeof id === 'number' || (typeof id === 'string' && id !== '') ? id : null
}
export const createEntityDraft = (
  record?: EntityRecord,
  defaults?: NavigationDefaults
): EntityDraft => ({
  project_product: record ? optionId(record.project_product) : defaults?.projectProduct ?? null,
  module: record ? optionId(record.module) : defaults?.module ?? null,
  datasource_alias: optionId(record?.datasource_alias),
  name: record?.name ?? '',
  description: record?.description ?? '',
  table_name: record?.table_name ?? '',
  schema_name: record?.schema_name ?? '',
  primary_key: record?.primary_key ?? 'id',
  unique_key: record?.unique_key ?? '',
  create_type: 2,
  delete_type: 2,
  cleanup_order: record?.cleanup_order ?? 100,
  status: record?.status ?? 1,
})
export function entityPayload(draft: EntityDraft) {
  return {
    project_product: optionId(draft.project_product),
    module: optionId(draft.module),
    datasource_alias: optionId(draft.datasource_alias),
    name: draft.name,
    description: draft.description,
    table_name: draft.table_name,
    schema_name: draft.schema_name,
    primary_key: draft.primary_key,
    unique_key: draft.unique_key,
    cleanup_order: draft.cleanup_order,
    status: draft.status,
    create_type: 2,
    delete_type: 2,
  }
}
export function validateEntity(draft: EntityDraft): string {
  if (optionId(draft.project_product) === null) return '请选择产品'
  if (optionId(draft.module) === null) return '请选择模块名称'
  if (optionId(draft.datasource_alias) === null) return '请选择逻辑数据库'
  if (!draft.table_name) return '请选择表名'
  if (!draft.name) return '请填写实体名称'
  return ''
}
export const normalizeTable = (table: string | TableInfo): TableOption => {
  const value = typeof table === 'string' ? table : table.name || table.table || ''
  const comment = typeof table === 'string' ? '' : table.comment || table.table_comment || ''
  return {
    value,
    comment,
    label: comment ? `${value} / ${comment}` : value,
    schema_name: typeof table === 'string' ? '' : table.schema_name || '',
  }
}
export const createBatchDraft = (defaults?: NavigationDefaults): BatchDraft => ({
  project_product: defaults?.projectProduct ?? null,
  module: defaults?.module ?? null,
  datasource_alias: null,
  sync_fields: true,
  skip_exists: true,
})
export const tableKey = (schema: string, name: string) => JSON.stringify([schema, name])
export function fieldMetadata(field: FieldRecord) {
  return {
    name: field.name,
    label: field.label,
    db_type: field.db_type,
    platform_type: field.platform_type,
    nullable: field.nullable,
    primary_key: field.primary_key,
    autoincrement: field.autoincrement,
    max_length: field.max_length,
    enum_values: field.enum_values ? [...field.enum_values] : [],
    sort: field.sort,
  }
}
