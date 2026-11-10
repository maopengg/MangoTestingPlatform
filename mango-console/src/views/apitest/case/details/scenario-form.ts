import type { ScenarioEditorMode, ApiCaseStep, ApiCaseScenario } from './types'
export function scenarioFormValues(scenario?: Partial<ApiCaseScenario>) {
  const item = scenario || {}
  return {
    name: String(item.name || ''),
    error_retry: item.error_retry ?? '',
    retry_interval: item.retry_interval ?? '',
    allow_failure: Boolean(item.allow_failure),
  }
}
export function scenarioSubmitPayload(
  values: Record<string, unknown>,
  step: ApiCaseStep,
  mode: ScenarioEditorMode,
  id: number | null
) {
  const payload = {...values}
  if (mode === 'create') {
    payload.case_detailed = step.id
    payload.api_info = step.api_info?.id
  } else payload.id = id
  return payload
}
