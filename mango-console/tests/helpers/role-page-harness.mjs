import path from 'node:path'
import * as vue from 'vue'
import { harness, flush } from './case-details-harness.mjs'
export const roleOk = (data = []) => ({ code: 200, data, msg: 'ok' })
export const roleFixture = (id = 1) => ({ key: id, title: 'Example role', description: 'Description' })
export const permissionFixture = () => ({ tree: [{ permissionKey: 'index.home', children: [] }, { permissionKey: 'system.role', children: [] }], menu_keys: ['index.home', 'system.role'], endpoint_groups: [], endpoint_permissions: {} })
export function setupRolePage(options = {}) {
  const life = { mount: [], activate: [], deactivate: [], unmount: [] }, calls = [], dialogs = [], messages = []
  const route = vue.reactive({ path: '/organization-permission/role/index', fullPath: '/organization-permission/role/index' })
  const user = vue.reactive({ userId: 1, roleId: 99, token: 'fixture', selected_environment: 0 })
  const permission = vue.reactive({ permissionKeys: [], hasPermission: () => true, initPermissionRoute: options.initPermissionRoute || (async () => {}) })
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const api = Object.fromEntries(['getUserAllRole', 'getUserRolePermission', 'postUserRoleList', 'putUserRoleList', 'deleteUserRoleList', 'putUserRolePermission'].map(name => [name, payload => {
    calls.push([name, structuredClone(payload)]); return options[name]?.(payload) ?? Promise.resolve(roleOk(name === 'getUserAllRole' ? [roleFixture()] : name === 'getUserRolePermission' ? permissionFixture() : []))
  }]))
  const h = harness('index', 'roles,listLoading,listError,permissionError,selectedRole,loadedRoleId,permissionPanel,pageCheckedKeys,endpointGroups,endpointOverrides,onEndpointChange,canSavePermission,isPermissionReadonly,form,editorId,editorVisible,actionTitle,saving,writeBusy,modalDialogRef,routeRefreshError,routeRefreshing,doRefresh,onSelectRole,retryPermission,onAdd,onUpdate,closeEditor,onDataForm,onDelete,onSavePermission,refreshOwnRoutes,onPageCheck,onPageSelect,onPageExpand,expandPermissionTree', {
    base: path.resolve('src/views/system/role'), api, modules: {
      vue: { ...vue, onMounted: f => life.mount.push(f), onActivated: f => life.activate.push(f), onDeactivated: f => life.deactivate.push(f), onBeforeUnmount: f => life.unmount.push(f) },
      'vue-router': { useRoute: () => route, useRouter: () => ({ replace: options.replace || (async () => {}) }) },
      '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(kind => [kind, text => messages.push([kind, text])])), Modal: { confirm(config) { const handle = { config, closed: false, close() { this.closed = true } }; dialogs.push(handle); return handle } } },
    },
  })
  const shell = { visible: false, loading: false, show() { this.visible = true }, close() { this.visible = false; this.loading = false }, setConfirmLoading(v) { this.loading = v } }
  h.modalDialogRef.value = shell
  let previous, mounted = false
  return { ...h, calls, dialogs, messages, route, user, permission, shell, life,
    mount() { mounted = true; previous = globalThis.document; globalThis.document = doc; life.mount.forEach(f => f()); life.activate.forEach(f => f()) },
    async visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')); await flush() },
    close() { if (mounted) { const current = globalThis.document; globalThis.document = doc; life.unmount.forEach(f => f()); globalThis.document = current === doc ? previous : current } h.close() },
  }
}
