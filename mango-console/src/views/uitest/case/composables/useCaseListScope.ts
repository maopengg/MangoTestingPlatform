import { onActivated, onBeforeUnmount, onDeactivated, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'

export function useCaseListScope(options: { invalidate: (clear: boolean) => void; resume?: () => void }) {
  const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), path = route.path
  let active = true, disposed = false, version = 0, mounted = false
  const identity = () => JSON.stringify([route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const available = () => active && !disposed && route.path === path && document.visibilityState === 'visible'
  function capture() { const key = identity(), epoch = version; return () => available() && epoch === version && key === identity() }
  function invalidate(clear = false) { version++; options.invalidate(clear) }
  function resume() { if (mounted && available()) options.resume?.() }
  watch(identity, () => { invalidate(true); resume() }, { flush: 'sync' })
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate(); else resume() }
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged) })
  onActivated(() => { const paused = !active; active = true; if (paused) resume() })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { available, capture, invalidate }
}
