import type { ManualCaseBinding } from '@/api/functional-test/types'

export function caseDetailId(value: unknown): number | null {
  if (typeof value !== 'string' || !/^\d+$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

export function enumTitle(
  options: ReadonlyArray<{ key: number | string; title: string }> = [],
  value: number | string | null | undefined
): string {
  if (value === null || value === undefined || value === '') return '-'
  return options.find((item) => String(item.key) === String(value))?.title ?? String(value)
}

export function bindingCaseId(binding: ManualCaseBinding): number {
  return binding.api_case ?? binding.ui_case ?? binding.automation_case_id
}
