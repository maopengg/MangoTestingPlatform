export interface TaskFineTuning {
  api_concurrency_limit: number | null
  case_people: number | null
  report_retention_policy: string
}
export function readFineTuning(record: Record<string, any>): TaskFineTuning {
  return {
    api_concurrency_limit: record.api_concurrency_limit ?? null,
    case_people: record.case_people?.id ?? record.case_people ?? null,
    report_retention_policy: record.report_retention_policy || 'all',
  }
}
export function fineTuningPatch(original: TaskFineTuning, current: TaskFineTuning): Partial<TaskFineTuning> {
  const normalized = readFineTuning(current)
  return Object.fromEntries(Object.entries(normalized).filter(([key, value]) =>
    JSON.stringify(value) !== JSON.stringify(original[key as keyof TaskFineTuning])))
}
