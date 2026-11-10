import type { NoticeProjectContext } from './types'
function projectId(value: unknown): number | null {
  if (typeof value !== 'number' && !(typeof value === 'string' && /^\d+$/.test(value))) return null
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
export function resolveNoticeProject(
  query: { id?: unknown; name?: unknown },
  record: unknown
): NoticeProjectContext {
  const stored = record && typeof record === 'object' ? record : null
  const storedId = stored && 'id' in stored ? projectId(stored.id) : null
  const id = query.id !== undefined ? projectId(query.id) : storedId
  if (id === null) return { id: null, name: '-' }
  const fallback =
    id === storedId && stored && 'name' in stored && typeof stored.name === 'string'
      ? stored.name
      : '-'
  return { id, name: typeof query.name === 'string' && query.name !== '' ? query.name : fallback }
}
