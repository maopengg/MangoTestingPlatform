export type Selection = number | string | Array<number | string> | null
export type ContextSource = string | (() => string)
export const contextOf = (source: ContextSource): string =>
  typeof source === 'function' ? source() : source
export interface Relation {
  id: number
  name?: string
  db_type?: number
}
export interface FeatureRecord {
  id: number
  project_product: Relation | number | null
  module: Relation | number | null
  gray_code: string
  name: string
  config_type: number
  feature_key: string
  yaml_file: Relation | number | null
  datasource_alias: Relation | number | null
  enable_sql: string | null
  disable_sql: string | null
  restore_sql: string | null
  enable_code: string | null
  disable_code: string | null
  restore_code: string | null
  default_restore: boolean
  status: number
  description: string | null
}
export interface FeatureForm {
  project_product: Selection
  module: Selection
  gray_code: string
  name: string
  config_type: number
  feature_key: string
  yaml_file: number | string | null
  datasource_alias: number | string | null
  enable_sql: string
  disable_sql: string
  restore_sql: string
  enable_code: string
  disable_code: string
  restore_code: string
  default_restore: boolean
  status: number
  description: string
}
export interface EditorHandle {
  open(record?: FeatureRecord, navigation?: { projectProduct: Selection; module: Selection }): void
}
export interface Option {
  value: number
  label: string
  db_type?: number
}
export function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}
export function idOf(value: unknown): number | null {
  const leaf = Array.isArray(value) ? value[value.length - 1] : value
  const id = leaf && typeof leaf === 'object' ? object(leaf).id : leaf
  if (
    (typeof id !== 'number' && typeof id !== 'string') ||
    (typeof id === 'string' && !/^\d+$/.test(id))
  )
    return null
  const number = Number(id)
  return Number.isSafeInteger(number) && number > 0 ? number : null
}
export function createForm(
  record?: FeatureRecord,
  navigation?: { projectProduct: Selection; module: Selection }
): FeatureForm {
  return {
    project_product: idOf(record ? record.project_product : navigation?.projectProduct),
    module: idOf(record ? record.module : navigation?.module),
    gray_code: record?.gray_code ?? '',
    name: record?.name ?? '',
    config_type: record?.config_type ?? 1,
    feature_key: record?.feature_key ?? '',
    yaml_file: idOf(record?.yaml_file),
    datasource_alias: idOf(record?.datasource_alias),
    enable_sql: record?.enable_sql ?? '',
    disable_sql: record?.disable_sql ?? '',
    restore_sql: record?.restore_sql ?? '',
    enable_code: record?.enable_code ?? '',
    disable_code: record?.disable_code ?? '',
    restore_code: record?.restore_code ?? '',
    default_restore: record?.default_restore ?? true,
    status: record?.status ?? 1,
    description: record?.description ?? '',
  }
}
export function validation(form: FeatureForm): string | null {
  if (!idOf(form.project_product)) return '请选择项目/产品'
  if (!idOf(form.module)) return '请选择模块'
  if (!form.gray_code.trim()) return '请输入灰度编号'
  if (!form.name.trim()) return '请输入灰度名称'
  if (!form.feature_key.trim()) return '请输入灰度Key'
  if (![1, 2, 3].includes(form.config_type)) return '请选择配置类型'
  if (form.config_type === 1 && !idOf(form.yaml_file)) return '请选择配置文件'
  if (form.config_type === 2 && !idOf(form.datasource_alias)) return '请选择逻辑数据源'
  if (
    form.config_type === 2 &&
    (!form.enable_sql.trim() || !form.disable_sql.trim() || !form.restore_sql.trim())
  )
    return '请填写执行SQL、关闭SQL和恢复SQL'
  if (
    form.config_type === 3 &&
    (!form.enable_code.trim() || !form.disable_code.trim() || !form.restore_code.trim())
  )
    return '请填写执行代码、关闭代码和恢复代码'
  return null
}
export function payload(form: FeatureForm, id: number | null) {
  return {
    ...(id === null ? {} : { id }),
    project_product: idOf(form.project_product),
    module: idOf(form.module),
    gray_code: form.gray_code,
    name: form.name,
    config_type: form.config_type,
    feature_key: form.feature_key,
    yaml_file: form.config_type === 1 ? idOf(form.yaml_file) : null,
    datasource_alias: form.config_type === 2 ? idOf(form.datasource_alias) : null,
    database: null,
    enable_sql: form.config_type === 2 ? form.enable_sql : null,
    disable_sql: form.config_type === 2 ? form.disable_sql : null,
    restore_sql: form.config_type === 2 ? form.restore_sql : null,
    enable_code: form.config_type === 3 ? form.enable_code : null,
    disable_code: form.config_type === 3 ? form.disable_code : null,
    restore_code: form.config_type === 3 ? form.restore_code : null,
    default_restore: form.default_restore,
    status: form.status,
    description: form.description,
  }
}
export function parseYamlOptions(value: unknown): Option[] {
  const response = object(value)
  if (response.code !== 200 || !Array.isArray(response.data))
    throw Error('Invalid configuration options')
  return response.data.map((value) => {
    const row = object(value),
      id = idOf(row.id),
      product = object(row.project_product),
      project = object(product.project)
    if (!id || typeof row.name !== 'string') throw Error('Invalid configuration option')
    const path = [project.name, product.name]
      .filter((value) => typeof value === 'string' && value)
      .join(' / ')
    return { value: id, label: `${row.name}${path ? ` / ${path}` : ''}` }
  })
}
export function parseAliases(value: unknown, productId: number): Option[] {
  const response = object(value)
  if (response.code !== 200 || !Array.isArray(response.data))
    throw Error('Invalid datasource options')
  return response.data
    .map((value) => {
      const row = object(value),
        id = idOf(row.id)
      if (
        !id ||
        typeof row.name !== 'string' ||
        typeof row.db_type !== 'number' ||
        idOf(row.project_product) !== productId
      )
        throw Error('Invalid datasource option')
      return { value: id, label: row.name, db_type: row.db_type }
    })
    .filter((row) => row.db_type !== undefined && [0, 1, 2].includes(row.db_type))
}
