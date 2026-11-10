import { cloneLosslessJson } from '@/utils/lossless-json'
import { liveId, liveObject, readLiveResult, type LiveId, type LiveResult } from './ui-live-workbench'

export interface ElementEventParameter { f: string; n?: string; p?: string; d?: boolean; v: unknown }
export interface ElementOperation { value: string; children?: ElementOperation[]; parameter?: ElementEventParameter[] }
export interface ElementEditorDraft {
  id: LiveId | null; page: LiveId | null; name: string; category: string
  exp: number | null; loc: string; sub: string | number
  exp2: number | null; loc2: string; sub2: string | number
  exp3: number | null; loc3: string; sub3: string | number
  sleep: string | number; is_iframe: number; location_description: string; surrounding_text: string; prompt: string
  expected_event: { ope_key: string; ope_value: ElementEventParameter[] }
  latest_match_count: number | string | null; latest_element_text: string; latest_runtime_time: string; latest_runtime_snapshot: LiveResult
}
const text = (value: unknown, fallback = '') => typeof value === 'string' ? value : fallback
const inputNumber = (value: unknown): string | number => typeof value === 'string' || typeof value === 'number' ? value : ''
const number = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) ? value : null
export function readElementEvent(value: unknown): ElementEditorDraft['expected_event'] {
  const row = liveObject(value)
  return { ope_key: text(row.ope_key), ope_value: Array.isArray(row.ope_value) ? row.ope_value.map(value => {
    const param = liveObject(value)
    return { f: text(param.f), n: text(param.n), p: text(param.p), d: param.d === true, v: cloneLosslessJson(param.v) }
  }) : [] }
}
export function readElementEditor(value: unknown = {}): ElementEditorDraft {
  const row = liveObject(value), page = liveObject(row.page)
  return {
    id: liveId(row.id), page: liveId(page.id ?? row.page), name: text(row.name), category: text(row.category, '未分类'),
    exp: number(row.exp), loc: text(row.loc), sub: inputNumber(row.sub),
    exp2: number(row.exp2), loc2: text(row.loc2), sub2: inputNumber(row.sub2),
    exp3: number(row.exp3), loc3: text(row.loc3), sub3: inputNumber(row.sub3),
    sleep: inputNumber(row.sleep), is_iframe: number(row.is_iframe) ?? 0,
    location_description: text(row.location_description), surrounding_text: text(row.surrounding_text), prompt: text(row.prompt),
    expected_event: readElementEvent(row.expected_event), latest_match_count: row.latest_match_count == null ? null : inputNumber(row.latest_match_count),
    latest_element_text: text(row.latest_element_text), latest_runtime_time: text(row.latest_runtime_time), latest_runtime_snapshot: readLiveResult(row.latest_runtime_snapshot),
  }
}
