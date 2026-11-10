
import { reportLoadError } from '@/utils/load-error'
import { reactive, watch, onBeforeUnmount, onDeactivated } from 'vue'
import { getExecutionEfficiencyOptions } from '@/api/system/execution_efficiency'
import { parseEfficiencyOptions, type EfficiencyId, type EfficiencyOption } from '../overview'
import type { TaskOptionKey } from '../config'

interface OptionState { loading: boolean; page: number; keyword: string; more: boolean; version: number; items: EfficiencyOption[]; error: string; retryPage: number; stale: boolean }
interface Options { available(): boolean; contextKey(): string; productId(): EfficiencyId | null }
export function useEfficiencyOptions(options: Options) {
  const initial = (): OptionState => ({ loading: false, page: 0, keyword: '', more: true, version: 0, items: [], error: '', retryPage: 1, stale: false })
  const state = reactive<Record<TaskOptionKey, OptionState>>({ task_ids: initial(), task_group_ids: initial() })
  const timers: Partial<Record<TaskOptionKey, ReturnType<typeof setTimeout>>> = {}
  const pending: Partial<Record<TaskOptionKey, { version: number; page: number; promise: Promise<void> }>> = {}
  let disposed = false
  const isTaskOption = (key: string): key is TaskOptionKey => key === 'task_ids' || key === 'task_group_ids'
  function clear(reset = true) {
    for (const key of ['task_ids', 'task_group_ids'] as const) {
      clearTimeout(timers[key]); delete timers[key]
      const version = state[key].version + 1
      if (reset) Object.assign(state[key], initial(), { version })
      else Object.assign(state[key], { version, loading: false, error: '', stale: true })
    }
  }
  function loadOptions(key: string, page = 1): Promise<void> {
    if (!isTaskOption(key) || disposed || !options.available()) return Promise.resolve()
    const target = state[key], scope = options.contextKey(), keyword = target.keyword, product = options.productId()
    if (pending[key]?.version === target.version && pending[key]?.page === page) return pending[key]!.promise
    const version = ++target.version
    target.loading = true; target.error = ''; target.retryPage = page
    const current = () => !disposed && options.available() && target.version === version && scope === options.contextKey()
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const response = await getExecutionEfficiencyOptions({ kind: key === 'task_ids' ? 'tasks' : 'groups', ...(product !== null ? { product_id: product } : {}), keyword, page, page_size: 50 })
        if (!current()) return
        const result = parseEfficiencyOptions(response)
        const items = page === 1 ? result.items : [...target.items, ...result.items]
        target.items = [...new Map(items.map(item => [String(item.value), item])).values()]
        target.page = page; target.more = result.more; target.stale = false
      } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "选项加载失败，请重试", false), target.error = '选项加载失败，请重试') }
      finally { if (target.version === version) target.loading = false; if (pending[key]?.version === version) delete pending[key] }
    })
    pending[key] = { version, page, promise }; return promise
  }
  function openOptions(key: string): Promise<void> {
    return isTaskOption(key) && (!state[key].page || state[key].stale || state[key].error) ? loadOptions(key, 1) : Promise.resolve()
  }
  function searchOptions(key: string, keyword: string) {
    if (!isTaskOption(key) || disposed || !options.available()) return
    const target = state[key]
    clearTimeout(timers[key]); target.version++; target.keyword = keyword; target.loading = true; target.more = false; target.error = ''; target.stale = true
    timers[key] = setTimeout(() => { delete timers[key]; void loadOptions(key) }, 250)
  }
  function moreOptions(key: string): Promise<void> {
    return isTaskOption(key) && !state[key].loading && !state[key].stale && state[key].more ? loadOptions(key, state[key].page + 1) : Promise.resolve()
  }
  function retryOptions(key: string): Promise<void> { return isTaskOption(key) ? loadOptions(key, state[key].retryPage) : Promise.resolve() }
  watch(options.contextKey, () => clear(), { flush: 'sync' })
  onDeactivated(() => clear(false))
  onBeforeUnmount(() => { disposed = true; clear() })
  return { state, isTaskOption, loadOptions, openOptions, searchOptions, moreOptions, retryOptions, clear }
}
