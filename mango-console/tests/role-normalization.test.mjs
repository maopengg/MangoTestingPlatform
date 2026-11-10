import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { setupRolePage, roleOk as ok, roleFixture as row, permissionFixture as permissions } from './helpers/role-page-harness.mjs'

test('finite role boundaries reject unreadable permission sets and preserve zero/long IDs', t => {
  const h = setupRolePage(); t.after(h.close); const m = h.load('role-permissions.ts')
  assert.deepEqual(m.createRoleForm({ name: 'Name', description: 'Description', id: 1 }), { name: 'Name', description: 'Description' })
  assert.deepEqual(m.parseRoles(ok([row(0), row('9007199254740993123')])).map(r => r.id), [0, '9007199254740993123'])
  for (const value of [null, false, '', -1, 1.5, Number.MAX_SAFE_INTEGER + 1]) assert.throws(() => m.parseRoles(ok([row(value)])))
  assert.throws(() => m.parseRoles(ok([row(1), row('1')])) )
  for (const data of [{}, { tree: [], checked_keys: null }, { tree: [], checked_keys: [null] }, { tree: [{}], checked_keys: [] }, { tree: [{ permissionKey: 'system', actions: [{}] }], checked_keys: [] }]) assert.throws(() => m.parseRolePermissions(ok(data)))
  assert.throws(() => m.parseRolePermissions({ code: 403, data: permissions() }))
  assert.deepEqual(m.parsePermissionKeys(['index.home', 'index.home']), ['index.home'])
})
test('display-only home wrapper preserves real child permissions without inventing a grant key', async t => {
  const source = permissions()
  source.tree = [{ menuUrl: '/index', menuName: '首页', children: [source.tree[0]] }, source.tree[1]]
  const h = setupRolePage({ getUserRolePermission: async () => ok(source) }); t.after(h.close)
  h.mount(); await flush()
  assert.equal(h.permissionError.value, '')
  assert.equal(h.canSavePermission.value, true)
  assert.deepEqual(h.permissionPanel.treeData.map(node => node.key), ['index.home', 'system.role'])
  assert.deepEqual(h.permissionPanel.checkedKeys, source.checked_keys)
  const m = h.load('role-permissions.ts')
  assert.throws(() => m.toPermissionTree([{ children: [source.tree[1]], actions: [{ permissionKey: 'unknown:change' }] }]))
})

test('list and permission loading are independent; failed read cannot enable saving and can retry', async t => {
  const pending = deferred(); let n = 0
  const h = setupRolePage({ getUserRolePermission: () => ++n === 1 ? pending.promise : Promise.resolve(ok(permissions())) }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.listLoading.value, false); assert.equal(h.permissionPanel.loading, true)
  pending.reject({ msg: 'Denied' }); await flush()
  assert.equal(h.loadedRoleId.value, null); assert.equal(h.canSavePermission.value, false)
  await h.onSavePermission(); assert.equal(h.calls.filter(c => c[0] === 'putUserRolePermission').length, 0)
  assert.equal(h.permissionError.value, 'Denied'); await h.retryPermission(); assert.equal(h.canSavePermission.value, true)
})
test('list failure recovers; same list request coalesces; absent role clears permissions', async t => {
  let n = 0; const pending = deferred()
  const h = setupRolePage({ getUserAllRole: () => ++n === 1 ? Promise.reject({ msg: 'Denied' }) : pending.promise }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.listError.value, 'Denied'); assert.equal(h.listLoading.value, false)
  const a = h.doRefresh(), b = h.doRefresh(); assert.equal(a, b)
  pending.resolve(ok([])); await a; assert.equal(h.listError.value, ''); assert.equal(h.selectedRole.value, null); assert.equal(h.loadedRoleId.value, null)
})
test('editor uses independent drafts, whitelisted snapshots and physical busy across cancel', async t => {
  const pending = deferred(); const h = setupRolePage({ putUserRoleList: () => pending.promise }); t.after(h.close)
  h.mount(); await flush(); const source = { id: 0, name: 'Original', description: 'Description', extra: 'omit' }
  h.onUpdate(source); h.form.name = 'Edited'; assert.equal(source.name, 'Original'); assert.equal(h.actionTitle.value, '编辑')
  const saving = h.onDataForm(); h.form.name = 'Later'; await h.onDataForm()
  assert.deepEqual(h.calls.find(c => c[0] === 'putUserRoleList')[1], { id: 0, name: 'Edited', description: 'Description' })
  assert.equal(h.calls.filter(c => c[0] === 'putUserRoleList').length, 1)
  h.closeEditor(); h.onAdd(); assert.equal(h.editorVisible.value, false); assert.equal(h.writeBusy.value, true)
  pending.resolve(ok()); await saving; h.onAdd(); assert.equal(h.form.name, ''); assert.equal(h.actionTitle.value, '新增')
  await h.onDataForm(); assert.equal(h.calls.filter(c => c[0] === 'postUserRoleList').length, 0)
})
test('save failure keeps draft; successful retry closes modal without toggling it open', async t => {
  let n = 0; const h = setupRolePage({ postUserRoleList: () => ++n === 1 ? Promise.reject({ msg: 'Denied' }) : Promise.resolve(ok()) }); t.after(h.close)
  h.mount(); await flush(); h.onAdd(); h.form.name = 'New'; await h.onDataForm()
  assert.equal(h.editorVisible.value, true); assert.equal(h.form.name, 'New'); assert.equal(h.saving.value, false)
  await h.onDataForm(); assert.equal(h.editorVisible.value, false); assert.equal(h.shell.visible, false)
})
test('delete confirmation retries rejection, guards repeats, and returns true on success', async t => {
  let n = 0; const pending = deferred(); const h = setupRolePage({ deleteUserRoleList: () => ++n === 1 ? Promise.reject({ msg: 'Denied' }) : pending.promise }); t.after(h.close)
  h.mount(); await flush(); h.onDelete({ id: 0, name: 'Delete', description: '' }); const dialog = h.dialogs[0]
  assert.equal(await dialog.config.onBeforeOk(), false)
  const removing = dialog.config.onBeforeOk(); assert.equal(await dialog.config.onBeforeOk(), false)
  pending.resolve(ok()); assert.equal(await removing, true); assert.equal(h.calls.filter(c => c[0] === 'deleteUserRoleList').length, 2)
})
test('permission writes fix role and key snapshots; load/saving prevent events and duplicate submits', async t => {
  const pending = deferred(); const h = setupRolePage({ putUserRolePermission: () => pending.promise }); t.after(h.close)
  h.mount(); await flush(); const keys = [...h.permissionPanel.checkedKeys]
  const saving = h.onSavePermission(); await h.onSavePermission(); await h.onSelectRole({ id: 2, name: 'Other', description: '' })
  h.onActionCheck('system.role:change', false)
  assert.equal(h.selectedRole.value.id, 1); assert.deepEqual(h.permissionPanel.checkedKeys, keys)
  assert.deepEqual(h.calls.find(c => c[0] === 'putUserRolePermission')[1], { role_id: 1, permission_keys: keys })
  pending.reject({ msg: 'Denied' }); await saving; assert.equal(h.permissionPanel.saving, false); assert.equal(h.canSavePermission.value, true)
})
test('guest target stays immutable while empty caller permissions do not preblock other role writes', async t => {
  const h = setupRolePage({ getUserAllRole: async () => ok([{ ...row(), title: '游客' }]) }); t.after(h.close)
  h.mount(); await flush(); h.onUpdate(h.roles.value[0]); h.onDelete(h.roles.value[0]); h.onActionCheck('system.role:change', false); await h.onSavePermission()
  assert.equal(h.editorVisible.value, false); assert.equal(h.dialogs.length, 0); assert.equal(h.calls.filter(c => c[0].startsWith('put')).length, 0)
  await h.onSelectRole({ id: 2, name: 'Other', description: '' }); await h.onSavePermission()
  assert.equal(h.calls.filter(c => c[0] === 'putUserRolePermission').length, 1)
})
test('identity changes invalidate reads and pending drafts; visibility and KeepAlive restore current state', async t => {
  const first = deferred(); let n = 0
  const h = setupRolePage({ getUserRolePermission: () => ++n === 1 ? first.promise : Promise.resolve(ok(permissions())) }); t.after(h.close)
  h.mount(); await flush(); h.user.token = 'new'; await flush(); first.resolve(ok({ tree: [], checked_keys: ['stale'] })); await flush()
  assert.equal(h.permissionPanel.checkedKeys.includes('stale'), false)
  for (const change of [() => h.user.userId++, () => h.user.roleId++, () => h.user.selected_environment++, () => h.permission.permissionKeys.push('system.role:read'), () => { h.route.fullPath += '?x' }]) {
    h.onAdd(); change(); await flush(); assert.equal(h.editorVisible.value, false); assert.equal(h.loadedRoleId.value, 1)
  }
  await h.visibility('hidden'); assert.equal(h.loadedRoleId.value, null); const count = h.calls.length
  await h.doRefresh(); assert.equal(h.calls.length, count)
  await h.visibility('visible'); assert.equal(h.loadedRoleId.value, 1)
  h.life.deactivate.forEach(f => f()); assert.equal(h.loadedRoleId.value, null)
  h.life.activate.forEach(f => f()); await flush(); assert.equal(h.loadedRoleId.value, 1)
})
test('own permission route refresh failure is separate and retries without repeating saved PUT', async t => {
  let n = 0; const h = setupRolePage({ initPermissionRoute: async () => { if (++n === 1) throw Error('offline') } }); t.after(h.close)
  h.mount(); await flush(); h.user.roleId = 1; await flush()
  await h.onSavePermission(); assert.match(h.routeRefreshError.value, /权限已保存/)
  await h.refreshOwnRoutes(); assert.equal(h.routeRefreshError.value, ''); assert.equal(h.calls.filter(c => c[0] === 'putUserRolePermission').length, 1)
})
test('own route refresh cannot apply to another identity, and permission key update reloads safely', async t => {
  const pending = deferred(); let guard
  const h = setupRolePage({ initPermissionRoute: async (_force, isCurrent) => { guard = isCurrent; await pending.promise; if (isCurrent()) h.permission.permissionKeys = ['system.role:read'] } }); t.after(h.close)
  h.mount(); await flush(); h.user.roleId = 1; await flush()
  const save = h.onSavePermission(); await flush(); h.user.token = 'other'; assert.equal(guard(), false)
  pending.resolve(); await save; await flush(); assert.deepEqual(h.permission.permissionKeys, []); assert.equal(h.loadedRoleId.value, 1)
})
test('role SFC script/template/style compile with finite typed form bindings', async () => {
  const filename = path.resolve('src/views/system/role/index.vue'), source = readFileSync(filename, 'utf8')
  const { descriptor, errors } = parse(source); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'role' })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: 'role', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: 'role', scoped: style.scoped })).errors, [])
})

test('cancelled deletion cannot affect a reopened editor and keeps the physical lock until response', async t => {
  const pending = deferred(); const h = setupRolePage({ deleteUserRoleList: () => pending.promise }); t.after(h.close)
  h.mount(); await flush(); h.onDelete({ id: 1, name: 'Target', description: '' }); const dialog = h.dialogs[0]
  const deleting = dialog.config.onBeforeOk(); dialog.config.onCancel(); h.onAdd(); assert.equal(h.editorVisible.value, false)
  pending.resolve(ok()); assert.equal(await deleting, false); await flush(); h.onAdd(); assert.equal(h.editorVisible.value, true)
  assert.equal(h.messages.filter(([kind]) => kind === 'success').length, 0)
})
test('own route update clears prior permission context and restores the current role after save settles', async t => {
  let n = 0; const h = setupRolePage({ initPermissionRoute: async (_force, isCurrent) => { if (isCurrent()) h.permission.permissionKeys = ['system.role:read'] }, getUserRolePermission: async () => { n++; return ok(permissions()) } }); t.after(h.close)
  h.mount(); await flush(); h.user.roleId = 1; await flush(); const before = n
  await h.onSavePermission(); await flush()
  assert.deepEqual(h.permission.permissionKeys, ['system.role:read']); assert.equal(h.loadedRoleId.value, 1); assert.ok(n > before); assert.equal(h.canSavePermission.value, true)
})
test('unreadable successful permission receipt cannot be saved as empty and still refreshes own routes', async t => {
  let refreshed = 0; const h = setupRolePage({ putUserRolePermission: async () => ok({ invalid: true }), initPermissionRoute: async () => { refreshed++ } }); t.after(h.close)
  h.mount(); await flush(); h.user.roleId = 1; await flush(); await h.onSavePermission()
  assert.equal(refreshed, 1); assert.match(h.permissionError.value, /权限已保存/); assert.equal(h.loadedRoleId.value, null); assert.equal(h.canSavePermission.value, false)
  await h.onSavePermission(); assert.equal(h.calls.filter(c => c[0] === 'putUserRolePermission').length, 1)
  await h.retryPermission(); assert.equal(h.canSavePermission.value, true)
})

test('returning from background does not revive an old route response; it refreshes current routes again', async t => {
  const pending = deferred(); const guards = []
  const h = setupRolePage({ initPermissionRoute: async (_force, valid) => { guards.push(valid); if (guards.length === 1) await pending.promise } }); t.after(h.close)
  h.mount(); await flush(); h.user.roleId = 1; await flush()
  const save = h.onSavePermission(); await flush(); await h.visibility('hidden'); await h.visibility('visible')
  assert.equal(guards[0](), false); pending.resolve(); await save; await flush()
  assert.equal(guards.length, 2); assert.equal(guards[1](), true); assert.equal(h.calls.filter(c => c[0] === 'putUserRolePermission').length, 1)
})

test('own permission write completed in background refreshes routes on return without applying stale panel data', async t => {
  const pending = deferred(); let refreshed = 0
  const h = setupRolePage({ putUserRolePermission: () => pending.promise, initPermissionRoute: async () => { refreshed++ } }); t.after(h.close)
  h.mount(); await flush(); h.user.roleId = 1; await flush()
  const save = h.onSavePermission(); await h.visibility('hidden'); pending.resolve(ok(['stale-panel-key'])); await save
  assert.equal(refreshed, 0); assert.equal(h.permissionPanel.checkedKeys.includes('stale-panel-key'), false)
  await h.visibility('visible'); assert.equal(refreshed, 1); assert.equal(h.calls.filter(c => c[0] === 'putUserRolePermission').length, 1)
})
