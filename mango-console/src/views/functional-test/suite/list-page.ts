import { normalizeEmptyListTotal } from '@/utils/api-response'
export function readListPage(value: unknown) {
  value = normalizeEmptyListTotal(value)

  if (!value || typeof value !== 'object') throw Error('Invalid list response')
  const response = value as { data?: unknown; totalSize?: unknown }
  if (
    !Array.isArray(response.data) ||
    typeof response.totalSize !== 'number' ||
    !Number.isSafeInteger(response.totalSize) ||
    response.totalSize < 0
  )
    throw Error('Invalid list page')
  const rows = response.data.map((value: unknown) => {
    if (!value || typeof value !== 'object' || Array.isArray(value))
      throw Error('Invalid list record')
    const row = value as Record<string, unknown>
    if (typeof row.id !== 'number' || !Number.isSafeInteger(row.id) || row.id <= 0)
      throw Error('Invalid list ID')
    return row
  })
  return { rows, total: response.totalSize }
}
