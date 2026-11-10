import type { Response } from '@/api/http'
import { createScopedDirectoryCache } from '@/utils/scoped-directory-cache'

const directory = createScopedDirectoryCache(response => response?.code === 200 &&
  Array.isArray(response.data) && response.data.every(row => row && typeof row === 'object' &&
    ((typeof row.key === 'number' && Number.isFinite(row.key)) || (typeof row.key === 'string' && row.key.length > 0)) &&
    typeof row.title === 'string'))

export function readUserNames(fetch: () => Promise<Response>, force = false) {
  return directory.read('user-names', fetch, force)
}
export function invalidateUserNames() { directory.invalidate() }
