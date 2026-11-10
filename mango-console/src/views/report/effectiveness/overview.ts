import { effectivenessObject } from './ai-summary'

type Source = Record<string, unknown>
export type EffectivenessId = number | string | null
export const effectivenessText = (value: unknown): string => typeof value === 'string' ? value : ''
export function effectivenessNumber(value: unknown): number | null {
  if (typeof value !== 'number' && (typeof value !== 'string' || !value.trim())) return null
  if (typeof value === 'string' && !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value.trim())) return null
  const result = Number(value)
  return Number.isFinite(result) ? result : null
}
export function effectivenessId(value: unknown): EffectivenessId {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value >= 0 ? value : null
  return typeof value === 'string' && /^\d+$/.test(value.trim()) ? value.trim() : null
}
export function effectivenessChartIndex(value: unknown): number | null {
  const index = effectivenessObject(value)?.dataIndex
  return typeof index === 'number' && Number.isSafeInteger(index) && index >= 0 ? index : null
}
export function effectivenessDate(value: unknown): string {
  const candidate = typeof value === 'string' ? value.slice(0, 10) : ''
  if (!/^\d{4}-\d{2}-\d{2}$/.test(candidate)) return ''
  const time = Date.parse(`${candidate}T00:00:00Z`)
  return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === candidate ? candidate : ''
}
const object = (value: unknown): Source => effectivenessObject(value) ?? {}
const objects = (value: unknown): Source[] => Array.isArray(value) ? value.filter((item): item is Source => effectivenessObject(item) !== null) : []
const count = (value: unknown): number => { const result = effectivenessNumber(value); return result !== null && result >= 0 ? result : 0 }
const rate = (value: unknown): number | null => { const result = effectivenessNumber(value); return result !== null && result >= 0 && result <= 100 ? result : null }
function counts<K extends string>(row: Source, keys: readonly K[]): Record<K, number> {
  return Object.fromEntries(keys.map(key => [key, count(row[key])])) as Record<K, number>
}
function numbers<K extends string>(row: Source, keys: readonly K[]): Record<K, number | null> {
  return Object.fromEntries(keys.map(key => [key, effectivenessNumber(row[key])])) as Record<K, number | null>
}
const resultCountKeys = ['suite_count', 'detail_count', 'success_count', 'failed_count', 'warning_count', 'proceed_count', 'stay_begin_count', 'stopped_count', 'unfinished_count'] as const
function resultCounts(row: Source) { return counts(row, resultCountKeys) }
function cards(value: unknown) {
  const row = object(value)
  return {
    ...resultCounts(row), ...counts(row, ['flaky_count', 'issue_count', 'feedback_sample_count', 'feedback_report_count'] as const),
    ...numbers(row, ['p95_first_feedback_seconds', 'p95_feedback_seconds'] as const),
    final_pass_rate: rate(row.final_pass_rate), completion_rate: rate(row.completion_rate), flaky_rate: rate(row.flaky_rate),
    feedback_sample_coverage: rate(row.feedback_sample_coverage), data_completeness: rate(row.data_completeness),
  }
}
function dimension(row: Source) {
  return {
    ...resultCounts(row), final_pass_rate: rate(row.final_pass_rate), completion_rate: rate(row.completion_rate),
    scene: effectivenessText(row.scene), scene_name: effectivenessText(row.scene_name),
    scope: effectivenessText(row.scope), scope_name: effectivenessText(row.scope_name),
    type: effectivenessId(row.type), type_name: effectivenessText(row.type_name),
    environment: effectivenessId(row.environment), environment_name: effectivenessText(row.environment_name),
  }
}
function moduleQuality(row: Source) {
  const level = row.quality_level
  const quality_level: 'danger' | 'warning' | 'success' | 'unknown' = level === 'danger' || level === 'warning' || level === 'success' ? level : 'unknown'
  return {
    ...dimension(row), module_id: effectivenessId(row.module_id), module_key: effectivenessText(row.module_key), module_path: effectivenessText(row.module_path),
    project_name: effectivenessText(row.project_name), project_product_name: effectivenessText(row.project_product_name),
    quality_level, quality_label: effectivenessText(row.quality_label) || '未知', pass_rate_delta: effectivenessNumber(row.pass_rate_delta),
    previous_final_pass_rate: rate(row.previous_final_pass_rate),
  }
}
export type EffectivenessModule = ReturnType<typeof moduleQuality>
export type EffectivenessDimension = ReturnType<typeof dimension>
function period(row: Source) { return { start: effectivenessText(row.start), end: effectivenessText(row.end) } }
function periodQuality(row: Source) { return { ...cards(row), ...period(row), key: effectivenessText(row.key), label: effectivenessText(row.label) } }
export type EffectivenessPeriod = ReturnType<typeof periodQuality>
export function normalizeEffectivenessPeriods(value: unknown): EffectivenessPeriod[] { return objects(value).map(periodQuality) }
function taskHealth(row: Source) {
  return {
    ...dimension(row), task_id: effectivenessId(row.task_id), task_name: effectivenessText(row.task_name),
    project_product_name: effectivenessText(row.project_product_name), module_name: effectivenessText(row.module_name),
    diagnostic_file_path: effectivenessText(row.diagnostic_file_path),
    execution_scene_names: Array.isArray(row.execution_scene_names) ? row.execution_scene_names.filter((value): value is string => typeof value === 'string') : [],
    ...counts(row, ['report_completed_count', 'report_success_count', 'execution_count', 'issue_count', 'consecutive_abnormal'] as const),
    report_success_rate: rate(row.report_success_rate),
  }
}
export type EffectivenessTask = ReturnType<typeof taskHealth>
function failedCase(row: Source) {
  return {
    task_id: effectivenessId(row.task_id), task_name: effectivenessText(row.task_name), case_type: effectivenessNumber(row.case_type),
    case_type_name: effectivenessText(row.case_type_name), case_id: effectivenessId(row.case_id), case_name: effectivenessText(row.case_name),
    project_product_name: effectivenessText(row.project_product_name), environment_name: effectivenessText(row.environment_name),
    latest_failed_detail_id: effectivenessId(row.latest_failed_detail_id), latest_error: effectivenessText(row.latest_error), latest_time: effectivenessText(row.latest_time),
    ...counts(row, ['attempt_count', 'failed_count'] as const), failure_rate: rate(row.failure_rate),
  }
}
export type EffectivenessFailedCase = ReturnType<typeof failedCase>
function sceneBenefit(row: Source) {
  return { scene: effectivenessText(row.scene), name: effectivenessText(row.name), ...counts(row, ['suite_count', 'execution_count', 'unique_case_count', 'abnormal_count', 'active_day_count'] as const) }
}
function benefits(value: unknown) {
  const row = object(value)
  return {
    ...counts(row, ['report_count', 'execution_count', 'unique_case_count', 'detected_issue_count', 'abnormal_result_count', 'affected_case_count', 'retry_recovered_count', 'period_recovered_case_count', 'active_day_count', 'project_product_count', 'module_count', 'environment_count', 'feedback_sample_count', 'feedback_report_count'] as const),
    ...numbers(row, ['p95_first_feedback_seconds', 'p95_feedback_seconds'] as const), feedback_sample_coverage: rate(row.feedback_sample_coverage),
    scene_benefits: objects(row.scene_benefits).map(sceneBenefit),
    automation_types: objects(row.automation_types).map(item => ({ type: effectivenessId(item.type), name: effectivenessText(item.name), count: count(item.count) })),
  }
}
function sceneMatrix(value: unknown) {
  const row = object(value)
  const options = (value: unknown) => objects(value).flatMap(item => {
    const key = typeof item.key === 'string' ? item.key.trim() || null : effectivenessId(item.key)
    return key === null ? [] : [{ key, title: effectivenessText(item.title) }]
  })
  const scenes = options(row.scenes), environments = options(row.environments)
  type Cell = { detail_count: number; failed_count: number; final_pass_rate: number | null }
  const values: Record<string, Record<string, Cell>> = Object.create(null)
  const source = object(row.values)
  for (const environment of environments) {
    const cells: Record<string, Cell> = Object.create(null), raw = object(source[String(environment.key)])
    for (const scene of scenes) {
      const cell = effectivenessObject(raw[String(scene.key)])
      if (cell) cells[String(scene.key)] = { detail_count: count(cell.detail_count), failed_count: count(cell.failed_count), final_pass_rate: rate(cell.final_pass_rate) }
    }
    values[String(environment.key)] = cells
  }
  return { scenes, environments, values }
}
export function normalizeEffectivenessOverview(value: unknown) {
  const row = object(value), comparison = object(row.comparison), convergence = object(row.convergence)
  const direction = convergence.direction
  const convergenceDirection: 'converging' | 'diverging' | 'stable' | 'unknown' = direction === 'converging' || direction === 'diverging' || direction === 'stable' ? direction : 'unknown'
  return {
    cards: cards(row.cards), previous_period: period(object(row.previous_period)),
    comparison: { has_previous: comparison.has_previous === true, ...numbers(comparison, ['final_pass_rate_delta', 'flaky_rate_delta', 'detail_count_delta', 'issue_count_delta', 'issue_rate_delta'] as const) },
    benefits: benefits(row.benefits),
    convergence: { direction: convergenceDirection, ...counts(convergence, ['current_issue_count', 'previous_issue_count', 'affected_case_count', 'new_issue_case_count', 'recovered_case_count'] as const),
      ...numbers(convergence, ['issue_count_delta', 'issue_rate_delta'] as const), current_issue_rate: rate(convergence.current_issue_rate), previous_issue_rate: rate(convergence.previous_issue_rate) },
    module_quality: objects(row.module_quality).map(moduleQuality),
    insights: objects(row.insights).map(item => ({ level: effectivenessText(item.level), title: effectivenessText(item.title), description: effectivenessText(item.description) })),
    trend: objects(row.trend).map(item => ({ ...dimension(item), date: effectivenessText(item.date), date_value: effectivenessText(item.date_value) })),
    period_quality: normalizeEffectivenessPeriods(row.period_quality),
    scene_distribution: objects(row.scene_distribution).map(dimension), scope_distribution: objects(row.scope_distribution).map(dimension),
    environment_quality: objects(row.environment_quality).map(dimension), automation_type_quality: objects(row.automation_type_quality).map(dimension),
    scene_matrix: sceneMatrix(row.scene_matrix),
    task_source_summary: counts(object(row.task_source_summary), ['task_count', 'report_count', 'execution_count', 'report_success_count'] as const),
    task_health: objects(row.task_health).map(taskHealth), failed_case_ranking: objects(row.failed_case_ranking).map(failedCase),
  }
}
export type EffectivenessOverview = ReturnType<typeof normalizeEffectivenessOverview>
export const createEmptyOverview = (): EffectivenessOverview => normalizeEffectivenessOverview(null)

export interface EffectivenessMatrixRow {
  environmentIndex: number; sceneIndex: number; environment: string; scene: string; label: string
  finalPassRate: number; detailCount: number; failedCount: number
}
export function effectivenessMatrixRows(matrix: EffectivenessOverview['scene_matrix']): EffectivenessMatrixRow[] {
  const result: EffectivenessMatrixRow[] = []
  matrix.environments.forEach((environment, environmentIndex) => {
    matrix.scenes.forEach((scene, sceneIndex) => {
      const item = matrix.values[String(environment.key)]?.[String(scene.key)]
      if (!item || item.final_pass_rate === null) return
      result.push({ environmentIndex, sceneIndex, environment: environment.title, scene: scene.title, label: `${environment.title} · ${scene.title}`,
        finalPassRate: item.final_pass_rate, detailCount: item.detail_count, failedCount: item.failed_count })
    })
  })
  return result.sort((left, right) => left.finalPassRate - right.finalPassRate || right.detailCount - left.detailCount)
}
