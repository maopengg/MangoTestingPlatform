export type ConfigSearchTarget = {
  stepId?: string | number
  scenarioId?: string | number
  caseApiType?: string
  caseApiSonType?: string
  detailType?: string
  detailTab?: string
}

export type ConfigSearchDocument = ConfigSearchTarget & {
  location: string
  fieldLabel: string
  value: any
}

export type ConfigSearchMatch = ConfigSearchTarget & {
  location: string
  path: string
  preview: string
}

export type ApiCaseExecutionTraceQuery = {
  result_id?: number | string
  trace_id?: string
  test_suite_detail_id?: string | number
  case_id?: string | number
}
