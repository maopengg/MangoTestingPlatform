import * as vue from 'vue'
import { harness } from './case-details-harness.mjs'
import { loadModule } from './auth-config-harness.mjs'
import { uiAuthBase, uiAuthRecord } from './ui-auth-editor-harness.mjs'

export const authListResponse = (rows = [uiAuthRecord()], totalSize = rows.length) => ({ code: 200, data: rows, totalSize })
export function setupUiAuthList(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], writes = [], messages = [], confirmations = []
  const route = vue.reactive({ path: '/uitest/auth-config/index', fullPath: '/uitest/auth-config/index' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.auth_config:read'] })
  const enumStore = vue.reactive({ environment_type: [{ key: 0, title: 'Test' }], ui_auth_type: [], ui_auth_refresh_mode: [], ui_auth_refresh_status: [], colors: [], getEnum: overrides.getEnum || (async () => {}) })
  const table = loadModule('src/hooks/table.ts'), search = loadModule('src/utils/search-condition.ts')
  const api = Object.fromEntries(Object.entries({
    getUiAuthConfig: overrides.getUiAuthConfig || (async () => authListResponse()), getUserName: overrides.getUserName || (async () => ({ code: 200, data: [{ id: 0, name: 'Example user' }] })),
    putUiAuthConfigStatus: overrides.putUiAuthConfigStatus || (async () => ({ code: 200 })), postUiAuthConfigRefresh: overrides.postUiAuthConfigRefresh || (async () => ({ code: 200 })),
    postUiAuthConfigClear: overrides.postUiAuthConfigClear || (async () => ({ code: 200 })), deleteUiAuthConfig: overrides.deleteUiAuthConfig || (async () => ({ code: 200 })),
    postUiAuthConfigAutoStart: overrides.postUiAuthConfigAutoStart || (async () => ({ code: 200, data: { task_id: 91 } })), postUiAuthConfigAutoCapture: overrides.postUiAuthConfigAutoCapture || (async () => ({ code: 200, data: { task_id: 92 } })),
    getExecutorTask: overrides.getExecutorTask || (async () => ({ code: 200 })),
  }).map(([name, fn]) => [name, (...args) => { (name.startsWith('get') ? reads : writes).push([name, ...args]); return fn(...args) }]))
  const h = harness('index', 'rows,listLoading,listError,list,query,pagination,conditionItems,userOptions,usersLoading,usersError,enumsLoading,enumsError,operationError,editorRef,cacheRef,sidebarResetKey,available,identity,doRefresh,refreshAfterEditor,onReset,normalizeQuery,onSearchRefresh,onNavigationFilterChange,loadUsers,loadEnums,onStatusChange,onRefresh,onClear,onDelete,getAuthActions,busy,isOperationLoading,optionTitle,onEdit,tasks,taskError,onAutoStart,onAutoCapture,isAuthTaskLoading', {
    base: uiAuthBase, api, modules: {
      vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
      '@/hooks/table': table, '@/utils/id-search': { createIdSearchValue: () => '' }, '@/utils/search-condition': search,
      '@/utils/update-user': { createUpdateUserCondition: () => ({ key: 'update_user', type: 'select', value: [] }), updateUserColumn: () => ({ key: 'update_user', width: 110 }) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@/store/modules/get-enum': { useEnum: () => enumStore },
      '@/utils/executor-task-observer.mjs': overrides.observer || { loadExecutorTaskObservation: () => null, saveExecutorTaskObservation() {}, clearExecutorTaskObservation() {} },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error'].map(key => [key, value => messages.push([key, value])])), Modal: { confirm(options) { const shell = { ...options, closed: false, close() { this.closed = true } }; confirmations.push(shell); return shell } } },
    },
  })
  return { ...h, callbacks, reads, writes, messages, confirmations, route, user, permission,
    mount: () => Promise.allSettled(callbacks.mount.map(fn => fn())),
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous },
  }
}
