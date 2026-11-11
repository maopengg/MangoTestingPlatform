export interface VariableTagSummary {
  total: number
  untagged: number
  items: Array<{ name: string; count: number }>
}
export type VariableTagReader = (query: Record<string, unknown>) => Promise<{ data: VariableTagSummary }>
export function variableTagFilter(tag: string | null): Record<string, unknown> {
  return tag === null ? {} : tag === '' ? { untagged: true } : { tag }
}
export function normalizeVariableTags(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return [...new Set(value.filter((tag): tag is string => typeof tag === 'string').map(tag => tag.trim()).filter(Boolean))]
}
export const variableTagOperations = [
  { value: 0, label: '添加标签' }, { value: 1, label: '移除标签' }, { value: 2, label: '替换标签' },
]
