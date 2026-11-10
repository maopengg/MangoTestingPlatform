
import { reportLoadError } from '@/utils/load-error'
import { ref, shallowRef } from 'vue'

export function useIterationRegion<T>(
  initial: () => T,
  read: () => Promise<T>,
  context: () => number,
  active: () => boolean
) {
  const data = shallowRef<T>(initial())
  const loading = ref(false),
    error = ref(false)
  let sequence = 0
  function invalidate(clear = false) {
    ++sequence
    loading.value = false
    if (clear) {
      data.value = initial()
      error.value = false
    }
  }
  async function load() {
    if (!active()) return false
    const version = ++sequence,
      scope = context()
    const current = () => active() && sequence === version && context() === scope
    loading.value = true
    error.value = false
    try {
      const result = await read()
      if (!current()) return false
      data.value = result
      return true
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), error.value = true)
      return false
    } finally {
      if (current()) loading.value = false
    }
  }
  return { data, loading, error, load, invalidate }
}
