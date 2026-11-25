export function formatCaseResultTime(value?: string | null): string {
  if (!value) return ''
  const parts = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/.exec(value)
  return parts ? `${parts[1]} ${parts[2]}` : value
}
