
import { reportLoadError } from '@/utils/load-error'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'

/** 首页独立只读面板的请求上下文；分页、图表和窗口状态仍归各自组件。 */
export function useHomeSnapshot<T>(options: {
  read: () => Promise<unknown>
  parse: (value: unknown) => T
  empty: () => T
  onInvalidate?: () => void
}) {
  const route = useRoute(), user = useUserStore(), entryPath = route.path
  const context = computed(() => JSON.stringify([
    route.fullPath, user.userId, user.roleId, user.token, user.selected_environment,
  ]))
  const snapshot = shallowRef<T>(options.empty())
  const loading = ref(false), loadFailed = ref(false)
  let active = true, mounted = false, sequence = 0
  const isAvailable = () => active && route.path === entryPath

  function invalidate() {
    sequence++
    loading.value = false
    options.onInvalidate?.()
  }
  async function reload() {
    if (!isAvailable()) return
    const request = ++sequence, identity = context.value
    const current = () => isAvailable() && request === sequence && identity === context.value
    loading.value = true
    loadFailed.value = false
    try {
      const value = options.parse(await options.read())
      if (current()) snapshot.value = value
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true)
    } finally {
      if (current()) loading.value = false
    }
  }
  watch(context, () => {
    invalidate()
    snapshot.value = options.empty()
    loadFailed.value = false
    if (mounted) void reload()
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; void reload() })
  onDeactivated(() => { active = false; invalidate() })
  onActivated(() => {
    if (mounted && !active) { active = true; void reload() }
  })
  onBeforeUnmount(() => { active = false; mounted = false; invalidate() })
  return { snapshot, loading, loadFailed, reload, isAvailable }
}
