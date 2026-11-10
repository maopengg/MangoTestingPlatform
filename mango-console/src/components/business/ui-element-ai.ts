import { cloneLosslessJson } from '@/utils/lossless-json'
import { liveId, liveObject, type LiveElement, type LiveId } from './ui-live-workbench'

export interface AiTrigger { error?: string; ope_key?: string; origin_loc?: string; origin_sub?: string | number }
export interface AiCandidate {
  record_id?: LiveId; candidate_index?: number; source?: string; source_label?: string; verified?: boolean
  count?: number; final_score?: number; score?: number; confidence?: number; sub?: number | string; loc?: string; exp?: number
  diagnostic_text?: string; reject_reason?: string; reason?: string; matched_label?: string; candidate_text?: string
  element_text?: string; element_name?: string; element_role?: string; actionability_checked?: boolean; trigger?: AiTrigger; _candidateRowIndex?: number; applied_slots?: number[]
}
export interface AiEngine {
  trace_id?: string; used_source?: string; trigger?: AiTrigger
  candidate_summary?: { total?: number; checked?: number; verified?: number; by_source?: Record<string, { total?: number; checked?: number; verified?: number; reasons?: Record<string, number> }>; top_rejections?: Array<{ source?: string; reason?: string; loc?: string }> }
  harness?: { agent_called?: boolean; duration_ms?: number; prompt_version?: string }
}
export interface AiElement extends LiveElement { ai_stable_pass_count?: number; ai_last_snapshot_time?: string; ai_last_heal_time?: string; latest_match_count?: number; latest_element_text?: string; latest_runtime_snapshot?: { locator_engine?: AiEngine } }
export interface AiSnapshot { id: LiveId; create_time?: string; test_env?: LiveId; match_count?: number; element_role?: string; element_text?: string; url?: string }
export interface AiHealRecord { id?: LiveId; candidates?: AiCandidate[]; ai_prompt_summary?: { locator_engine?: AiEngine }; failed_reason?: string; error_message?: string; page_url?: string; create_time?: string; status?: number; confidence?: number; applied?: boolean; selected_loc?: string }
export interface ElementAiInfo { element: AiElement | null; latest_heal_record: AiHealRecord | null; statistics: { snapshot_count?: number; heal_record_count?: number; pending_suggestion_count?: number; applied_count?: number }; snapshots: AiSnapshot[]; heal_records: AiHealRecord[] }
export const emptyElementAiInfo = (): ElementAiInfo => ({ element: null, latest_heal_record: null, statistics: {}, snapshots: [], heal_records: [] })
export type BaselineEvidence = Partial<Record<'id' | 'element_id' | 'element' | 'create_time' | 'update_time' | 'test_env' | 'source' | 'status' | 'screenshot_path' | 'title' | 'url' | 'frame_url' | 'page_id' | 'page' | 'project_product_id' | 'project_product' | 'exp' | 'loc' | 'sub' | 'match_count' | 'locator_hash' | 'html_hash' | 'element_text' | 'element_tag' | 'element_role' | 'element_type' | 'element_name' | 'element_placeholder' | 'element_value' | 'element_attributes' | 'element_rect' | 'element_css' | 'page_dom_digest' | 'accessibility_digest' | 'outer_html' | 'parent_html' | 'nearby_html', unknown>>
export type HealEvidence = Partial<Record<'id' | 'element_id' | 'element' | 'page_id' | 'page' | 'project_product_id' | 'project_product' | 'snapshot_id' | 'snapshot' | 'test_env' | 'source' | 'status' | 'create_time' | 'update_time' | 'failed_exp' | 'failed_loc' | 'failed_sub' | 'failed_reason' | 'page_url' | 'error_message' | 'selected_exp' | 'selected_loc' | 'selected_sub' | 'confidence' | 'applied' | 'applied_by_id' | 'applied_by' | 'applied_time' | 'current_context' | 'ai_prompt_summary' | 'ai_response' | 'candidates', unknown>>
// Read-only executor diagnostics retain extra evidence at the protocol boundary; write IDs are validated separately.
export function readElementAiInfo(value: unknown): Pick<ElementAiInfo, 'element' | 'latest_heal_record' | 'statistics'> {
  const row = liveObject(value)
  return { element: row.element ? cloneLosslessJson(liveObject(row.element)) as AiElement : null, latest_heal_record: row.latest_heal_record ? cloneLosslessJson(liveObject(row.latest_heal_record)) as AiHealRecord : null, statistics: cloneLosslessJson(liveObject(row.statistics)) }
}
export function readAiSnapshots(value: unknown): AiSnapshot[] {
  const data = liveObject(value).items
  if (!Array.isArray(data)) throw Error('基线历史返回格式不正确')
  return data.map(value => { const row = liveObject(value), id = liveId(row.id); if (id === null) throw Error('基线记录缺少ID'); return { ...cloneLosslessJson(row), id } as AiSnapshot })
}
export function readAiHealRecords(value: unknown): AiHealRecord[] {
  const data = liveObject(value).items
  if (!Array.isArray(data)) throw Error('自愈历史返回格式不正确')
  return data.map(value => { const row = liveObject(value), id = liveId(row.id); if (id === null) throw Error('自愈记录缺少ID'); return { ...cloneLosslessJson(row), id } as AiHealRecord })
}
