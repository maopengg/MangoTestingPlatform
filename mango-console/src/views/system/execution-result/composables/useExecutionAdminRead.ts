import { reportLoadError } from '@/utils/load-error'
import { ref } from 'vue'
import { useLatestRequest } from '@/hooks/use-latest-request'

/** One independent read region, with an owner-provided identity and query snapshot. */
export function useExecutionAdminRead<T>(options: {
  available(): boolean
  context(): string
  read(): Promise<T>
  apply(value: T): void
  clear(): void
  message: string
}) {
  const loading = ref(false), error = ref(''), requests = useLatestRequest()
  let pending: { key: string; promise: Promise<void> } | null = null
  function invalidate() { requests.invalidateRequests(); pending = null; loading.value = false }
  function run(): Promise<void> {
    if (!options.available()) return Promise.resolve()
    const key = options.context()
    if (pending?.key === key) return pending.promise
    const request = requests.beginRequest()
    const current = () => options.available() && requests.isLatestRequest(request) && key === options.context()
    loading.value = true; error.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const result = await options.read()
        if (current()) options.apply(result)
      } catch (failure) {
        if (current()) { options.clear(); error.value = options.message; reportLoadError(failure, options.message) }
      } finally {
        if (requests.isLatestRequest(request)) { loading.value = false; pending = null }
      }
    })
    pending = { key, promise }
    return promise
  }
  return { loading, error, run, invalidate }
}
