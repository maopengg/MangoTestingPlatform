import type { UIEdge, UiStepControl } from '@/types/components'
import type { UiStepConditionGroup, UiStepHealingPolicy } from '@/types/ui-test/case'
import type { ElementEditorDraft, ElementEventParameter } from './ui-element-editor'
import { readElementEditor } from './ui-element-editor'
import { liveObject, liveId, readLiveResult, type LiveId, type LiveResult } from './ui-live-workbench'
import { cloneLosslessJson } from '@/utils/lossless-json'

export type StepId = LiveId
export interface StepNodeConfig { id?: StepId; ai_healed?: boolean; ai_review_status?: string; ai_heal_record_id?: StepId }
export interface StepNode { id: string; position: { x: number; y: number }; type: number; label: string; config?: StepNodeConfig }
export interface StepFlow { nodes: StepNode[]; edges: UIEdge[] }
export type StepElement = Partial<ElementEditorDraft> & { create_time?: string; update_time?: string; element_text?: string }
export interface StepParameter extends ElementEventParameter { value_type?: string; input_type?: string }
export interface StepSql { sql: string | Record<string, unknown>; key_list?: string | string[] | null; datasource_alias?: StepId | null }
export interface StepDetail {
  id: StepId | null; name: string; type: number; ope_key: string; ope_value: StepParameter[]
  ele_name: StepElement | null; condition_value: { expect?: unknown; value?: unknown } | string | number | boolean | null
  custom: Array<{ key: string; value: unknown }>; sql_execute: StepSql[]; func: string
  precondition: UiStepConditionGroup; postcondition: UiStepConditionGroup; create_time: string; update_time: string
}
export interface StepRecord {
  id: StepId; name: string; page: { id: StepId; name: string; url: string } | null
  project_product: { id: StepId; ui_client_type: StepId | null } | null
  status: number; flow_data: StepFlow; goal: string; healing_enabled: boolean
  entry_criteria: UiStepConditionGroup; success_criteria: UiStepConditionGroup; healing_policy?: UiStepHealingPolicy; config_version?: number
}
export interface StepResult extends LiveResult { next_node_id?: StepId; cache_data?: unknown; slot_id?: StepId; case_step_details_id?: StepId; ass_msg?: string; picture_name?: string; ele_name?: StepElement; loc?: string }
export interface StepExecution { id: StepId; create_time: string; result_data: StepResult | null }
export interface StepField {
  key: string; label: string; value: unknown; type: string; placeholder?: string; required?: boolean
  field?: string; min?: number; max?: number; precision?: number; suffix?: string
  compactHalf?: boolean; compactNarrow?: boolean; compactWideLabel?: boolean
  validator?: (this: StepField) => boolean
}
export interface StepDatasource { label: string; value: StepId; dbType: number }
export interface StepFileOption { label: string; value: string | number; children?: StepFileOption[] }
export function readStepFiles(value: unknown): StepFileOption[] { return stepArray(value).filter(value => value !== null).map(value => { const row = liveObject(value); if (typeof row.label !== 'string' || (typeof row.value !== 'string' && typeof row.value !== 'number')) throw Error('文件选项格式不正确'); return { label: row.label, value: row.value, ...(row.children ? { children: readStepFiles(row.children) } : {}) } }) }
export interface StepCanvasPort { selectNode: (id: string) => void; beautifyLayout: () => void }
export function stepResponse(value: unknown): unknown { const row = liveObject(value); if (row.code !== 200) throw Error('请求未成功，请重试'); return row.data }
export function stepArray(value: unknown): unknown[] { if (!Array.isArray(value)) throw Error('返回列表格式不正确'); return value }
export function requiredStepId(value: unknown): StepId { const id = liveId(value); if (id === null) throw Error('缺少有效ID'); return id }
export function readStepConfig(value: unknown): StepNodeConfig { return cloneLosslessJson(liveObject(value)) as StepNodeConfig }
export function readStepFlow(value: unknown): StepFlow {
  const row = liveObject(value)
  return { nodes: stepArray(row.nodes ?? []).map(value => { const node = liveObject(value), position = liveObject(node.position)
    if (typeof node.id !== 'string' || !node.id || typeof node.type !== 'number' || !Number.isFinite(Number(position.x)) || !Number.isFinite(Number(position.y))) throw Error('画布节点格式不正确')
    return { id: node.id, type: node.type, label: String(node.label ?? ''), position: { x: Number(position.x), y: Number(position.y) }, config: readStepConfig(node.config) }
  }), edges: stepArray(row.edges ?? []).map(value => { const edge = liveObject(value), source = liveObject(edge.source), target = liveObject(edge.target)
    if (typeof edge.id !== 'string' || typeof source.node_id !== 'string' || typeof target.node_id !== 'string') throw Error('画布连线格式不正确')
    const position = (value: unknown): UIEdge['source']['position'] => value === 'left' || value === 'right' || value === 'top' ? value : 'bottom'
    return { id: edge.id, source: { node_id: source.node_id, position: position(source.position) }, target: { node_id: target.node_id, position: position(target.position) } }
  }) }
}
export const emptyStepGroup = (): UiStepConditionGroup => ({ operator: 'all', conditions: [] })
export function readStepGroup(value: unknown): UiStepConditionGroup {
  const row = liveObject(value)
  return { operator: row.operator === 'any' ? 'any' : 'all', conditions: cloneLosslessJson(stepArray(row.conditions ?? [])) as UiStepConditionGroup['conditions'] }
}
export function createNodeDraft(): StepDetail { return { id: null, name: '', type: 0, ope_key: '', ope_value: [], ele_name: null, condition_value: null, custom: [], sql_execute: [], func: '', precondition: emptyStepGroup(), postcondition: emptyStepGroup(), create_time: '', update_time: '' } }
export function readStepDetail(value: unknown): StepDetail {
  const row = liveObject(value)
  return { ...createNodeDraft(), id: liveId(row.id), name: String(row.name ?? ''), type: Number(row.type ?? 0), ope_key: String(row.ope_key ?? ''),
    ope_value: stepArray(row.ope_value ?? []).map(value => { const item = liveObject(value); return { f: String(item.f ?? ''), n: String(item.n ?? ''), p: String(item.p ?? ''), d: item.d === true, v: cloneLosslessJson(item.v), value_type: typeof item.value_type === 'string' ? item.value_type : undefined, input_type: typeof item.input_type === 'string' ? item.input_type : undefined } }),
    ele_name: row.ele_name && typeof row.ele_name === 'object' ? { ...readElementEditor(row.ele_name), create_time: String(liveObject(row.ele_name).create_time ?? ''), update_time: String(liveObject(row.ele_name).update_time ?? '') } : null,
    condition_value: cloneLosslessJson(row.condition_value ?? null) as StepDetail['condition_value'],
    custom: stepArray(row.custom ?? []).map(value => { const item = liveObject(value); return { key: String(item.key ?? ''), value: cloneLosslessJson(item.value) } }),
    sql_execute: cloneLosslessJson(stepArray(row.sql_execute ?? [])) as StepSql[], func: String(row.func ?? ''), precondition: readStepGroup(row.precondition), postcondition: readStepGroup(row.postcondition), create_time: String(row.create_time ?? ''), update_time: String(row.update_time ?? '') }
}
export function readStepRecord(value: unknown): StepRecord {
  const row = liveObject(value), page = liveObject(row.page), product = liveObject(row.project_product)
  return { id: requiredStepId(row.id), name: String(row.name ?? ''), page: liveId(page.id) === null ? null : { id: requiredStepId(page.id), name: String(page.name ?? ''), url: String(page.url ?? '') },
    project_product: liveId(product.id) === null ? null : { id: requiredStepId(product.id), ui_client_type: liveId(product.ui_client_type) }, status: Number(row.status ?? 2), flow_data: readStepFlow(row.flow_data), goal: String(row.goal ?? ''), healing_enabled: row.healing_enabled === true,
    entry_criteria: readStepGroup(row.entry_criteria), success_criteria: readStepGroup(row.success_criteria), healing_policy: row.healing_policy ? cloneLosslessJson(row.healing_policy) as UiStepHealingPolicy : undefined, config_version: typeof row.config_version === 'number' ? row.config_version : undefined }
}
// 运行证据是可扩展只读JSON；写入必须由具体的保存白名单构建。
export function readStepResult(value: unknown): StepResult { return readLiveResult(value) as StepResult }
export const defaultStepControl = (): UiStepControl => ({ close_after_execution: false, before_wait_seconds: 1, after_wait_seconds: 1, close_live_after_execution: false })
