import { get, post } from '@/api/http'

export interface EffectivenessQuery {
  start_date?: string
  end_date?: string
  project_product_id?: number | string
  test_env?: string
  execution_scene?: string
  execution_scope?: string
}
export interface EffectivenessAiContext {
  project_product: string; period: string; comparison_period: string
  environment: string; task_type: string; coverage_scope: string
}
export interface EffectivenessAiRequest {
  overview: Record<string, unknown>
  context: EffectivenessAiContext
  force: boolean
  mode?: 'insights'
  insight_keys?: string[]
}
export function getAutomationEffectivenessOverview(data: EffectivenessQuery, silentError = false) {
  return get({
    url: 'system/test/suite/effectiveness/overview',
    data: () => data,
    silentError,
  })
}

export function postAutomationEffectivenessCacheClear() {
  return post({
    url: 'system/test/suite/effectiveness/cache/clear',
  })
}

export function postAutomationEffectivenessAiSummary(data: EffectivenessAiRequest) {
  return post({
    url: 'system/test/suite/effectiveness/ai-summary',
    data,
    silentError: true,
  })
}
