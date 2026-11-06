import { inject, provide, watch, type InjectionKey } from 'vue'
import { putApiCase } from '@/api/apitest/case'
import { putApiCaseDetailedParameter } from '@/api/apitest/case-detailed-parameter'
import { createChangeAwareSave } from '@/utils/change-aware-save'

type ParameterSave = (
  payload: Parameters<typeof putApiCaseDetailedParameter>[0]
) => Promise<Awaited<ReturnType<typeof putApiCaseDetailedParameter>> | null>
const parameterSaveKey: InjectionKey<ParameterSave> = Symbol('api-case-parameter-save')

const caseFields = [
  'name',
  'front_sql',
  'front_custom',
  'front_headers',
  'front_public',
  'front_auth_config',
  'posterior_sql',
  'callback_checks',
]
const parameterFields = [
  'headers',
  'params',
  'body_config',
  'sse_config',
  'front_sql',
  'front_func',
  'ass_general',
  'ass_sql',
  'ass_json_all',
  'ass_text_all',
  'ass_jsonpath',
  'ass_schema',
  'posterior_sql',
  'posterior_response',
  'posterior_response_text',
  'posterior_sleep',
  'posterior_func',
  'posterior_file',
]

function editableValues(record: any, fields: string[]) {
  return { id: record?.id, ...Object.fromEntries(fields.map((key) => [key, record?.[key]])) }
}

export function useApiCaseAutoSave(record: () => any, scenarios: () => any[]) {
  const caseSave = createChangeAwareSave(putApiCase)
  const parameterSave = createChangeAwareSave(putApiCaseDetailedParameter)
  watch(record, (value) => caseSave.seed(editableValues(value, caseFields)), {
    immediate: true,
    flush: 'sync',
  })
  watch(
    scenarios,
    (values) =>
      values.forEach((value) => parameterSave.seed(editableValues(value, parameterFields))),
    { immediate: true, flush: 'sync' }
  )
  provide(parameterSaveKey, parameterSave.save)
  return { saveCase: caseSave.save, saveParameter: parameterSave.save }
}

export function useApiCaseParameterSave() {
  return inject(parameterSaveKey, putApiCaseDetailedParameter)
}
