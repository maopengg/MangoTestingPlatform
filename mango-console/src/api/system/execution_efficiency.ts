import { get } from '@/api/http'

export type EfficiencySection = 'queue' | 'timing' | 'anomalies'
export interface EfficiencyQuery {
  section: EfficiencySection
  page: number
  page_size: number
  project_product_id?: number | string
  module_ids__in?: string | number
  test_env__in?: string
  case_type__in?: string
  task_ids__in?: string
  task_group_ids__in?: string
  report_id?: string
  start_at?: string
  end_at?: string
}
export function getExecutionEfficiency(data: EfficiencyQuery) {
  return get<unknown>({ url: 'system/test/suite/execution-efficiency', data: () => data })
}
export function getExecutionEfficiencyOptions(data: { kind: 'tasks' | 'groups'; product_id?: number | string; keyword: string; page: number; page_size: number }) {
  return get<unknown>({
    url: 'system/test/suite/execution-efficiency/options', data: () => data,
  })
}
