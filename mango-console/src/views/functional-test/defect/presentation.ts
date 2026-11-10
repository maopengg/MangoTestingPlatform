import { createDefectForm, defectFields, defectId, defectMetadata } from './form'
import type { DefectFilters, DefectListRecord, DefectStats, DefectUserOption } from './types'

const text = (value: unknown) => (typeof value === 'string' ? value : '')
export function defectListRecord(value: unknown): DefectListRecord {
  const raw = defectFields(value),
    id = defectId(raw.id)
  if (
    id === null ||
    typeof raw.title !== 'string' ||
    typeof raw.defect_no !== 'string' ||
    typeof raw.status !== 'number'
  )
    throw Error('缺陷记录格式错误')
  const {
    id: _id,
    project_product: _product,
    module: _module,
    assignee: _assignee,
    source_plan_id: _plan,
    case_ids: _cases,
    plan_case_ids: _planCases,
    ...form
  } = createDefectForm(raw)
  const user = (value: unknown) => {
    const row = defectFields(value),
      id = defectId(row.id)
    return id === null ? null : { id, name: text(row.name) || text(row.username) }
  }
  const product = defectFields(raw.project_product),
    productId = defectId(product.id),
    project = defectFields(product.project)
  const module = defectFields(raw.module),
    moduleId = defectId(module.id)
  const metadata = defectMetadata(raw)
  return {
    ...form,
    ...metadata,
    id,
    status: raw.status,
    defect_no: raw.defect_no,
    project_product:
      productId === null
        ? null
        : {
            id: productId,
            name: text(product.name),
            project: product.project
              ? { id: defectId(project.id), name: text(project.name) }
              : null,
          },
    module:
      moduleId === null
        ? null
        : { id: moduleId, name: text(module.name), full_path: text(module.full_path) },
    assignee: user(raw.assignee),
    reporter: user(raw.reporter),
    relation_count: defectId(raw.relation_count) ?? metadata.relations.length,
  }
}
export function emptyDefectFilters(): DefectFilters {
  return {
    project_product: null,
    module: null,
    keyword: '',
    status: null,
    severity: null,
    priority: null,
    defect_type: null,
    source_type: null,
    assignee: null,
    reporter: null,
    source_plan: null,
    create_range: [],
    update_range: [],
  }
}
export function snapshotDefectFilters(value: DefectFilters): DefectFilters {
  return {
    ...value,
    project_product: defectId(value.project_product),
    module: defectId(value.module),
    create_range: value.create_range ? [...value.create_range] : [],
    update_range: value.update_range ? [...value.update_range] : [],
  }
}
export function defectQuery(filters: DefectFilters): Record<string, unknown> {
  const query: Record<string, unknown> = {}
  for (const key of [
    'project_product',
    'module',
    'keyword',
    'status',
    'severity',
    'priority',
    'defect_type',
    'source_type',
    'assignee',
    'reporter',
    'source_plan',
  ] as const) {
    const value =
      key === 'project_product' || key === 'module' ? defectId(filters[key]) : filters[key]
    if (value !== null && value !== undefined && value !== '') query[key] = value
  }
  for (const [field, prefix] of [
    ['create_range', 'create_time'],
    ['update_range', 'update_time'],
  ] as const) {
    const range = filters[field]
    if (range?.length === 2) {
      query[`${prefix}_start`] = range[0]
      query[`${prefix}_end`] = range[1]
    }
  }
  return query
}
export function emptyDefectStats(): DefectStats {
  return { open_count: 0, my_pending_count: 0, serious_count: 0, resolved_pending_count: 0 }
}
export function parseDefectStats(value: unknown): DefectStats {
  const row = defectFields(value)
  const count = (key: keyof DefectStats) => {
    const value = defectId(row[key])
    if (value === null) throw Error('缺陷统计格式错误')
    return value
  }
  return {
    open_count: count('open_count'),
    my_pending_count: count('my_pending_count'),
    serious_count: count('serious_count'),
    resolved_pending_count: count('resolved_pending_count'),
  }
}
export function defectUserOptions(value: unknown): DefectUserOption[] {
  if (!Array.isArray(value)) throw Error('用户选项格式错误')
  return value.map((item) => {
    const row = defectFields(item),
      key = defectId(row.key)
    if (key === null || typeof row.title !== 'string') throw Error('用户选项格式错误')
    return { key, title: row.title }
  })
}
