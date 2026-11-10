import type { ScenarioEditorMode, ApiCaseStep, ApiCaseScenario } from './types'
export function getLegacyExpectedStatusCodes(item: any) {
  const codes = new Set<number>()
  const addCode = (value: unknown) => {
    const code = Number(value)
    if (Number.isInteger(code) && code >= 100 && code <= 599) {
      codes.add(code)
      return
    }
    const prefix = Number(String(value || '').slice(0, 3))
    if ([400, 404, 405, 409, 422].includes(prefix)) codes.add(prefix)
  }
  let jsonAll = item?.ass_json_all
  if (typeof jsonAll === 'string') {
    try {
      jsonAll = JSON.parse(jsonAll)
    } catch {
      jsonAll = null
    }
  }
  if (jsonAll && typeof jsonAll === 'object') addCode(jsonAll.code)
  ;(item?.ass_jsonpath || []).forEach((assertion: any) => {
    const actual = String(assertion?.actual || '').trim()
    const method = String(assertion?.method || '').toLowerCase()
    if (
      ['$.code', '$["code"]', "$['code']"].includes(actual) &&
      (!method || method.includes('equal'))
    ) {
      addCode(assertion.expect)
    }
  })
  addCode(item?.ass_schema?.properties?.code?.const)
  const latestHttpStatus = Number(item?.result_data?.response?.code)
  if ([400, 404, 405, 409, 422].includes(latestHttpStatus)) codes.add(latestHttpStatus)
  return Array.from(codes).sort((left, right) => left - right)
}

export function scenarioFormValues(scenario?: Partial<ApiCaseScenario>) {
  const item = scenario || {}
  const expectation = (
    item.body_config as { protocol_expectation?: { mode?: string; status_codes?: number[] } } | null
  )?.protocol_expectation
  const codes = getLegacyExpectedStatusCodes(item)
  return {
    name: String(item.name || ''),
    protocol_expectation_mode: expectation?.mode || (codes.length ? 'codes' : 'auto'),
    protocol_expectation_codes: (expectation?.status_codes || codes).join(','),
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
  const { protocol_expectation_mode, protocol_expectation_codes, ...payload } = values
  if (
    !['mcp', 'grpc', 'websocket'].includes(
      String(step.api_info?.protocol_type || 'http').toLowerCase()
    )
  ) {
    const expectationMode = protocol_expectation_mode || 'auto'
    payload.protocol_expectation = {
      mode: expectationMode,
      status_codes:
        expectationMode === 'codes'
          ? String(protocol_expectation_codes || '')
              .split(',')
              .map((code) => code.trim())
              .filter(Boolean)
              .map(Number)
          : [],
    }
  }
  if (mode === 'create') {
    payload.case_detailed = step.id
    payload.api_info = step.api_info?.id
  } else payload.id = id
  return payload
}
