export function reportRecords(value: unknown): Record<string, any>[] {
  return Array.isArray(value)
    ? value.filter((row) => row !== null && typeof row === 'object' && !Array.isArray(row))
    : []
}

export function caseResultRows(item: Record<string, any>): Record<string, any>[] {
  const children = reportRecords(item.children)
  return children.length ? children : [item]
}
