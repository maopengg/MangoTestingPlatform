import type { Ref } from 'vue'
import { reportLoadError, runLoadRequest } from '@/utils/load-error'

/** A query owns one region; invalidation abandons responses, not the physical HTTP request. */
export function createReportQuery(available: () => boolean, context: () => string) {
  let version = 0
  let pending: { key: string; version: number; promise: Promise<boolean>; promote(): void } | null = null
  let loading: Ref<boolean> | null = null
  function invalidate() {
    version++
    if (loading) loading.value = false
    loading = null
    pending = null
  }
  function run<T>(options: {
    key: string; silent?: boolean; loading: Ref<boolean>; error: Ref<string>; message: string
    read(): Promise<T>; apply(value: T): void; fail?(): void
  }): Promise<boolean> {
    if (!available()) return Promise.resolve(false)
    const identity = context(), key = JSON.stringify([identity, options.key])
    if (pending?.key === key && pending.version === version) {
      if (!options.silent) pending.promote()
      return pending.promise
    }
    invalidate()
    const currentVersion = version
    const current = () => available() && currentVersion === version && identity === context()
    let silent = Boolean(options.silent)
    const promote = () => { silent = false; loading = options.loading; options.loading.value = true }
    if (!silent) { options.error.value = ''; promote() }
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return false
        const result = await runLoadRequest(silent, () => options.read())
        if (!current()) return false
        options.apply(result); options.error.value = ''
        return true
      } catch (error) {
        if (current()) { options.error.value = options.message; reportLoadError(error, options.message, silent); if (!silent) options.fail?.() }
        return false
      } finally {
        if (currentVersion === version) { options.loading.value = false; loading = null; pending = null }
      }
    })
    pending = { key, version: currentVersion, promise, promote }
    return promise
  }
  return { run, invalidate }
}
