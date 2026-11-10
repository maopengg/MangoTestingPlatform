type Scalar = number | string | null
type Evidence = Record<string, unknown>
export interface UiLocatorView { exp: Scalar; loc: string; sub: Scalar }
export interface UiElementView {
  id: Scalar; name: string; locators: UiLocatorView[]; ele_quantity: number | null
  visible: boolean | null; enabled: boolean | null; editable: boolean | null
  locate_duration_ms: number | null; bounding_box: { x: Scalar; y: Scalar; width: Scalar; height: Scalar } | null
  text_snippets: string[]; element_text: string; __configuredFallback: boolean
}
export interface UiLocatorCandidate {
  loc: string; source: string; count: number | null; final_score: number | null
  verified: boolean; adopted: boolean; decision_status: string; reject_reason: string; decision_reasons: string[]
}
export interface UiRuntimeView {
  id: Scalar; page_step_details_id: Scalar; name: string; elementName: string; type: Scalar; ope_key: string
  status: number | null; sleep: Scalar; duration_ms: number | null; test_time: Scalar; stop_time: Scalar
  error_message: string; ass_msg: string; picture_path: string; page_title: string; page_url: string
  viewport: { width: Scalar; height: Scalar } | null; elements: UiElementView[]
  locator_engine: { used_source: string; candidate_count: number | null; temporary_heal_used: boolean; candidates: UiLocatorCandidate[] } | null
}
export interface UiStepView extends UiRuntimeView { runtimeRows: UiRuntimeView[] }
export interface UiReportView {
  name: string; case_name: string; status: number | null; test_time: Scalar; test_object: string
  cache_data: unknown; data_factory_cache_data: unknown; steps: UiStepView[]
}
export const uiReportObject = (value: unknown): Evidence | null => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Evidence : null
const text = (value: unknown): string => typeof value === 'string' ? value : ''
const scalar = (value: unknown): Scalar => typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value)) ? value : null
const numeric = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) ? value : null
const bool = (value: unknown): boolean | null => typeof value === 'boolean' ? value : null
const strings = (value: unknown): string[] => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item.length > 0) : []
function objects(value: unknown): Evidence[] { return Array.isArray(value) ? value.filter((item): item is Evidence => uiReportObject(item) !== null) : [] }
function firstArray(row: Evidence, keys: string[]): Evidence[] | null {
  for (const key of keys) {
    const values = row[key]
    if (Array.isArray(values) && values.length) return objects(values)
  }
  return null
}
function locatorText(value: unknown): string {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'object') {
    try { return JSON.stringify(value) || '-' } catch { return '-' }
  }
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean' ? String(value) : '-'
}
function locators(row: Evidence): UiLocatorView[] {
  if (Array.isArray(row.locators)) return objects(row.locators).map(item => ({
    exp: scalar(item.exp), loc: locatorText(item.loc), sub: scalar(item.sub),
  })).filter(item => item.loc !== '-')
  if (Array.isArray(row.loc)) return row.loc.map((value, index) => {
    const item = uiReportObject(value)
    return item ? {
      exp: scalar(item.exp ?? item.type ?? row.exp), loc: locatorText(item.loc ?? item.value ?? item.expression), sub: scalar(item.sub ?? row.sub),
    } : {
      exp: scalar(Array.isArray(row.exp) ? row.exp[index] : row.exp), loc: locatorText(value), sub: scalar(row.sub),
    }
  }).filter(item => item.loc !== '-')
  return ['', '2', '3'].map(suffix => ({ exp: scalar(row[`exp${suffix}`]), loc: locatorText(row[`loc${suffix}`]), sub: scalar(row[`sub${suffix}`]) })).filter(item => item.loc !== '-')
}
function element(value: unknown, configured = false): UiElementView | null {
  const row = uiReportObject(value)
  if (!row) return null
  const box = uiReportObject(row.bounding_box)
  return {
    id: scalar(row.id), name: text(row.name), locators: locators(row), ele_quantity: numeric(row.ele_quantity),
    visible: bool(row.visible), enabled: bool(row.enabled), editable: bool(row.editable),
    locate_duration_ms: numeric(row.locate_duration_ms),
    bounding_box: box ? { x: scalar(box.x), y: scalar(box.y), width: scalar(box.width), height: scalar(box.height) } : null,
    text_snippets: strings(row.text_snippets), element_text: text(row.element_text), __configuredFallback: configured || row.__configuredFallback === true,
  }
}
function elementRows(row: Evidence): UiElementView[] {
  const values = firstArray(row, ['elements', 'element_result', 'element_list', 'element'])
    ?? (uiReportObject(row.ele_name) ? [row.ele_name] : row.loc != null && row.loc !== '' ? [row] : [])
  return values.map(value => element(value)).filter((value): value is UiElementView => value !== null)
}
export function uiFallbackElements(value: unknown): UiElementView[] {
  const item = element(value, true)
  return item?.locators.length ? [item] : []
}
export function normalizeUiRuntime(value: unknown): UiRuntimeView | null {
  const row = uiReportObject(value)
  if (!row) return null
  const viewport = uiReportObject(row.viewport), engine = uiReportObject(row.locator_engine)
  return {
    id: scalar(row.id), page_step_details_id: scalar(row.page_step_details_id), name: text(row.name),
    elementName: text(uiReportObject(row.ele_name)?.name) || text(row.elementName), type: scalar(row.type), ope_key: text(row.ope_key),
    status: numeric(row.status), sleep: scalar(row.sleep), duration_ms: numeric(row.duration_ms),
    test_time: scalar(row.test_time), stop_time: scalar(row.stop_time), error_message: text(row.error_message), ass_msg: text(row.ass_msg),
    picture_path: text(row.picture_path), page_title: text(row.page_title), page_url: text(row.page_url),
    viewport: viewport ? { width: scalar(viewport.width ?? viewport.w), height: scalar(viewport.height ?? viewport.h) } : null,
    elements: elementRows(row),
    locator_engine: engine ? {
      used_source: text(engine.used_source), candidate_count: numeric(engine.candidate_count), temporary_heal_used: engine.temporary_heal_used === true,
      candidates: objects(engine.candidates).map(candidate => ({
        loc: text(candidate.loc), source: text(candidate.source), count: numeric(candidate.count), final_score: numeric(candidate.final_score),
        verified: candidate.verified === true, adopted: candidate.adopted === true, decision_status: text(candidate.decision_status),
        reject_reason: text(candidate.reject_reason), decision_reasons: strings(candidate.decision_reasons),
      })),
    } : null,
  }
}
export function normalizeUiReport(value: unknown): UiReportView {
  const row = uiReportObject(value) ?? {}
  const steps = (firstArray(row, ['steps', 'element_result_list', 'children']) ?? []).map(item => {
    const step = normalizeUiRuntime(item)
    if (!step) return null
    const runtimeRows = (firstArray(item, ['element_result_list', 'children']) ?? [item]).map(normalizeUiRuntime).filter((runtime): runtime is UiRuntimeView => runtime !== null)
    return { ...step, runtimeRows }
  }).filter((step): step is UiStepView => step !== null)
  return {
    name: text(row.name), case_name: text(row.case_name), status: numeric(row.status),
    test_time: scalar(row.test_time), test_object: text(row.test_object),
    cache_data: row.cache_data, data_factory_cache_data: row.data_factory_cache_data, steps,
  }
}
