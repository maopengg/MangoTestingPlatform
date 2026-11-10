import { ref, shallowRef } from 'vue'
import { reportLoadError, runLoadRequest } from '@/utils/load-error'
import type { PollingContext } from '@/hooks/use-page-polling'

interface ResultRegionOptions<T> {
  runId: () => string | null
  initial: () => T
  request: (id: string) => Promise<unknown>
  read: (response: unknown, id: string) => T
  failureMessage: string
}

export function useRunResultRegion<T>(options: ResultRegionOptions<T>) {
  const data = shallowRef<T>(options.initial())
  const loading = ref(false)
  const error = ref('')
  const hasLoaded = ref(false)
  let version = 0
  let disposed = false
  let pending: { isCurrent: () => boolean; promise: Promise<boolean> } | null = null

  function load(silent = false, context?: PollingContext): Promise<boolean> {
    const id = options.runId()
    if (disposed || !id || (context && !context.isCurrent())) return Promise.resolve(false)
    if (pending?.isCurrent()) {
      if (!silent) loading.value = true
      return pending.promise
    }
    const snapshot = version
    const isCurrent = () => !disposed && snapshot === version && options.runId() === id && (!context || context.isCurrent())
    const job = { isCurrent, promise: Promise.resolve(false) }
    pending = job
    if (!silent) loading.value = true
    job.promise = Promise.resolve().then(async () => {
      try {
        if (!isCurrent()) return false
        const response = await runLoadRequest(silent, () => options.request(id))
        if (!isCurrent()) return false
        const result = options.read(response, id)
        data.value = result
        hasLoaded.value = true
        error.value = ''
        return true
      } catch (cause) {
        if (isCurrent()) {
          error.value = options.failureMessage
          reportLoadError(cause, options.failureMessage, silent)
        }
        throw cause
      } finally {
        if (pending === job) {
          pending = null
          loading.value = false
        }
      }
    })
    return job.promise
  }

  function invalidate() {
    version++
    pending = null
    loading.value = false
  }
  function reset() {
    invalidate()
    data.value = options.initial()
    error.value = ''
    hasLoaded.value = false
  }

  function dispose() { disposed = true; reset() }

  return { data, loading, error, hasLoaded, load, invalidate, reset, dispose }
}
