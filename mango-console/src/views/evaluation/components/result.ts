export function resultObject(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}
export const resultArray = (value: unknown): unknown[] => (Array.isArray(value) ? value : [])
