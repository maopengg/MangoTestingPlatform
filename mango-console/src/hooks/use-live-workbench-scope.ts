import { onActivated, onBeforeUnmount, onDeactivated, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'

/** Each request owns an epoch as well as an identity, including A → B → A navigation. */
export function useLiveWorkbenchScope(context: () => unknown, options: { invalidate: () => void; resume: () => void }) {
  const user = useUserStore(), permission = usePermissionStore(), route = useRoute(), path = route.path
  let active = true, disposed = false, mounted = false, epoch = 0
  const identity = () => JSON.stringify([route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys, context()])
  const available = () => !disposed && active && route.path === path && document.visibilityState === 'visible'
  function capture() { const version = epoch, key = identity(); return () => available() && version === epoch && key === identity() }
  function invalidate() { epoch++; options.invalidate() }
  function resume() { if (mounted && available()) options.resume() }
  watch(identity, () => { invalidate(); resume() }, { flush: 'sync' })
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate(); else resume() }
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged) })
  onActivated(() => { const wasInactive = !active; active = true; if (wasInactive) resume() })
  onDeactivated(() => { active = false; invalidate() })
  onBeforeUnmount(() => { disposed = true; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { available, capture }
}
