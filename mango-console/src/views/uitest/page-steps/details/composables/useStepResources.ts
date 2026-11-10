import { reportLoadError } from '@/utils/load-error'
import { onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'

type Resource = 'steps' | 'aliases' | 'elements' | 'details' | 'files'
export function useStepResources(options: { enabled: () => boolean; context: () => unknown; invalidated: () => void; resume: () => void }) {
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore()
  const path = route.path
  const loading = reactive({ steps: false, aliases: false, elements: false, details: false, files: false })
  const errors = reactive({ steps: '', aliases: '', elements: '', details: '', files: '' })
  const sequences = { steps: 0, aliases: 0, elements: 0, details: 0, files: 0 }
  let revision = 0, active = true, disposed = false, mounted = false
  const identity = () => JSON.stringify([options.context(), route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => !disposed && active && route.path === path && document.visibilityState === 'visible'
  function capture() { const key = identity(), version = revision; return () => available() && version === revision && key === identity() }
  function invalidate() {
    revision++
    for (const key of Object.keys(loading) as Resource[]) { loading[key] = false; errors[key] = '' }
    if (options.enabled()) options.invalidated()
  }
  async function read<T>(resource: Resource, request: () => Promise<T>, apply: (result: T) => void): Promise<boolean> {
    const currentContext = capture(), sequence = ++sequences[resource]
    const current = () => currentContext() && sequence === sequences[resource]
    if (!current()) return false
    loading[resource] = true; errors[resource] = ''
    try { const result = await request(); if (!current()) return false; apply(result); return true }
    catch (error) { if (current()) { errors[resource] = '加载失败，请重试'; reportLoadError(error) }; return false }
    finally { if (current()) loading[resource] = false }
  }
  function resume() { if (mounted && available() && options.enabled()) options.resume() }
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate(); else resume() }
  watch(identity, () => { invalidate(); resume() }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged) })
  onActivated(() => { const paused = !active; active = true; if (paused) resume() })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { loading, errors, read, capture }
}
