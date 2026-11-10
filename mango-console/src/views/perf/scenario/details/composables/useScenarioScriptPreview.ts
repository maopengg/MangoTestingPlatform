import { nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { getPerfScenarioScriptPreview } from '@/api/perf'
import { readScenarioScriptPreview } from '../script-preview'
import type { ScenarioScriptPreview, ScriptPreviewTab } from '../types'

export function useScenarioScriptPreview(options: {
  scenarioId: () => string
  contextVersion: () => number
  isContextCurrent: (version: number) => boolean
}) {
  const visible = ref(false), loading = ref(false), copying = ref(false), error = ref(false)
  const activeTab = ref<ScriptPreviewTab>('script')
  const preview = ref<ScenarioScriptPreview | null>(null)
  let epoch = 0, tabEpoch = 0, active = true, disposed = false
  let pendingRead: { epoch: number; promise: Promise<boolean> } | null = null
  const available = () => !disposed && active && (typeof document === 'undefined' || document.visibilityState !== 'hidden')

  function capture() {
    const id = options.scenarioId(), version = options.contextVersion(), current = epoch
    if (!available() || !visible.value || !/^\d+$/.test(id) || !Number.isSafeInteger(Number(id)) ||
      Number(id) < 1 || !options.isContextCurrent(version)) return null
    return {
      id, epoch: current,
      isCurrent: () => available() && visible.value && current === epoch && id === options.scenarioId() &&
        version === options.contextVersion() && options.isContextCurrent(version),
    }
  }

  function close(): void {
    epoch++
    visible.value = false
    preview.value = null
    loading.value = false
    error.value = false
  }

  function reload(): Promise<boolean> {
    const context = capture()
    if (!context) return Promise.resolve(false)
    if (pendingRead?.epoch === context.epoch) return pendingRead.promise
    const request = { epoch: context.epoch, promise: Promise.resolve(false) }
    pendingRead = request
    loading.value = true
    error.value = false
    preview.value = null
    request.promise = (async () => {
      try {
        const response = await getPerfScenarioScriptPreview(context.id)
        if (!context.isCurrent()) return false
        preview.value = readScenarioScriptPreview(response, context.id)
        await nextTick()
        return context.isCurrent()
      } catch {
        if (context.isCurrent()) error.value = true
        return false
      } finally {
        if (context.isCurrent()) loading.value = false
        if (pendingRead === request) pendingRead = null
      }
    })()
    return request.promise
  }

  function open(): Promise<boolean> {
    if (!available() || !options.isContextCurrent(options.contextVersion())) return Promise.resolve(false)
    const id = options.scenarioId()
    if (!/^\d+$/.test(id) || !Number.isSafeInteger(Number(id)) || Number(id) < 1) return Promise.resolve(false)
    if (visible.value && loading.value) return reload()
    close()
    visible.value = true
    activeTab.value = 'script'
    return reload()
  }

  async function copy(): Promise<boolean> {
    const context = capture(), snapshot = preview.value, tab = activeTab.value, revision = tabEpoch
    if (!context || !snapshot || copying.value || loading.value) return false
    const current = () => context.isCurrent() && snapshot === preview.value && revision === tabEpoch
    copying.value = true
    try {
      if (typeof navigator === 'undefined' || !navigator.clipboard?.writeText) {
        if (current()) Message.error('当前浏览器无法复制，请手动复制')
        return false
      }
      await navigator.clipboard.writeText(tab === 'snapshot' ? snapshot.snapshot : snapshot.script)
      if (!current()) return false
      Message.success('已复制预览内容')
      return true
    } catch {
      if (current()) Message.error('复制失败，请重试')
      return false
    } finally {
      copying.value = false
    }
  }

  function onVisibleChange(value: boolean): void { if (!value) close() }
  function visibilityChanged(): void { if (document.visibilityState === 'hidden') close() }
  watch(activeTab, () => { tabEpoch++ }, { flush: 'sync' })
  watch(() => [options.scenarioId(), options.contextVersion()], close, { flush: 'sync' })
  onMounted(() => { if (typeof document !== 'undefined') document.addEventListener('visibilitychange', visibilityChanged) })
  onDeactivated(() => { active = false; close() })
  onActivated(() => { active = true })
  onBeforeUnmount(() => {
    disposed = true
    active = false
    close()
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', visibilityChanged)
  })
  return { visible, loading, copying, error, preview, activeTab, open, close, reload, copy, onVisibleChange }
}
