import { normalizeEmptyListTotal } from '@/utils/api-response'
import { idOf, object, type FeatureRecord, type Relation, type Selection } from './editor-form'

export interface FeatureQuery {
  project_product: Selection
  module: Selection
  config_type: number[]
  status: number[]
  yaml_file: number[]
  gray_code: string
  name: string
  feature_key: string
}
interface DisplayRelation extends Relation {
  full_path?: string
  file_path?: string
  project?: { id: number; name: string }
}
export interface FeatureRow extends FeatureRecord {
  project_product: DisplayRelation | null
  module: DisplayRelation | null
  yaml_file: DisplayRelation | null
  datasource_alias: DisplayRelation | null
  database: DisplayRelation | null
  path_config: unknown[]
}
export const createQuery = (): FeatureQuery => ({
  project_product: null,
  module: null,
  config_type: [],
  status: [],
  yaml_file: [],
  gray_code: '',
  name: '',
  feature_key: '',
})
export function requestParams(query: FeatureQuery, page: number, pageSize: number) {
  return Object.fromEntries(
    Object.entries({
      page,
      pageSize,
      project_product: idOf(query.project_product),
      module: idOf(query.module),
      config_type__in: query.config_type.join(','),
      status__in: query.status.join(','),
      yaml_file__in: query.yaml_file.join(','),
      gray_code: query.gray_code,
      name: query.name,
      feature_key: query.feature_key,
    }).filter(([, value]) => value !== '' && value != null)
  )
}
function relation(value: unknown): DisplayRelation | null {
  if (value == null) return null
  const row = object(value),
    id = idOf(value)
  if (!id) throw Error('Invalid feature relation')
  const project = object(row.project),
    projectId = idOf(project.id)
  return {
    id,
    ...(typeof row.name === 'string' ? { name: row.name } : {}),
    ...(typeof row.full_path === 'string' ? { full_path: row.full_path } : {}),
    ...(typeof row.file_path === 'string' ? { file_path: row.file_path } : {}),
    ...(typeof row.db_type === 'number' ? { db_type: row.db_type } : {}),
    ...(projectId && typeof project.name === 'string'
      ? { project: { id: projectId, name: project.name } }
      : {}),
  }
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw Error('Invalid feature text')
  return value
}
function nullableText(value: unknown): string | null {
  return value == null ? null : text(value)
}
export function featurePage(value: unknown): { rows: FeatureRow[]; total: number } {
  value = normalizeEmptyListTotal(value)

  const response = object(value),
    list = response.data
  const total =
    response.totalSize === undefined && Array.isArray(list) && !list.length ? 0 : response.totalSize
  if (
    response.code !== 200 ||
    !Array.isArray(list) ||
    typeof total !== 'number' ||
    !Number.isSafeInteger(total) ||
    total < list.length
  )
    throw Error('Invalid feature page')
  const seen = new Set<number>()
  const rows = list.map((value): FeatureRow => {
    const row = object(value),
      id = idOf(row.id)
    if (
      !id ||
      seen.has(id) ||
      ![1, 2, 3].includes(Number(row.config_type)) ||
      typeof row.config_type !== 'number' ||
      ![0, 1].includes(Number(row.status)) ||
      typeof row.status !== 'number' ||
      typeof row.default_restore !== 'boolean' ||
      !Array.isArray(row.path_config)
    )
      throw Error('Invalid feature record')
    seen.add(id)
    return {
      id,
      name: text(row.name),
      gray_code: text(row.gray_code),
      feature_key: text(row.feature_key),
      config_type: row.config_type,
      status: row.status,
      default_restore: row.default_restore,
      project_product: relation(row.project_product),
      module: relation(row.module),
      yaml_file: relation(row.yaml_file),
      datasource_alias: relation(row.datasource_alias),
      database: relation(row.database),
      enable_sql: nullableText(row.enable_sql),
      disable_sql: nullableText(row.disable_sql),
      restore_sql: nullableText(row.restore_sql),
      enable_code: nullableText(row.enable_code),
      disable_code: nullableText(row.disable_code),
      restore_code: nullableText(row.restore_code),
      description: nullableText(row.description),
      path_config: JSON.parse(JSON.stringify(row.path_config)) as unknown[],
    }
  })
  return { rows, total }
}
