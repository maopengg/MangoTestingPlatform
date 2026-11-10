import type { EffectivenessQuery } from '@/api/system/automation-effectiveness'
import { defaultPeriodPreset, periodPresetOptions, type PeriodPreset } from './config'
import { effectivenessId } from './overview'

type FilterValue = number | string
export type ProductSelection = FilterValue | FilterValue[] | null | undefined
export interface EffectivenessFilters {
  periodPreset: PeriodPreset
  dateRange: string[]
  project_product: ProductSelection
  test_env: FilterValue[]
  execution_scene: FilterValue[]
  execution_scope: FilterValue[]
}
function formatDate(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
function shiftMonthsClamped(date: Date, months: number): Date {
  const target = new Date(date.getFullYear(), date.getMonth() - months, 1)
  const targetMonthLastDay = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate()
  target.setDate(Math.min(date.getDate(), targetMonthLastDay))
  return target
}
export function resolvePeriodDateRange(preset: PeriodPreset, current = new Date()): string[] {
  const end = new Date(current.getFullYear(), current.getMonth(), current.getDate()), start = new Date(end)
  if (preset === 'recent_2_days' || preset === 'recent_7_days' || preset === 'recent_14_days') {
    const days = preset === 'recent_2_days' ? 2 : preset === 'recent_7_days' ? 7 : 14
    start.setDate(start.getDate() - days + 1)
  } else if (preset === 'recent_month' || preset === 'recent_3_months') {
    start.setTime(shiftMonthsClamped(end, preset === 'recent_month' ? 1 : 3).getTime())
    start.setDate(start.getDate() + 1)
  } else if (preset === 'natural_month') start.setDate(1)
  else if (preset === 'natural_quarter') start.setMonth(Math.floor(start.getMonth() / 3) * 3, 1)
  else {
    start.setDate(start.getDate() - (start.getDay() || 7) + 1)
    if (preset === 'natural_two_weeks') start.setDate(start.getDate() - 7)
  }
  return [formatDate(start), formatDate(end)]
}
export function createDefaultFilters(current = new Date()): EffectivenessFilters {
  return { periodPreset: defaultPeriodPreset, dateRange: resolvePeriodDateRange(defaultPeriodPreset, current), project_product: undefined, test_env: [], execution_scene: [], execution_scope: [] }
}
export function selectedEffectivenessProduct(value: unknown): number | string | null {
  return effectivenessId(Array.isArray(value) ? value[value.length - 1] : value)
}
const filterValues = (value: unknown): FilterValue[] => Array.isArray(value) ? value.filter((item): item is FilterValue => (typeof item === 'string' && item.trim().length > 0) || (typeof item === 'number' && Number.isFinite(item))) : []
export function copyEffectivenessFilters(source: EffectivenessFilters): EffectivenessFilters {
  return {
    periodPreset: periodPresetOptions.some(option => option.value === source.periodPreset) ? source.periodPreset : defaultPeriodPreset,
    dateRange: Array.isArray(source.dateRange) ? source.dateRange.filter((item): item is string => typeof item === 'string') : [],
    project_product: Array.isArray(source.project_product) ? [...source.project_product] : source.project_product,
    test_env: filterValues(source.test_env), execution_scene: filterValues(source.execution_scene), execution_scope: filterValues(source.execution_scope),
  }
}
export function effectivenessQuery(filters: EffectivenessFilters): EffectivenessQuery {
  const snapshot = copyEffectivenessFilters(filters), params: EffectivenessQuery = {}
  if (snapshot.dateRange.length === 2) [params.start_date, params.end_date] = snapshot.dateRange
  const productId = selectedEffectivenessProduct(snapshot.project_product)
  if (productId !== null) params.project_product_id = productId
  if (snapshot.test_env.length) params.test_env = snapshot.test_env.join(',')
  if (snapshot.execution_scene.length) params.execution_scene = snapshot.execution_scene.join(',')
  if (snapshot.execution_scope.length) params.execution_scope = snapshot.execution_scope.join(',')
  return params
}
