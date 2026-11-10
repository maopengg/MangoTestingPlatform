import type { Response } from '@/api/http'
import { createDirectoryCache, createScopedDirectoryCache } from '@/utils/scoped-directory-cache'

function cacheable(response: Response) {
  const nodes = (rows: unknown): boolean => Array.isArray(rows) && rows.every(row => row &&
    typeof row === 'object' && !Array.isArray(row) &&
    ((typeof row.key === 'number' && Number.isFinite(row.key)) || (typeof row.key === 'string' && row.key.length > 0)) &&
    typeof row.title === 'string' && (row.disabled === undefined || typeof row.disabled === 'boolean') &&
    (row.children === undefined || nodes(row.children)))
  return response?.code === 200 && nodes(response.data)
}

export function createModuleDirectoryCache(now = Date.now) { return createDirectoryCache(cacheable, now) }
const directory = createScopedDirectoryCache(cacheable)

function directoryKey(kind: 'tree' | 'name', product: unknown) {
  const leaf = Array.isArray(product) ? product[product.length - 1] : product
  return `${kind}:${leaf == null || leaf === '' ? '__all__' : String(leaf)}`
}

export function readModuleDirectory(kind: 'tree' | 'name', product: unknown, fetch: () => Promise<Response>, force = false) {
  return directory.read(directoryKey(kind, product), fetch, force)
}
export function moduleDirectoryExpiresAt(kind: 'tree' | 'name', product?: unknown) {
  return directory.expiresAt(directoryKey(kind, product))
}
export function invalidateModuleDirectoryCache() { directory.invalidate() }
