import { requiredUiCaseAssetId, uiCaseAssetId, uiCaseAssetObject, uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'
import type { CaseStepRow } from './step-list'

type Evidence = Readonly<Record<string, unknown>>
export interface CaseRuntimeNode {
  id: UiCaseAssetId; status: number; nextId: UiCaseAssetId | null; pending: boolean; evidence: Evidence
}
export interface CaseRuntimeStep {
  id: UiCaseAssetId | null; detailId: UiCaseAssetId | null; executionId: string; testEnv: UiCaseAssetId | null
  sequence: number; status: number; error: string | null; final: boolean
  cache: unknown; factoryCache: unknown; nodes: CaseRuntimeNode[]; evidence: Evidence
}
export interface CaseRuntimeResult {
  id: UiCaseAssetId; executionId: string; testEnv: UiCaseAssetId | null; status: number; final: boolean
  cache: unknown; factoryCache: unknown; steps: CaseRuntimeStep[]; evidence: Evidence
}
export interface CaseNodeProgress {
  id: UiCaseAssetId; detailId: UiCaseAssetId; executionId: string; count: number; node: CaseRuntimeNode
}
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid runtime text'); return value }
function integer(value: unknown): number {
  const number = typeof value === 'number' ? value : typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : NaN
  if (!Number.isSafeInteger(number) || number < 0) throw Error('Invalid runtime number')
  return number
}
function list(value: unknown): unknown[] { if (value == null) return []; if (!Array.isArray(value)) throw Error('Invalid runtime list'); return value }
function flag(value: unknown): boolean { if (value == null) return false; if (typeof value !== 'boolean') throw Error('Invalid runtime flag'); return value }
// 仅供报告/流程图读取的异构证据；状态判断使用上面的有限字段，不以证据对象充当页面状态或保存入参。
function evidence(value: Record<string, unknown>): Evidence { return Object.freeze({ ...value }) }
function node(value: unknown): CaseRuntimeNode {
  const row = uiCaseAssetObject(value)
  return { id: requiredUiCaseAssetId(row.id), status: integer(row.status), nextId: uiCaseAssetId(row.next_node_id), pending: flag(row.runtime_pending), evidence: evidence(row) }
}
export function readCaseRuntimeStep(value: unknown): CaseRuntimeStep {
  const row = uiCaseAssetObject(value)
  return {
    id: uiCaseAssetId(row.id), detailId: uiCaseAssetId(row.case_step_details_id), executionId: text(row.execution_id), testEnv: uiCaseAssetId(row.test_env),
    sequence: integer(row.progress_sequence ?? 0), status: integer(row.status), error: row.error_message == null ? null : text(row.error_message), final: flag(row.is_final),
    cache: row.cache_data, factoryCache: row.data_factory_cache_data, nodes: list(row.element_result_list).map(node).filter(item => !item.pending), evidence: evidence(row),
  }
}
export function readCaseRuntimeResult(value: unknown): CaseRuntimeResult {
  const row = uiCaseAssetObject(value)
  return {
    id: requiredUiCaseAssetId(row.id), executionId: text(row.execution_id), testEnv: uiCaseAssetId(row.test_env), status: integer(row.status), final: true,
    cache: row.cache_data, factoryCache: row.data_factory_cache_data,
    steps: list(row.steps).map(value => ({ ...readCaseRuntimeStep(value), final: true })), evidence: evidence(row),
  }
}
export function readCaseNodeProgress(value: unknown): CaseNodeProgress {
  const row = uiCaseAssetObject(value)
  return { id: requiredUiCaseAssetId(row.id), detailId: requiredUiCaseAssetId(row.case_step_details_id), executionId: text(row.execution_id), count: integer(row.completed_count ?? 0), node: node(row.element_result) }
}
export function readLatestCaseRuntime(response: unknown, caseId: UiCaseAssetId, environment: UiCaseAssetId | null): CaseRuntimeResult | null {
  const detail = uiCaseAssetResponse(response)
  if (detail == null) return null
  const row = uiCaseAssetObject(detail)
  if (row.source_type !== 'page' || row.target_type !== 'ui_case' || String(requiredUiCaseAssetId(row.target_id)) !== String(caseId) || String(uiCaseAssetId(row.test_env)) !== String(environment)) throw Error('Unexpected runtime result scope')
  if (row.result_data == null) return null
  const result = readCaseRuntimeResult(row.result_data)
  if (String(result.id) !== String(caseId) || String(result.testEnv) !== String(environment)) throw Error('Unexpected runtime result')
  return result
}
export function caseRuntimeStepEvidence(step: CaseRuntimeStep | null | undefined): Record<string, unknown> | null {
  if (!step) return null
  const nodes: Record<string, unknown>[] = step.nodes.map(item => ({ ...item.evidence, id: item.id, status: item.status, next_node_id: item.nextId }))
  const last = step.nodes[step.nodes.length - 1]
  if (!step.final && last && last.status !== 0 && last.nextId !== null && !step.nodes.some(item => String(item.id) === String(last.nextId))) nodes.push({ id: last.nextId, status: 3, next_node_id: null, runtime_pending: true })
  return { ...step.evidence, id: step.id, case_step_details_id: step.detailId, execution_id: step.executionId, test_env: step.testEnv, status: step.status, is_final: step.final, progress_sequence: step.sequence, error_message: step.error, cache_data: step.cache, data_factory_cache_data: step.factoryCache, element_result_list: nodes }
}
export function mergeCaseRuntimeStep(current: CaseRuntimeResult | null, step: CaseRuntimeStep, caseId: UiCaseAssetId): CaseRuntimeResult {
  const previous = current?.executionId === step.executionId ? current : null
  if (previous?.final) return previous
  const existing = previous?.steps.find(item => String(item.detailId) === String(step.detailId))
  if (previous && existing && (existing.final || step.sequence < existing.sequence || (!step.final && step.nodes.length < existing.nodes.length))) return previous
  const steps = [...(previous?.steps ?? [])], index = steps.findIndex(item => String(item.detailId) === String(step.detailId))
  if (index < 0) steps.push(step); else steps[index] = step
  return { id: caseId, executionId: step.executionId, testEnv: step.testEnv, status: step.final && step.status === 0 ? 0 : 3, final: false, cache: previous?.cache, factoryCache: previous?.factoryCache, steps, evidence: previous?.evidence ?? Object.freeze({}) }
}
export function mergeCaseNodeProgress(current: CaseRuntimeResult | null, progress: CaseNodeProgress, caseId: UiCaseAssetId, environment: UiCaseAssetId | null): CaseRuntimeResult | null {
  if (!current || current.executionId !== progress.executionId || current.final) return current
  const existing = current.steps.find(item => String(item.detailId) === String(progress.detailId))
  if (existing?.final || (progress.count > 0 && progress.count < (existing?.nodes.length ?? 0))) return current
  const nodes = [...(existing?.nodes ?? [])], index = nodes.findIndex(item => String(item.id) === String(progress.node.id))
  if (index < 0) nodes.push(progress.node); else nodes[index] = progress.node
  const step: CaseRuntimeStep = { id: progress.id, detailId: progress.detailId, executionId: progress.executionId, testEnv: environment, sequence: existing?.sequence ?? 0, status: 3, error: existing?.error ?? null, final: false, cache: existing?.cache, factoryCache: existing?.factoryCache, evidence: existing?.evidence ?? Object.freeze({}), nodes }
  return mergeCaseRuntimeStep(current, step, caseId)
}
export function applyCaseRuntimeRows(rows: CaseStepRow[], result: CaseRuntimeResult, resetMissing: boolean): CaseStepRow[] {
  const steps = new Map(result.steps.filter(item => item.detailId !== null).map(item => [String(item.detailId), item]))
  return rows.map(row => { const step = steps.get(String(row.id)); return step ? { ...row, status: step.final ? step.status : 3, error_message: step.error } : resetMissing ? { ...row, status: 2, error_message: null } : row })
}
export function caseRuntimeCache(result: CaseRuntimeResult | null, factory = false): unknown {
  const present = (value: unknown) => value !== null && value !== undefined && value !== '' && (Array.isArray(value) ? value.length > 0 : typeof value === 'object' ? Object.keys(value).length > 0 : true)
  const own = factory ? result?.factoryCache : result?.cache
  if (present(own)) return own
  const last = [...(result?.steps ?? [])].reverse().find(item => present(factory ? item.factoryCache : item.cache))
  return (factory ? last?.factoryCache : last?.cache) ?? {}
}
