import { requiredUiCaseAssetId, uiCaseAssetObject, uiCaseAssetResponse, type UiCaseAssetId } from '@/components/business/ui-case-step-create'

const statuses = ['waiting_executor', 'pending', 'claimed', 'running', 'success', 'failed', 'interrupted', 'cancelled', 'timeout'] as const
export interface CaseExecutionTask {
  taskId: UiCaseAssetId; status: typeof statuses[number]; terminal: boolean; error: string; result: unknown
}
export interface CaseExecutionSubmission { taskId: UiCaseAssetId; executionId: string; message: string }
export interface CaseExecutionObservation { taskId: UiCaseAssetId; executionId: string; legacy: boolean }
export interface CaseExecutionLaunch { actuatorUsername?: string; withLive: boolean }
export const caseExecutionScope = (owner: string) => `ui-case-run:${encodeURIComponent(owner)}`
function taskId(value: unknown): UiCaseAssetId {
  if (typeof value !== 'number' && typeof value !== 'string') throw Error('Invalid case task ID')
  const id = requiredUiCaseAssetId(value)
  if (!/[1-9]/.test(String(id))) throw Error('Invalid case task ID')
  return id
}
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid case execution text'); return value }
export function readCaseExecutionSubmission(response: unknown, caseId: UiCaseAssetId, environment: UiCaseAssetId): CaseExecutionSubmission {
  const row = uiCaseAssetObject(uiCaseAssetResponse(response)), executionId = text(row.execution_id)
  if (!executionId || String(requiredUiCaseAssetId(row.id)) !== String(caseId) || String(requiredUiCaseAssetId(row.test_env)) !== String(environment)) throw Error('Unexpected case submission')
  return { taskId: taskId(row.task_id), executionId, message: text(uiCaseAssetObject(response).msg) }
}
export function readCaseExecutionTask(response: unknown, caseId: UiCaseAssetId, expectedTaskId?: UiCaseAssetId): CaseExecutionTask {
  const row = uiCaseAssetObject(uiCaseAssetResponse(response)), id = taskId(row.task_id), status = statuses.find(value => value === row.status)
  const terminal = status !== undefined && ['success', 'failed', 'interrupted', 'cancelled', 'timeout'].includes(status)
  if (!status || terminal !== row.terminal || row.task_type !== 'ui_case' || row.business_type !== 'u_case' || String(requiredUiCaseAssetId(row.business_id)) !== String(caseId) || (expectedTaskId !== undefined && String(id) !== String(expectedTaskId))) throw Error('Unexpected case task')
  return { taskId: id, status, terminal, error: text(row.error_message), result: row.result }
}
export function readActiveCaseExecutionTasks(response: unknown, caseId: UiCaseAssetId): CaseExecutionTask[] {
  const data = uiCaseAssetResponse(response)
  if (!Array.isArray(data)) throw Error('Invalid case task list')
  return data.map(value => readCaseExecutionTask({ code: 200, data: value }, caseId))
}
export function readCaseExecutionObservation(value: unknown, caseId: UiCaseAssetId, environment: UiCaseAssetId, owner: string, legacy: boolean): CaseExecutionObservation | null {
  if (value == null) return null
  const row = uiCaseAssetObject(value)
  if (String(requiredUiCaseAssetId(row.businessId)) !== String(caseId) || row.businessType !== 'u_case') throw Error('Unexpected case observation')
  if (!legacy && (row.owner !== owner || String(requiredUiCaseAssetId(row.environment)) !== String(environment) || !text(row.executionId))) throw Error('Unexpected case observation owner')
  return { taskId: taskId(row.taskId), executionId: legacy ? '' : text(row.executionId), legacy }
}
