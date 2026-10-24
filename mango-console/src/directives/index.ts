import { App, Directive, Ref, ref, watchEffect } from 'vue'
import usePermissionStore from '@/store/modules/permission'
import type { PermissionRequirement } from '@/utils/permission'

const states = new WeakMap<HTMLElement, {
  required: Ref<PermissionRequirement | undefined>
  stop: () => void
}>()

export const permissionDirective: Directive<HTMLElement, PermissionRequirement> = {
  mounted(el, binding) {
    const store = usePermissionStore()
    const required = ref<PermissionRequirement | undefined>(binding.value)
    const stop = watchEffect(() => {
      el.toggleAttribute('data-mango-permission-denied', !store.hasPermission(required.value))
    })
    states.set(el, { required, stop })
  },
  updated(el, binding) {
    const state = states.get(el)
    if (state) state.required.value = binding.value
  },
  unmounted(el) {
    states.get(el)?.stop()
    states.delete(el)
  },
}

export function setupDirectives(app: App) {
  app.directive('permission', permissionDirective)
}
