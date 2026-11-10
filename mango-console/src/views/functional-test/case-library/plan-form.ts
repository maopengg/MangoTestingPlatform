import { emptyPlan } from '../plan/config'
import { caseProductId } from './form'
import type { LibraryPlanForm } from './types'

export function createLibraryPlanForm(): LibraryPlanForm {
  const { id, ...defaults } = emptyPlan()
  return {
    ...defaults,
    project_product: null,
    owner: null,
    requirement_version: null,
    iteration: null,
    planned_start_time: null,
    planned_end_time: null,
  }
}

export function libraryPlanPayload(form: LibraryPlanForm) {
  return {
    name: form.name,
    project_product: caseProductId(form.project_product),
    scope_type: form.scope_type,
    requirement_version: form.scope_type === 0 ? form.requirement_version : null,
    iteration: form.scope_type === 1 ? form.iteration : null,
    scope_ref: form.scope_ref,
    environment: form.environment,
    build_version: form.build_version,
    owner: form.owner,
    planned_start_time: form.planned_start_time,
    planned_end_time: form.planned_end_time,
    status: form.status,
    remark: form.remark,
  }
}
