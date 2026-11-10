import { effectScope, toRaw, watch } from 'vue'
import useUserStore from '@/store/modules/user'
import type { Response } from '@/api/http'

const CACHE_TTL = 5 * 60 * 1000
type Entry = { response: Response; expiresAt: number }

export function createDirectoryCache(cacheable: (response: Response) => boolean, now = Date.now) {
  const entries = new Map<string, Entry>()
  const pending = new Map<string, Promise<Response>>()
  let version = 0
  return {
    expiresAt: (key: string) => entries.get(key)?.expiresAt ?? 0,
    invalidate() { version++; entries.clear(); pending.clear() },
    async read(key: string, fetch: () => Promise<Response>, force = false): Promise<Response> {
      const generation = version
      const running = pending.get(key)
      if (running) {
        const response = await running
        if (generation !== version) throw new Error('选项目录已失效，请重新加载')
        return structuredClone(response)
      }
      const entry = entries.get(key)
      if (!force && entry && entry.expiresAt > now()) return structuredClone(entry.response)
      entries.delete(key)
      const request = Promise.resolve().then(fetch).then(response => {
        if (generation === version && cacheable(response)) {
          entries.set(key, { response: structuredClone(response), expiresAt: now() + CACHE_TTL })
        }
        return response
      }).finally(() => { if (pending.get(key) === request) pending.delete(key) })
      pending.set(key, request)
      const response = await request
      if (generation !== version) throw new Error('选项目录已失效，请重新加载')
      return structuredClone(response)
    },
  }
}

export function createScopedDirectoryCache(cacheable: (response: Response) => boolean) {
  type OwnerCache = { identity: string; cache: ReturnType<typeof createDirectoryCache> }
  const owners = new WeakMap<object, OwnerCache>()
  function ownerCache() {
    const user = useUserStore(), owner = toRaw(user)
    const identity = () => JSON.stringify([user.userId, user.roleId, user.token, user.selected_environment])
    let entry = owners.get(owner)
    if (!entry) {
      entry = { identity: identity(), cache: createDirectoryCache(cacheable) }
      owners.set(owner, entry)
      const observed = entry, scope = effectScope(true)
      scope.run(() => watch(identity, value => {
        if (observed.identity !== value) { observed.cache.invalidate(); observed.identity = value }
      }, { flush: 'sync' }))
      const dispose = user.$dispose.bind(user)
      user.$dispose = () => { observed.cache.invalidate(); scope.stop(); owners.delete(owner); dispose() }
    }
    if (entry.identity !== identity()) { entry.cache.invalidate(); entry.identity = identity() }
    return entry.cache
  }
  return {
    read: (key: string, fetch: () => Promise<Response>, force = false) => ownerCache().read(key, fetch, force),
    invalidate: () => ownerCache().invalidate(),
    expiresAt: (key: string) => ownerCache().expiresAt(key),
  }
}
