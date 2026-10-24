export interface ExecutorTaskObservation {
  taskId: string | number
  businessType?: string
  businessId?: string | number
  meta?: Record<string, any>
  savedAt?: number
}

export function saveExecutorTaskObservation(
  scope: string,
  businessId: string | number,
  observation: ExecutorTaskObservation
): boolean
export function loadExecutorTaskObservation(
  scope: string,
  businessId: string | number
): ExecutorTaskObservation | null
export function clearExecutorTaskObservation(
  scope: string,
  businessId: string | number,
  taskId?: string | number
): void
