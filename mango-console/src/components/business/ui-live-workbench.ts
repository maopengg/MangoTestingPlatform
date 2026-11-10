import { cloneLosslessJson } from '@/utils/lossless-json'

export type LiveId = string | number
export type ScanMode = 'quick' | 'deep' | 'region'
export interface LiveLocator {
  exp: number | null; loc: string; sub: string | number
  source?: string; match_count?: number; score?: number
  candidate_id?: string; verified?: boolean; validation_done?: boolean
  count?: number; visible?: boolean; duration_ms?: number; element_text?: string; error_message?: string
  reason?: string; risk?: string; strategy?: string; confidence?: number
}
export interface LiveElement {
  id?: LiveId; name?: string; category?: string; tag?: string; role?: string; text?: string
  label?: string; accessible_name?: string; placeholder?: string; attributes?: Record<string, unknown>
  frame_depth?: number; shadow_depth?: number; in_viewport?: boolean; risks?: string[]
  locators?: LiveLocator[]; baseline_snapshot?: Record<string, unknown>; ai_heal_status?: number
  exp?: number | null; loc?: string; sub?: string | number
  exp2?: number | null; loc2?: string; sub2?: string | number
  exp3?: number | null; loc3?: string; sub3?: string | number
  _rowKey?: string; _name?: string; _category?: string; _checking?: boolean
  _aiLoading?: boolean; _saving?: boolean; _saved?: boolean
  _checkStatus?: string; _checkDuration?: number; _checkKey?: string
}
export interface LiveNodeDetail {
  type?: number; ope_key?: string | string[] | null; ope_value?: Array<{ f: string; v: unknown }>
  ele_name?: LiveId | null; sql_execute?: Array<{ datasource_alias: LiveId | null; sql: string; key_list: string }>
  custom?: Array<{ key: string; value: unknown }>; func?: string
}
export interface RecordedAction {
  client_id: string; action: string; name: string; category: string; status: string
  detail: LiveNodeDetail | null; element?: LiveElement | null; element_id?: LiveId | null
  page?: { page_id?: LiveId; url?: string }; input_value?: string; value?: unknown; key?: string
  delta_x?: number; delta_y?: number; drag_delta_x?: number; drag_delta_y?: number
  seconds?: number; expect?: string; url?: string; sensitive?: boolean; passive?: boolean; duration_ms?: number
  _checking?: boolean; _checkStatus?: string; _checkDuration?: number; _checkKey?: string
}
export interface RecorderSettings { mergeInput: boolean; recordScroll: boolean; recordNavigation: boolean }
export interface RecorderField {
  label: string; key: string; value: unknown; type: string; required: boolean; placeholder?: string
  field?: string; compactHalf?: boolean; compactNarrow?: boolean; compactWideLabel?: boolean
  min?: number; max?: number; precision?: number; suffix?: string
}
export interface LiveActuator {
  username: string; name?: string; is_owner?: boolean; is_full?: boolean
  active_user_count?: number; max_user_count?: number; users?: Array<{ username: string }>
}
export function readLiveActuators(value: unknown): LiveActuator[] {
  if (!Array.isArray(value)) return []
  return value.map(value => {
    const row = liveObject(value)
    if (typeof row.username !== 'string' || !row.username) throw Error('执行器选项返回格式不正确')
    return {
      username: row.username, name: typeof row.name === 'string' ? row.name : '',
      is_owner: row.is_owner === true, is_full: row.is_full === true,
      active_user_count: Number(row.active_user_count ?? 0), max_user_count: Number(row.max_user_count ?? 5),
      users: Array.isArray(row.users) ? row.users.map(value => ({ username: String(liveObject(value).username ?? '') })) : [],
    }
  })
}
export interface ScanStats { scan_mode: ScanMode; returned_count?: number; duration_ms?: number; frame_count?: number; shadow_roots?: number }
export interface LiveLocatorResult extends LiveLocator {
  group?: number; slot?: number; status?: string; highlighted?: boolean; highlighted_count?: number
  enabled?: boolean; editable?: boolean; highlight_error?: string; same_target?: boolean
}
export interface LiveResult {
  id?: LiveId; name?: string; type?: number; ope_key?: string; status?: number; sleep?: number | null
  duration_ms?: number | null; page_url?: string; page_title?: string; error_message?: string
  element_id?: LiveId; element_name?: string; check_id?: string; executor_task_id?: LiveId
  check_mode?: 'normal' | 'deep'; check_status?: string; checked_time?: string; scan_row_key?: string
  workspace_id?: LiveId; is_final?: boolean
  locator_engine?: { used_source?: string; candidate_count?: number; temporary_heal_used?: boolean; screenshot_error?: string; locator_updates?: LiveLocatorResult[] }
  locator_groups?: LiveLocatorResult[]; elements?: Array<Partial<LiveLocator> & { name?: string; ele_quantity?: string; element_text?: string }>
  expected_event_result?: { configured?: boolean; executed?: boolean; ope_key?: string; status?: number }
  baseline?: { before?: string; after?: string; collection_requested?: boolean }
  selected_result?: LiveResult; element_result_list?: LiveResult[]; result_data?: { element_result_list?: LiveResult[] }
  element_result?: LiveResult | LiveResult[]
}
export interface LiveCommandData {
  element?: LiveElement; recorded_action?: Partial<RecordedAction>; passive_actions?: Partial<RecordedAction>[]
  element_result?: LiveResult; scan_check_result?: LiveResult; row_key?: string; baseline_snapshot?: Record<string, unknown>
}
export function readLiveResult(value: unknown): LiveResult {
  return cloneLosslessJson(liveObject(value)) as LiveResult
}
export function liveId(value: unknown): LiveId | null {
  if (typeof value === 'string' && value.trim()) return value
  if (typeof value === 'number' && Number.isSafeInteger(value) && value >= 0) return value
  return null
}
export function routeLiveId(value: unknown): string | undefined {
  const id = liveId(value)
  return id === null ? undefined : String(id)
}
export function liveObject(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
export function liveError(error: unknown, fallback: string): string {
  const row = liveObject(error)
  return typeof row.msg === 'string' ? row.msg : typeof row.message === 'string' ? row.message : fallback
}
export function readLiveLocator(value: unknown): LiveLocator {
  const row = liveObject(value)
  return { ...row, exp: typeof row.exp === 'number' ? row.exp : null, loc: typeof row.loc === 'string' ? row.loc : '', sub: typeof row.sub === 'string' || typeof row.sub === 'number' ? row.sub : '' } as LiveLocator
}
// Executor evidence is extensible; normalize the fields edited by this UI while retaining evidence in snapshots.
export function readLiveElement(value: unknown): LiveElement {
  const row = liveObject(value)
  return { ...cloneLosslessJson(row), id: liveId(row.id) ?? undefined, locators: Array.isArray(row.locators) ? row.locators.map(readLiveLocator) : undefined, baseline_snapshot: liveObject(row.baseline_snapshot) } as LiveElement
}
export function readRecordedAction(value: unknown): Partial<RecordedAction> {
  const row = cloneLosslessJson(liveObject(value))
  return { ...row, ...(row.element ? { element: readLiveElement(row.element) } : {}), ...(row.detail ? { detail: liveObject(row.detail) } : {}) } as Partial<RecordedAction>
}
export function recordingSnapshot(actions: RecordedAction[]): Record<string, unknown>[] {
  return actions.map(({ _checking, _checkStatus, _checkDuration, _checkKey, ...action }) => cloneLosslessJson({ ...action }))
}
