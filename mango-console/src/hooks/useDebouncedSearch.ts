import { onActivated, onBeforeUnmount, onDeactivated, onMounted, onScopeDispose, watch } from 'vue'
import { reportLoadError } from '@/utils/load-error'

/** 自动搜索合并连续交互；手动查询立即执行，并取消尚未发出的自动查询。 */
export function useDebouncedSearch<T>(
  search: () => T,
  snapshot: () => unknown,
  options: { enabled?: () => boolean } = {}
) {
  let timer: ReturnType<typeof setTimeout> | undefined
  let active = true
  let attached = false
  let appliedKey = JSON.stringify(snapshot())
  let pendingKey: string | undefined
  const available = () => active && options.enabled?.() !== false &&
    (typeof document === 'undefined' || document.visibilityState !== 'hidden')

  function cancel() {
    if (timer !== undefined) clearTimeout(timer)
    timer = undefined
    pendingKey = undefined
  }
  function run(): T | undefined {
    cancel()
    if (!available()) return
    appliedKey = JSON.stringify(snapshot())
    return search()
  }
  function sync() { cancel(); appliedKey = JSON.stringify(snapshot()) }
  function schedule() {
    if (!available()) { cancel(); return }
    const key = JSON.stringify(snapshot())
    if (key === appliedKey) { cancel(); return }
    if (timer !== undefined && pendingKey === key) return
    cancel()
    pendingKey = key
    timer = setTimeout(() => {
      timer = undefined
      pendingKey = undefined
      if (available() && JSON.stringify(snapshot()) === key) {
        try { Promise.resolve(run()).catch(error => reportLoadError(error, '搜索失败，请重试')) }
        catch (error) { reportLoadError(error, '搜索失败，请重试') }
      }
    }, 500)
  }
  function pause() {
    active = false
    cancel()
    if (attached && typeof document !== 'undefined') document.removeEventListener?.('visibilitychange', visibilityChanged)
    attached = false
  }
  function visibilityChanged() { if (!available()) cancel() }
  function attach() {
    if (!attached && typeof document !== 'undefined') {
      document.addEventListener?.('visibilitychange', visibilityChanged)
      attached = true
    }
  }
  if (options.enabled) watch(options.enabled, () => sync(), { flush: 'sync' })
  onMounted(attach)
  onActivated(() => { active = true; attach(); sync() })
  onDeactivated(pause)
  onBeforeUnmount(pause)
  onScopeDispose(pause)
  return { schedule, run, cancel, sync }
}
