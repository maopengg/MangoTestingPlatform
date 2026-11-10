import type { IterationScheduleForm, IterationScheduleSubject } from './types'

export function createIterationScheduleForm(
  record?: IterationScheduleSubject
): IterationScheduleForm {
  const owner = record?.development_owner
  return {
    development_owner: typeof owner === 'number' ? owner : owner?.id ?? null,
    priority: record?.priority ?? null,
    planned_start_date: record?.planned_start_date || null,
    planned_submit_date: record?.planned_submit_date || null,
    status: record?.status ?? null,
  }
}

export function iterationSchedulePayload(
  id: number,
  iterationId: number,
  form: IterationScheduleForm
) {
  return {
    id,
    iteration_ref: iterationId,
    development_owner: form.development_owner ?? null,
    priority: form.priority ?? null,
    planned_start_date: form.planned_start_date || null,
    planned_submit_date: form.planned_submit_date || null,
    status: form.status,
  }
}
