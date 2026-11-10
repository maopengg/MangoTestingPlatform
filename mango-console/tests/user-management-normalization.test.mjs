import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/system/user')
const ok = (data = [], totalSize = 1) => ({ code: 200, data, totalSize, msg: 'ok' })
const row = (values = {}) => ({ id: 0, name: 'Example', username: 'example@example.com', role: { id: 0, name: 'Example role' },
  is_super_admin: false, department_ids: [0, 2], departments: [{ id: 0, name: 'Example department' }, { id: 2, name: 'Other' }],
  requires_email_login_migration: false, ip: null, last_login_time: null, update_time: '2026-11-09 10:00:00', update_user: null, ...values })
function actual(filename, dependencies) {
  const exports = {}, source = ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, name => { if (name in dependencies) return dependencies[name]; { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error('Unexpected dependency ' + name) } })
  return exports
}
function dialog() { return { shown: 0, closed: 0, loading: false, show() { this.shown++; return Promise.resolve(true) }, close() { this.closed++; this.loading = false; return Promise.resolve(false) }, setConfirmLoading(value) { this.loading = value } } }
function setup(overrides = {}, child = false) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, calls = [], messages = [], confirms = [], navigations = []
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 })
  const route = vue.reactive({ path: '/organization-permission/user/index', fullPath: '/organization-permission/user/index' })
  const permission = vue.reactive({ permissionKeys: ['system.user:read'], hasPermission: () => true,
    initPermissionRoute: (...args) => overrides.routes?.(...args) ?? Promise.resolve() })
  const api = Object.fromEntries(['getUserInfo', 'putUserInfo', 'registerUser', 'deleteUserInfo', 'resetUserPassword', 'resetUserApiKey', 'getUserAllRole', 'getUserDepartmentName'].map(name => [name, (...args) => {
    calls.push([name, ...args]); if (overrides[name]) return overrides[name](...args)
    return Promise.resolve(name === 'getUserInfo' ? ok([row()]) : name === 'getUserAllRole' || name === 'getUserDepartmentName' ? ok([{ key: 0, title: 'Example' }]) : ok())
  }]))
  const modal = { confirm(options) { const handle = { options, closed: false, close() { this.closed = true } }; confirms.push(handle); return handle }, warning(options) { return this.confirm(options) } }
  const modules = { vue: { ...vue, onMounted: f => callbacks.mount.push(f), onActivated: f => callbacks.activate.push(f), onDeactivated: f => callbacks.deactivate.push(f), onBeforeUnmount: f => callbacks.unmount.push(f) },
    'vue-router': { useRoute: () => route, useRouter: () => ({ push: async value => navigations.push(value), replace: async value => navigations.push(value) }) },
    '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
    '@/hooks/table': actual('src/hooks/table.ts', { vue }), '@/hooks/use-latest-request': actual('src/hooks/use-latest-request.ts', {}),
    '@arco-design/web-vue': { Modal: modal, Message: Object.fromEntries(['success', 'warning', 'error'].map(name => [name, value => messages.push([name, value])])) } }
  const names = child ? 'draft,record,visible,saving,roles,departments,roleOptions,departmentOptions,roleLoading,departmentLoading,roleError,departmentError,saveError,dialog,openRegister,openEdit,closeEditor,loadRoles,loadDepartments,save,emailSettings'
    : 'rows,listLoading,listError,conditionItems,pagination,selectedRowKeys,editor,editorSaving,identityKey,passwordTarget,passwordError,resetPasswordDialogRef,rowOperation,routeRefreshing,routeRefreshError,writeBusy,doRefresh,onSearch,onResetSearch,onRegisterUser,onUpdate,onResetPassword,onResetPasswordConfirm,closePassword,onDelete,onResetApiKey,onSuperAdminChange,onUserSaved,onEditorBusy,onEditorCommitted,refreshOwnRoutes,goToEmailConfig'
  const h = harness(child ? 'UserEditorDialog' : 'index', names, { base, api, modules, props: { contextKey: 'example-context', locked: false } })
  const shell = dialog(); if (child) h.dialog.value = shell; else h.resetPasswordDialogRef.value = shell
  return { ...h, shell, user, route, permission, callbacks, calls, messages, confirms, navigations,
    mount() { callbacks.mount.forEach(f => f()); callbacks.activate.forEach(f => f()) },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(f => f()); h.close(); globalThis.document = previous } }
}

test('user DTO drops secrets and audit-only extra fields, preserves zero/long IDs and copies all relations', t => {
  const h = setup(); t.after(h.close); const m = h.load('user-records.ts'), input = row({ password: 'example-secret', api_key: 'example-secret', config: {} })
  const parsed = m.copyUserRecord(input); assert.equal(parsed.id, 0); assert.equal(parsed.role.id, 0)
  for (const key of ['password', 'api_key', 'config']) assert.equal(key in parsed, false)
  parsed.department_ids.push(3); parsed.departments[0].name = 'Changed'; parsed.role.name = 'Changed'
  assert.deepEqual(input.department_ids, [0, 2]); assert.equal(input.departments[0].name, 'Example department'); assert.equal(input.role.name, 'Example role')
  assert.equal(m.copyUserRecord(row({ id: '90071992547409931234' })).id, '90071992547409931234')
})
test('malformed list/flags/IDs and error responses remain errors instead of empty or truthy success', t => {
  const h = setup(); t.after(h.close); const m = h.load('user-records.ts')
  for (const value of [{ code: 403, data: [] }, ok({}), ok([row()], '1'), ok([row(), row()], 2), ok([row({ id: Number.MAX_SAFE_INTEGER + 1 })]), ok([row({ is_super_admin: 'false' })]), ok([row({ requires_email_login_migration: 0 })]), ok([row({ department_ids: [0, '0'] })])]) assert.throws(() => m.parseUserList(value))
  assert.deepEqual(m.parseUserList(ok([], 0)), { rows: [], total: 0 })
  assert.throws(() => m.userSuccess({ code: 400, msg: 'failed' }, 'fallback'))
})
test('drafts and whitelist payloads preserve role zero, are independent, and keep registration/email semantics', t => {
  const h = setup(); t.after(h.close); const m = h.load('user-records.ts'), source = m.copyUserRecord(row()), draft = m.createUserDraft(source)
  draft.department_ids.push(3); assert.deepEqual(source.department_ids, [0, 2]); assert.deepEqual(m.createUserDraft().department_ids, [])
  const payload = m.userUpdatePayload(source.id, draft); draft.department_ids.push(4)
  assert.deepEqual(payload.department_ids, [0, 2, 3]); assert.equal(payload.role, 0); assert.equal('update_user' in payload, false)
  const registration = m.userRegistrationPayload({ ...draft, name: ' Example ', username: 'Example@EXAMPLE.com ' })
  assert.deepEqual(registration, { name: 'Example', email: 'example@example.com', role: 0, is_super_admin: false }); assert.equal('department_ids' in registration, false)
  assert.match(m.validateUserDraft({ ...draft, username: 'legacy' }), /邮箱/)
})
test('options are finite and selected unavailable roles/departments retain readable names without duplicates', t => {
  const h = setup(); t.after(h.close); const m = h.load('user-records.ts'), options = m.parseUserOptions(ok([{ key: 0, title: 'Example', extra: 'omit' }]))
  assert.deepEqual(options, [{ key: 0, title: 'Example' }]); assert.throws(() => m.parseUserOptions(ok([{ key: false, title: 'bad' }])))
  const merged = m.mergeUserOptions(options, [{ id: '0', name: 'Same' }, { id: 3, name: 'Unavailable' }]); assert.equal(merged.length, 2)
  merged[0].title = 'Change'; assert.equal(options[0].title, 'Example')
})
test('search instances reset independently, ID separators share global normalization and query omits empty/unrelated values', t => {
  const h = setup(); t.after(h.close); const m = h.load('user-records.ts'), config = h.load('config.ts'), a = config.createConditionItems(), b = config.createConditionItems()
  a[0].value = '5574、5577'; assert.equal(a[0].value, '5574,5577'); assert.equal(b[0].value, '')
  assert.deepEqual(m.userSearchQuery({ id: '5574,5577', name: '', username: null, unrelated: 'omit' }), { id__in: '5574,5577' })
  assert.deepEqual(m.userSearchQuery({ name: 'Example' }), { name: 'Example' }); assert.throws(() => m.userSearchQuery({ username: {} }))
})
test('editor opens a copy, preserves selected option labels and clears draft on cancel/reopen', async t => {
  const h = setup({}, true); t.after(h.close); const input = row(); h.openEdit(input); await flush()
  h.draft.name = 'Changed'; h.draft.department_ids.push(3); assert.equal(input.name, 'Example'); assert.deepEqual(input.department_ids, [0, 2])
  assert.equal(h.roleOptions.value[0].key, 0); assert.equal(h.departmentOptions.value.find(item => item.key === 2).title, 'Other')
  h.closeEditor(); h.openRegister(); assert.equal(h.record.value, null); assert.equal(h.draft.role, null); assert.deepEqual(h.draft.department_ids, []); assert.equal(h.draft.is_super_admin, false)
})
test('editor registration has fixed payload and physical duplicate lock, and never submits a password', async t => {
  const write = deferred(), h = setup({ registerUser: () => write.promise }, true); t.after(h.close)
  h.openRegister(); Object.assign(h.draft, { name: ' Example ', username: 'Example@EXAMPLE.com', role: 0 })
  const task = h.save(); h.draft.username = 'new@example.com'; await h.save(); h.openEdit(row({ id: 2 }))
  assert.equal(h.calls.filter(([name]) => name === 'registerUser').length, 1); assert.equal(h.calls.find(([name]) => name === 'registerUser')[1].email, 'example@example.com')
  assert.equal(h.saving.value, true); assert.equal(h.shell.loading, true)
  write.resolve(ok()); await task; assert.equal(h.visible.value, false); assert.equal(h.saving.value, false); assert.ok(h.events.some(([name, id]) => name === 'saved' && id === null))
})
test('editor validates legacy email, retries save failure and preserves current draft on failure', async t => {
  let count = 0; const h = setup({ putUserInfo: async () => ++count === 1 ? { code: 400 } : ok() }, true); t.after(h.close)
  h.openEdit(row({ username: 'legacy', requires_email_login_migration: true })); await h.save(); assert.equal(count, 0); assert.equal(h.shell.loading, false)
  h.draft.username = 'new@example.com'; await h.save(); assert.match(h.saveError.value, /重试/); assert.equal(h.visible.value, true); assert.equal(h.draft.username, 'new@example.com')
  await h.save(); assert.equal(count, 2); assert.equal(h.visible.value, false)
})
test('cancel during editor save keeps physical lock and late success does not close or notify a new context', async t => {
  const write = deferred(), h = setup({ putUserInfo: () => write.promise }, true); t.after(h.close)
  h.openEdit(row()); const task = h.save(); h.closeEditor(); h.props.contextKey = 'different-user'; await flush(); h.openEdit(row({ id: 2 }))
  assert.equal(h.visible.value, false); assert.equal(h.saving.value, true)
  write.resolve(ok()); await task; assert.equal(h.saving.value, false); assert.equal(h.events.some(([name]) => name === 'saved'), false); assert.equal(h.messages.some(([name]) => name === 'success'), false)
  h.openEdit(row({ id: 2 })); assert.equal(h.record.value.id, 2)
})
test('role and department reads load independently, fail/retry, and ignore old-open responses', async t => {
  const role = deferred(), department = deferred(); let count = 0
  const h = setup({ getUserAllRole: () => role.promise, getUserDepartmentName: () => ++count === 1 ? department.promise : Promise.resolve(ok([{ key: 3, title: 'New' }])) }, true); t.after(h.close)
  h.openEdit(row()); const same = h.loadDepartments(); assert.equal(h.loadDepartments(), same); await flush()
  role.resolve(ok([{ key: 0, title: 'Role' }])); await flush(); assert.equal(h.roleLoading.value, false); assert.equal(h.departmentLoading.value, true)
  department.reject(Error('offline')); await same; assert.match(h.departmentError.value, /重试/); await h.loadDepartments(); assert.equal(h.departmentError.value, '')
  h.closeEditor(); h.openRegister(); await flush(); assert.deepEqual(h.departments.value, [])
})
test('editor context change invalidates in-flight options and clears sensitive form data', async t => {
  const options = deferred(), h = setup({ getUserAllRole: () => options.promise }, true); t.after(h.close)
  h.openEdit(row()); await flush(); h.props.contextKey = 'other'; await flush(); options.resolve(ok([{ key: 4, title: 'Old' }])); await flush()
  assert.equal(h.visible.value, false); assert.equal(h.draft.username, ''); assert.deepEqual(h.roles.value, []); assert.equal(h.roleLoading.value, false)
})
test('list requests coalesce, search resets page and old responses cannot override current filters', async t => {
  const a = deferred(), b = deferred(); let n = 0; const h = setup({ getUserInfo: () => ++n === 1 ? a.promise : b.promise }); t.after(h.close)
  h.mount(); const first = h.doRefresh(); assert.equal(h.doRefresh(), first); await flush(); assert.equal(n, 1)
  h.pagination.page = 3; h.conditionItems[1].value = 'New'; const latest = h.onSearch(); await flush()
  assert.equal(h.calls.at(-1)[1].page, 1); assert.equal('size' in h.calls.at(-1)[1], false)
  b.resolve(ok([row({ id: 2 })])); await latest; a.resolve(ok([row({ id: 1 })])); await first
  assert.equal(h.rows.value[0].id, 2); assert.equal(h.listLoading.value, false)
})
test('list malformed/error response preserves current rows, can retry, reset clears filters and deletes clamp page', async t => {
  let count = 0; const h = setup({ getUserInfo: async () => ++count === 2 ? { code: 403 } : ok([row()]) }); t.after(h.close)
  h.mount(); await flush(); await h.doRefresh(); assert.match(h.listError.value, /重试/); assert.equal(h.rows.value.length, 1)
  h.pagination.page = 4; h.conditionItems[0].value = '5574'; await h.doRefresh(); assert.equal(h.pagination.page, 1)
  await h.onResetSearch(); assert.equal(h.conditionItems[0].value, ''); assert.equal(h.listError.value, '')
})
test('identity switch clears old data, windows and filters; late old reads are ignored', async t => {
  const a = deferred(); let count = 0; const h = setup({ getUserInfo: () => ++count === 1 ? a.promise : Promise.resolve(ok([row({ id: 2 })])) }); t.after(h.close)
  h.mount(); await flush(); h.onResetPassword(row()); h.user.token = 'other-session'; await flush()
  assert.equal(h.passwordTarget.value, null); a.resolve(ok([row({ id: 1 })])); await flush(); assert.equal(h.rows.value[0].id, 2)
})
test('background and KeepAlive invalidate reads and confirmations, foreground/activation resumes once', async t => {
  const a = deferred(); let count = 0; const h = setup({ getUserInfo: () => ++count === 1 ? a.promise : Promise.resolve(ok([row({ id: 2 })])) }); t.after(h.close)
  h.mount(); await flush(); h.onDelete(row()); const confirmation = h.confirms.at(-1)
  h.visibility('hidden'); assert.equal(confirmation.closed, true); assert.equal(await confirmation.options.onBeforeOk(), false)
  a.resolve(ok([row({ id: 1 })])); await flush(); assert.deepEqual(h.rows.value, [])
  h.visibility('visible'); await flush(); assert.equal(count, 2)
  h.callbacks.deactivate.forEach(f => f()); h.callbacks.activate.forEach(f => f()); await flush(); assert.equal(count, 3)
})
test('delete confirmation returns false on failure, retains dialog, retries fixed snapshot and closes on success', async t => {
  let count = 0; const h = setup({ deleteUserInfo: async () => ++count === 1 ? { code: 400 } : ok() }); t.after(h.close)
  h.mount(); await flush(); const input = row({ id: '90071992547409931234' }); h.onDelete(input); input.id = 44
  const confirmation = h.confirms.at(-1); assert.equal(await confirmation.options.onBeforeOk(), false); assert.equal(confirmation.closed, false)
  assert.equal(await confirmation.options.onBeforeOk(), true); assert.equal(confirmation.closed, true)
  assert.equal(h.calls.filter(([name]) => name === 'deleteUserInfo').at(-1)[1], '90071992547409931234')
})
test('MCP key reset has physical duplicate lock and late result cannot notify switched user', async t => {
  const write = deferred(), h = setup({ resetUserApiKey: () => write.promise }); t.after(h.close)
  h.mount(); await flush(); h.onResetApiKey(row()); const confirmation = h.confirms.at(-1), task = confirmation.options.onBeforeOk()
  assert.equal(await confirmation.options.onBeforeOk(), false); h.user.userId = 2; await flush(); assert.notEqual(h.rowOperation.value, null)
  write.resolve(ok({ api_key: 'example-secret' })); assert.equal(await task, false); assert.equal(h.rowOperation.value, null); assert.equal(h.messages.some(([name]) => name === 'success'), false)
})
test('password migration guard keeps business restriction and reset failure can retry same snapshot', async t => {
  let n = 0; const h = setup({ resetUserPassword: async () => ++n === 1 ? { code: 400 } : ok() }); t.after(h.close)
  h.mount(); await flush(); h.onResetPassword(row({ requires_email_login_migration: true })); assert.equal(h.passwordTarget.value, null); assert.match(h.confirms.at(-1).options.title, /邮箱/)
  const input = row(); h.onResetPassword(input); input.id = 2; await h.onResetPasswordConfirm(); assert.match(h.passwordError.value, /重试/); assert.equal(h.passwordTarget.value.id, 0)
  await h.onResetPasswordConfirm(); assert.equal(h.passwordTarget.value, null); assert.equal(h.rowOperation.value, null); assert.equal(h.calls.filter(([name]) => name === 'resetUserPassword').at(-1)[1].id, 0)
})
test('cancelled password reset retains physical lock but late success never closes reopened window', async t => {
  const write = deferred(), h = setup({ resetUserPassword: () => write.promise }); t.after(h.close)
  h.mount(); await flush(); h.onResetPassword(row()); const task = h.onResetPasswordConfirm(); h.closePassword(); h.onResetPassword(row({ id: 2 })); assert.equal(h.passwordTarget.value, null)
  write.resolve(ok()); await task; assert.equal(h.messages.some(([name]) => name === 'success'), false)
  h.onResetPassword(row({ id: 2 })); assert.equal(h.passwordTarget.value.id, 2)
})
test('super admin switch only applies after success and sends fixed whitelist/department snapshot', async t => {
  const write = deferred(), h = setup({ putUserInfo: () => write.promise }); t.after(h.close)
  h.mount(); await flush(); const input = h.rows.value[0], task = h.onSuperAdminChange(input, true)
  input.department_ids.push(9); assert.equal(input.is_super_admin, false); assert.equal(await h.onSuperAdminChange(input, true), false)
  const payload = h.calls.find(([name]) => name === 'putUserInfo')[1]; assert.deepEqual(payload.department_ids, [0, 2]); assert.equal(payload.role, 0)
  write.resolve(ok()); assert.equal(await task, true); assert.equal(h.rowOperation.value, null)
})
test('super admin switch refusal leaves original state and reports failure without hiding controls by role', async t => {
  const h = setup({ putUserInfo: async () => ({ code: 400 }) }); t.after(h.close); h.mount(); await flush()
  assert.equal(await h.onSuperAdminChange(h.rows.value[0], true), false); assert.equal(h.rows.value[0].is_super_admin, false)
  assert.equal(h.messages.some(([name]) => name === 'error'), true)
})
test('own user change refreshes shared permission routes; refresh failure is separate and retryable', async t => {
  let count = 0; const h = setup({ routes: async () => { if (++count === 1) throw Error('offline') } }); t.after(h.close)
  h.mount(); await flush(); await h.onUserSaved(1); assert.match(h.routeRefreshError.value, /用户已保存/); assert.equal(h.routeRefreshing.value, false)
  await h.refreshOwnRoutes(); assert.equal(count, 2); assert.equal(h.routeRefreshError.value, '')
})
test('own user write completed in background refreshes routes after return without replaying write', async t => {
  const write = deferred(); let routes = 0; const h = setup({ putUserInfo: () => write.promise, routes: async () => { routes++ } }); t.after(h.close)
  h.mount(); await flush(); const task = h.onSuperAdminChange(row({ id: 1 }), true); h.visibility('hidden')
  write.resolve(ok()); assert.equal(await task, false); assert.equal(routes, 0)
  h.visibility('visible'); await flush(); assert.equal(routes, 1); assert.equal(h.calls.filter(([name]) => name === 'putUserInfo').length, 1)
})
test('editor completion releases parent wait and resumes paused required read without notifying another identity', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush(); h.onEditorBusy(true); h.visibility('hidden'); h.visibility('visible')
  const before = h.calls.length; h.onEditorCommitted(1, 'other-identity'); h.onEditorBusy(false); await flush()
  assert.ok(h.calls.length > before); assert.equal(h.routeRefreshing.value, false)
})
test('SFC scripts/templates/styles compile and registration super-admin field is unconditional', async () => {
  for (const file of ['index.vue', 'components/UserEditorDialog.vue']) {
    const filename = path.join(base, file), source = readFileSync(filename, 'utf8'), { descriptor, errors } = parse(source)
    assert.deepEqual(errors, []); const script = compileScript(descriptor, { id: file })
    const template = compileTemplate({ source: descriptor.template.content, filename, id: file, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: file, scoped: true })).errors, [])
  }
  const source = readFileSync(path.join(base, 'components/UserEditorDialog.vue'), 'utf8')
  assert.equal(source.includes('currentUser.is_super_admin'), false); assert.match(source, /label="超级管理员"/)
})
