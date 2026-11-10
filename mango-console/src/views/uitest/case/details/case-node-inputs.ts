import { cloneLosslessJson } from '@/utils/lossless-json'
import { requiredUiCaseAssetId, uiCaseAssetObject, type UiCaseAssetId } from '@/components/business/ui-case-step-create'

export interface CaseNodeInputContext { caseId: UiCaseAssetId; caseStepId: UiCaseAssetId; pageStepId: UiCaseAssetId }
export function buildCaseNodeInputs(previous: unknown[], nodeId: UiCaseAssetId, value: unknown): unknown[] {
  const result = cloneLosslessJson(previous), input = uiCaseAssetObject(value)
  const matches = result.map(uiCaseAssetObject).filter(row => String(requiredUiCaseAssetId(row.page_step_details_id)) === String(nodeId))
  if (matches.length !== 1) throw Error('Missing or duplicate case node inputs')
  const target = matches[0]
  const type = Number(target.type)
  if (![0, 1, 2, 3, 4, 5, 6].includes(type)) throw Error('Invalid case node type')
  if ([0, 1, 4, 6].includes(type)) {
    if (target.page_step_details_data != null && !Array.isArray(target.page_step_details_data)) throw Error('Invalid case node parameters')
    target.page_step_details_data = (Array.isArray(target.page_step_details_data) ? target.page_step_details_data : []).map(value => {
      const param = uiCaseAssetObject(value)
      if (typeof param.f !== 'string') throw Error('Invalid case parameter name')
      const key = `${param.f}-ope_value`
      if (Object.prototype.hasOwnProperty.call(input, key)) param.v = cloneLosslessJson(input[key])
      else if (!['locating', 'actual'].includes(param.f) && Object.prototype.hasOwnProperty.call(input, param.f)) param.v = cloneLosslessJson(input[param.f])
      return param
    })
    if (input.condition_value !== undefined) target.condition_value = { expect: cloneLosslessJson(input.condition_value) }
  } else if (type === 2) {
    if (input.sql_execute != null && !Array.isArray(input.sql_execute)) throw Error('Invalid SQL parameters')
    target.page_step_details_data = cloneLosslessJson(input.sql_execute ?? [])
  } else if (type === 3) target.page_step_details_data = [{ key: input.key, value: cloneLosslessJson(input.value) }]
  else if (type === 5) target.page_step_details_data = [{ func: input.func }]
  return result
}
