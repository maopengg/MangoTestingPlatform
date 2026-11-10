import { requiredUiAuthId, uiAuthObject, uiAuthResponse, type UiAuthId } from './auth-editor-records'

export type UiAuthTaskAction = 'start' | 'capture'
export const authTaskBusiness = (action: UiAuthTaskAction) => action === 'start' ? 'u_auth_auto' : 'u_auth_auto_capture'
export const authTaskScope = (action: UiAuthTaskAction, owner: string) => `ui-auth-${action}:${encodeURIComponent(owner)}`
export const authTaskTimeout = (action: UiAuthTaskAction) => (action === 'start' ? 2 : 15) * 60 * 1000
const statuses = ['waiting_executor', 'pending', 'claimed', 'running', 'success', 'failed', 'interrupted', 'cancelled', 'timeout'] as const
type TaskStatus = typeof statuses[number]
export interface UiAuthTaskState { taskId: UiAuthId; status: TaskStatus; terminal: boolean }
export interface UiAuthObservation { taskId: UiAuthId; legacy: boolean }
export function positiveAuthTaskId(value: unknown): UiAuthId {
  if (typeof value !== 'number' && typeof value !== 'string') throw Error('Invalid authorization task ID')
  const id = requiredUiAuthId(value)
  if (!/[1-9]/.test(String(id))) throw Error('Invalid authorization task ID')
  return id
}
export function readAuthSubmission(response: unknown): UiAuthId {
  return positiveAuthTaskId(uiAuthObject(uiAuthResponse(response)).task_id)
}
export function readAuthTask(response: unknown, taskId: UiAuthId, recordId: UiAuthId, action: UiAuthTaskAction): UiAuthTaskState {
  const row = uiAuthObject(uiAuthResponse(response)), id = positiveAuthTaskId(row.task_id)
  const status = statuses.find(status => status === row.status)
  const terminal = status !== undefined && ['success', 'failed', 'interrupted', 'cancelled', 'timeout'].includes(status)
  if (!status || row.terminal !== terminal || String(id) !== String(taskId) || String(requiredUiAuthId(row.business_id)) !== String(recordId) || row.business_type !== authTaskBusiness(action) || row.task_type !== (action === 'start' ? 'auth_start' : 'auth_capture')) throw Error('Unexpected authorization task')
  return { taskId: id, status, terminal }
}
export function readAuthObservation(value: unknown, recordId: UiAuthId, action: UiAuthTaskAction, owner: string, legacy: boolean): UiAuthObservation | null {
  if (value == null) return null
  const row = uiAuthObject(value)
  if (String(requiredUiAuthId(row.businessId)) !== String(recordId) || row.businessType !== authTaskBusiness(action) || (!legacy && row.owner !== owner)) throw Error('Unexpected authorization observation')
  return { taskId: positiveAuthTaskId(row.taskId), legacy }
}
