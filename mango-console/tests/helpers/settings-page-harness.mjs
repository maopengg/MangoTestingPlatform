import path from 'node:path'
import * as vue from 'vue'
import { harness } from './case-details-harness.mjs'

export function settingsPageHarness(options = {}) {
  const previousDocument = globalThis.document
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, messages = []
  const route = vue.reactive({ path: '/system/settings/index', fullPath: '/system/settings/index', query: { group: options.group } })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'example', selected_environment: 0 })
  const permission = vue.reactive({ permissionKeys: [] })
  const h = harness('index', 'doRefresh,loadSettingsEnums,settingsGroups,settingsLoading,settingsReady,settingsError,enumsLoading,enumsError,saveItem,lastSavedValues,normalizeEditValue,normalizePayloadValue,activeNavigationKey,panelRef,sectionElements,configSectionElements', {
    base: path.resolve('src/views/system/settings'), api: options.api || {}, modules: {
      vue: { ...vue, onMounted: f => callbacks.mount.push(f), onActivated: f => callbacks.activate.push(f), onDeactivated: f => callbacks.deactivate.push(f), onBeforeUnmount: f => callbacks.unmount.push(f) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/store/modules/get-enum': { useEnum: () => ({ environment_type: options.environmentOptions || [], getEnum: options.enumRead || (async () => {}) }) },
      '@/hooks/useMenuIcon': { useMenuIcon: () => ({ resolveMenuIcon: () => '' }) },
      '@/store/modules/platform-branding': { default: () => ({ apply() {} }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['warning', 'error', 'success'].map(kind => [kind, value => messages.push([kind, value])])), Modal: {} },
    },
  })
  return { ...h, route, user, permission, callbacks, messages,
    mount() { callbacks.mount.forEach(f => f()); callbacks.activate.forEach(f => f()) },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(f => f()); h.close(); globalThis.document = previousDocument },
  }
}
