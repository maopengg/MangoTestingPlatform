import { iterationObject, iterationRecordId, parseIterationDetail } from './presentation'
import type { IterationForm, IterationRow } from './types'

export function iterationSelectionId(value: unknown): number | null {
  const leaf = Array.isArray(value) ? value[value.length - 1] : value
  if (typeof leaf !== 'string' && typeof leaf !== 'number') return null
  if (typeof leaf === 'string' && !/^\d+$/.test(leaf)) return null
  const id = Number(leaf)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
const text = (value: unknown) => (typeof value === 'string' ? value : '')
const numeric = (value: unknown) =>
  typeof value === 'number' && Number.isFinite(value) ? value : 0
export function parseIterationRow(value: unknown): IterationRow {
  const row = iterationObject(value)
  const product = row.project_product ? iterationObject(row.project_product) : null
  const project = product?.project ? iterationObject(product.project) : null
  const metrics = row.test_metrics ? iterationObject(row.test_metrics) : {}
  return {
    ...parseIterationDetail(row),
    iteration_no: text(row.iteration_no),
    project_product: product
      ? {
          id: iterationRecordId(product.id),
          name: text(product.name),
          project: project ? { id: iterationRecordId(project.id), name: text(project.name) } : null,
        }
      : null,
    remark: text(row.remark),
    requirement_count: numeric(row.requirement_count),
    plan_count: numeric(row.plan_count),
    open_defect_count: numeric(row.open_defect_count),
    update_time: text(row.update_time),
    test_metrics: {
      total: numeric(metrics.total),
      executed: numeric(metrics.executed),
      progress: numeric(metrics.progress),
      pass_rate: numeric(metrics.pass_rate),
    },
  }
}
export function createIterationForm(
  record: IterationRow | null = null,
  productId: number | null = null
): IterationForm {
  return {
    iteration_no: record?.iteration_no ?? '',
    name: record?.name ?? '',
    project_product: record?.project_product?.id ?? productId,
    owner: record?.owner?.id ?? null,
    start_date: record?.start_date ?? null,
    end_date: record?.end_date ?? null,
    status: record?.status ?? 0,
    remark: record?.remark ?? '',
  }
}
export function iterationSavePayload(form: IterationForm, id: number | null) {
  return {
    ...(id === null ? {} : { id }),
    iteration_no: form.iteration_no.trim(),
    name: form.name.trim(),
    project_product: iterationSelectionId(form.project_product),
    owner: iterationSelectionId(form.owner),
    start_date: form.start_date || null,
    end_date: form.end_date || null,
    status: form.status === null || form.status === '' ? null : Number(form.status),
    remark: form.remark,
  }
}
