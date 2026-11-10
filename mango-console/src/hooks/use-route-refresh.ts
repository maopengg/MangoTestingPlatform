import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { isNavigationFailure, useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'

interface RefreshRequest {
  version: number
  target: { path: string; query: LocationQueryRaw; hash: string }
  promise: Promise<void>
  resolve: () => void
}

export function useRouteRefresh() {
  const route = useRoute(),
    router = useRouter(),
    user = useUserStore()
  const loading = ref(false)
  let version = 0,
    active = true,
    disposed = false
  let timer: ReturnType<typeof setTimeout> | undefined
  let queued: RefreshRequest | null = null,
    running: Promise<void> | null = null
  const available = () =>
    !disposed && active && (typeof document === 'undefined' || !document.hidden)
  function invalidate(): void {
    version++
    if (timer !== undefined) clearTimeout(timer)
    timer = undefined
    queued?.resolve()
    queued = null
    if (!running) loading.value = false
  }
  async function run(): Promise<void> {
    const task = queued
    timer = undefined
    queued = null
    if (!task) return
    running = task.promise
    const current = () => available() && task.version === version
    try {
      if (!current()) return
      const failure = await router.replace(task.target)
      if (failure && isNavigationFailure(failure) && current())
        Message.error('页面刷新失败，请重试')
    } catch {
      if (current()) Message.error('页面刷新失败，请重试')
    } finally {
      running = null
      loading.value = false
      task.resolve()
    }
  }
  function refresh(): Promise<void> {
    if (!available() || route.path === '/redirect' || route.path.startsWith('/redirect/'))
      return Promise.resolve()
    if (running) return running
    if (queued) {
      if (timer !== undefined) clearTimeout(timer)
    } else {
      let resolve!: () => void
      const promise = new Promise<void>((done) => {
        resolve = done
      })
      queued = {
        version,
        promise,
        resolve,
        target: {
          path: '/redirect' + route.path,
          hash: route.hash,
          query: Object.fromEntries(
            Object.entries(route.query).map(([key, value]) => [
              key,
              Array.isArray(value) ? [...value] : value,
            ])
          ),
        },
      }
      loading.value = true
    }
    timer = setTimeout(() => {
      void run()
    }, 200)
    return queued.promise
  }
  watch(
    () => [route.fullPath, user.userId, user.roleId, user.token, user.selected_environment],
    invalidate,
    { flush: 'sync' }
  )
  function visibilityChanged(): void {
    if (typeof document !== 'undefined' && document.hidden) invalidate()
  }
  onMounted(() => {
    if (typeof document !== 'undefined')
      document.addEventListener('visibilitychange', visibilityChanged)
  })
  onActivated(() => {
    active = true
  })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onBeforeUnmount(() => {
    disposed = true
    invalidate()
    if (typeof document !== 'undefined')
      document.removeEventListener('visibilitychange', visibilityChanged)
  })
  return { loading, refresh }
}
