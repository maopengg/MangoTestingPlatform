import type { Ref } from 'vue'
import { reportLoadError } from '@/utils/load-error'

interface ReadOptions<T> {
  key: string
  silent: boolean
  loading: Ref<boolean>
  error: Ref<string>
  message: string
  read(): Promise<T>
  apply(value: T): void
  isCurrent?(): boolean
}

// 每个独立面板各持有一个会话；失效只放弃旧响应，不冒充物理请求已取消。
export function createReportReadSession(available: () => boolean) {
  let version = 0
  let pending: { key: string; version: number; promise: Promise<void>; isCurrent(): boolean; promote(): void } | null = null
  let activeLoading: Ref<boolean> | null = null
  function invalidate() {
    version += 1
    if (activeLoading) activeLoading.value = false
    activeLoading = null
  }
  function run<T>(options: ReadOptions<T>): Promise<void> {
    if (!available()) return Promise.resolve()
    if (pending?.key === options.key && pending.version === version && pending.isCurrent()) {
      if (!options.silent) pending.promote()
      return pending.promise
    }
    invalidate()
    const currentVersion = version
    const current = () => available() && currentVersion === version && (options.isCurrent?.() ?? true)
    if (!options.silent) options.error.value = ''
    activeLoading = options.loading
    if (!options.silent) options.loading.value = true
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const result = await options.read()
        if (current()) { options.apply(result); options.error.value = '' }
      } catch (error: unknown) {
        if (!current()) return
        if (options.silent) throw error
        options.error.value = options.message
        reportLoadError(error, options.message, options.silent)
      } finally {
        if (currentVersion === version) {
          options.loading.value = false
          activeLoading = null
        }
        if (pending?.version === currentVersion) pending = null
      }
    })
    pending = { key: options.key, version: currentVersion, promise, isCurrent: current, promote() {
      options.silent = false
      activeLoading = options.loading
      options.loading.value = true
    } }
    return promise
  }
  return { run, invalidate }
}
