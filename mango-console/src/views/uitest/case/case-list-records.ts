import { normalizeEmptyListTotal } from '@/utils/api-response'
import { cloneLosslessJson } from '@/utils/lossless-json'
import { uiCaseAssetId, requiredUiCaseAssetId, uiCaseAssetObject, uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'

export type CaseId = UiCaseAssetId
export type PublicationStatus = 'unpublished' | 'prepublished' | 'published'
export interface CaseRelation { id: CaseId; name: string }
export interface CaseSuite { name: string; parametrize: Array<{ key: string; value: unknown; test_envs: CaseId[] }> }
export interface UiCaseRow {
  id: CaseId; name: string; project_product: (CaseRelation & { project: CaseRelation | null }) | null
  module: (CaseRelation & { full_path: string }) | null; case_people: CaseRelation | null
  level: number | null; scenario_layer: number; scenario_type: number; scenario_tags: string[]; scenario_description: string
  status: number; publication_status: PublicationStatus; case_flow: string; parametrize: CaseSuite[]
  update_user: (CaseRelation & { username: string }) | null; update_time: string
}
export interface UiCaseMetadataDraft {
  project_product: CaseId | CaseId[] | null; module: CaseId | null; name: string; level: number | null
  scenario_layer: number; scenario_type: number; scenario_tags: string[]; scenario_description: string; case_people: CaseId | null
}
export interface CaseUserOption { key: CaseId; title: string }
export interface CaseListQuery {
  page: number; pageSize: number; id?: string | number; name?: string; project_product?: CaseId; module?: CaseId; module__in?: string
  level__in?: string; scenario_layer__in?: string; scenario_type__in?: string; scenario_tags?: string[]
  case_people__in?: string; status__in?: string; update_user__in?: string; publication_status?: PublicationStatus
}
const object = uiCaseAssetObject
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid case text'); return value }
function integer(value: unknown, fallback = 0): number { if (value == null) return fallback; if (typeof value !== 'number' || !Number.isSafeInteger(value)) throw Error('Invalid case number'); return value }
function array(value: unknown): unknown[] { if (value == null) return []; if (!Array.isArray(value)) throw Error('Invalid case array'); return value }
function relation(value: unknown): CaseRelation | null {
  if (value == null || value === '') return null
  if (typeof value !== 'object') return { id: requiredUiCaseAssetId(value), name: '' }
  const row = object(value); return { id: requiredUiCaseAssetId(row.id), name: text(row.name ?? row.username) }
}
export function caseOptionId(value: unknown): CaseId | null {
  if (Array.isArray(value)) return caseOptionId(value[value.length - 1])
  return value && typeof value === 'object' ? uiCaseAssetId(object(value).id) : uiCaseAssetId(value)
}
export function readCaseSuites(value: unknown): CaseSuite[] {
  return array(value).map(value => {
    const row = object(value)
    return { name: text(row.name), parametrize: array(row.parametrize).map(value => { const item = object(value); return { key: text(item.key), value: cloneLosslessJson(item.value === undefined ? '' : item.value), test_envs: array(item.test_envs).map(requiredUiCaseAssetId) } }) }
  })
}
export function readUiCaseRow(value: unknown): UiCaseRow {
  const row = object(value), product = relation(row.project_product), module = relation(row.module), user = relation(row.update_user)
  const productData = row.project_product && typeof row.project_product === 'object' ? object(row.project_product) : {}
  const moduleData = row.module && typeof row.module === 'object' ? object(row.module) : {}
  const userData = row.update_user && typeof row.update_user === 'object' ? object(row.update_user) : {}
  const publication = row.publication_status ?? 'unpublished'
  if (typeof publication !== 'string' || !['unpublished', 'prepublished', 'published'].includes(publication)) throw Error('Invalid case publication state')
  return {
    id: requiredUiCaseAssetId(row.id), name: text(row.name), project_product: product ? { ...product, project: relation(productData.project) } : null,
    module: module ? { ...module, full_path: text(moduleData.full_path) } : null, case_people: relation(row.case_people), level: row.level == null ? null : integer(row.level),
    scenario_layer: integer(row.scenario_layer), scenario_type: integer(row.scenario_type), scenario_tags: array(row.scenario_tags).map(text), scenario_description: text(row.scenario_description),
    status: integer(row.status, 2), publication_status: publication as PublicationStatus, case_flow: text(row.case_flow), parametrize: readCaseSuites(row.parametrize),
    update_user: user ? { ...user, username: text(userData.username) } : null, update_time: text(row.update_time),
  }
}
export function readUiCaseList(value: unknown) {
  value = normalizeEmptyListTotal(value)

  const rows = array(uiCaseAssetResponse(value)).map(readUiCaseRow), total = integer(object(value).totalSize, -1)
  if (total < 0 || new Set(rows.map(row => String(row.id))).size !== rows.length) throw Error('Invalid case list')
  return { rows, total }
}
export function readCaseUsers(value: unknown): CaseUserOption[] {
  return array(uiCaseAssetResponse(value)).map(value => { const row = object(value); return { key: requiredUiCaseAssetId(row.key), title: text(row.title) } })
}
export function createMetadataDraft(row: UiCaseRow | null = null, defaults: { projectProduct?: CaseId | null; module?: CaseId | null } = {}): UiCaseMetadataDraft {
  return { project_product: row?.project_product?.id ?? defaults.projectProduct ?? null, module: row?.module?.id ?? defaults.module ?? null, name: row?.name ?? '', level: row?.level ?? null,
    scenario_layer: row?.scenario_layer ?? 0, scenario_type: row?.scenario_type ?? 0, scenario_tags: [...(row?.scenario_tags ?? [])], scenario_description: row?.scenario_description ?? '', case_people: row?.case_people?.id ?? null }
}
export function caseMetadataPayload(draft: UiCaseMetadataDraft, id: CaseId | null) {
  if (!draft.name.trim() || draft.level === null) throw Error('Missing case metadata')
  const fields = { project_product: requiredUiCaseAssetId(caseOptionId(draft.project_product)), module: requiredUiCaseAssetId(caseOptionId(draft.module)), name: draft.name,
    level: integer(draft.level), scenario_layer: integer(draft.scenario_layer), scenario_type: integer(draft.scenario_type), scenario_tags: draft.scenario_tags.map(text), scenario_description: draft.scenario_description, case_people: requiredUiCaseAssetId(draft.case_people) }
  return id === null ? { ...fields, front_custom: [], front_sql: [], posterior_sql: [], front_public: [], front_auth_config: [] } : { ...fields, id }
}
export function caseListQuery(values: Record<string, unknown>, status: string, moduleIds: CaseId[], page: number, pageSize: number): CaseListQuery {
  const query: CaseListQuery = { page, pageSize }
  for (const key of ['id', 'name', 'level__in', 'scenario_layer__in', 'scenario_type__in', 'case_people__in', 'status__in', 'update_user__in'] as const) {
    const value = values[key]
    if (value == null || value === '') continue
    if (typeof value !== 'string' && typeof value !== 'number') throw Error('Invalid case filter')
    if (key === 'id') query.id = value; else query[key] = String(value)
  }
  const product = caseOptionId(values.project_product), module = caseOptionId(values.module)
  if (product !== null) query.project_product = product
  if (moduleIds.length) query.module__in = moduleIds.map(requiredUiCaseAssetId).join(','); else if (module !== null) query.module = module
  const tags = array(values.scenario_tags).map(text); if (tags.length) query.scenario_tags = [...tags]
  if (status !== 'all') { if (!['published', 'prepublished', 'unpublished'].includes(status)) throw Error('Invalid publication filter'); query.publication_status = status as PublicationStatus }
  return query
}
