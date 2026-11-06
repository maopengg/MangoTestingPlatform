import { get } from '@/api/http'

export type EfficiencySection = 'queue' | 'timing' | 'anomalies'
export interface EfficiencyResponse {
  summary: Record<string, number | null>
  items?: Array<Record<string, any>>
  count?: number
  workers?: { online: number; capacity: number; running: number }
  as_of?: string
  scope?: string | { start_at: string; end_at: string; cohort: string }
  basic?: Array<Record<string, any>>
  phases?: Array<{ name: string; duration_ms: number }>
  trend?: Array<{ time: string; completed: number; p50_ms: number | null; p95_ms: number | null }>
  slow_cases?: Array<Record<string, any>>
  slow_reports?: Array<Record<string, any>>
}

export function getExecutionEfficiency(data: Record<string, any>) {
  return get<EfficiencyResponse>({ url: 'system/test/suite/execution-efficiency', data: () => data })
}

export function getExecutionEfficiencyOptions(data: Record<string, any>) {
  return get<{ items: Array<{ id: number; name: string }>; has_more: boolean }>({
    url: 'system/test/suite/execution-efficiency/options', data: () => data,
  })
}
