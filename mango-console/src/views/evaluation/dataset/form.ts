import type { DatasetFilters, DatasetForm, EvaluationDatasetRecord } from './types'

export function normalizeLabels(value: unknown): string[] {
  const values = Array.isArray(value) ? value : typeof value === 'string' ? [value] : []
  return [
    ...new Set(
      values
        .filter((entry): entry is string => typeof entry === 'string')
        .flatMap((entry) => entry.split(/[,，\n]/))
        .map((entry) => entry.trim())
        .filter(Boolean)
    ),
  ]
}

export function createDatasetFilters(): DatasetFilters {
  return { name: '', task_type: [], status: [] }
}

export function createDatasetForm(record?: EvaluationDatasetRecord): DatasetForm {
  return {
    id: record?.id ?? null,
    name: record?.name ?? '',
    description: record?.description ?? '',
    task_type: normalizeLabels(record?.task_type),
    status: record?.status ?? 'draft',
  }
}

export function datasetQuery(filters: DatasetFilters, page: number, pageSize: number) {
  const query: Record<string, string | number> = { page, pageSize }
  const labels = normalizeLabels(filters.task_type)
  if (filters.name) query.name = filters.name
  if (labels.length) query.task_types = JSON.stringify(labels)
  if (filters.status.length) query.status__in = filters.status.join(',')
  return query
}

export function datasetPayload(form: DatasetForm) {
  const payload = {
    id: form.id ?? undefined,
    name: form.name,
    description: form.description,
    task_type: normalizeLabels(form.task_type),
  }
  return form.id === null ? payload : { ...payload, status: form.status }
}

export function restoredDatasetStatus(record: EvaluationDatasetRecord) {
  return record.status === 'archived' ? (record.current_version ? 'enabled' : 'draft') : 'archived'
}
