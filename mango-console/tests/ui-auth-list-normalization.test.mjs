import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { uiAuthBase, uiAuthRecord } from './helpers/ui-auth-editor-harness.mjs'
import { setupUiAuthList, authListResponse } from './helpers/ui-auth-list-harness.mjs'
import { taskResponse } from './helpers/ui-auth-task-harness.mjs'
import * as taskStorage from '../src/utils/executor-task-observer.mjs'

test('finite list records retain display/editor fields, isolate JSON and keep zero/long IDs', t => {
  const h = setupUiAuthList(); t.after(h.close); const dto = h.load('auth-list-records.ts'), source = uiAuthRecord({ update_user: { id: 0, username: 'Example' } })
  const { rows, total } = dto.readUiAuthList(authListResponse([source])); assert.equal(total, 1); assert.equal(rows[0].id, 0); assert.equal(rows[0].test_env, 0)
  assert.equal(rows[0].update_user.username, 'Example'); assert.equal('cache_data' in rows[0], false); assert.equal(rows[0].project_product.id, 0)
  rows[0].manual_config.headers.example = 'Changed'; assert.equal(source.manual_config.headers.example, 'value')
  assert.equal(dto.readUiAuthListRecord(uiAuthRecord({ id: '90071992547409930000' })).id, '90071992547409930000')
  assert.match(dto.getAuthConfigText(dto.readUiAuthListRecord(uiAuthRecord({ auth_type: 2 }))), /登录接口 #0/)
})
test('list boundary rejects malformed envelopes, duplicate IDs and invalid row fields', t => {
  const h = setupUiAuthList(); t.after(h.close); const dto = h.load('auth-list-records.ts')
  for (const value of [{ code: 403 }, { code: 200, data: {}, totalSize: 0 }, authListResponse([], -1), authListResponse([], '1'), authListResponse([uiAuthRecord(), uiAuthRecord()]), authListResponse([uiAuthRecord({ id: null })]), authListResponse([uiAuthRecord({ refreshing: 'true' })])]) assert.throws(() => dto.readUiAuthList(value))
})
test('query keeps only supported scalar filters, pageSize, leaf product and zero without leaking draft fields', t => {
  const h = setupUiAuthList(); t.after(h.close); const dto = h.load('auth-list-records.ts')
  assert.deepEqual(dto.uiAuthListQuery({ id: '1,2', name: 'Example', test_env__in: '0,1', auth_type__in: '0', ignored: 'omit', update_user__in: null }, [7, 0], 2, 50), { page: 2, pageSize: 50, project_product: 0, id: '1,2', name: 'Example', test_env__in: '0,1', auth_type__in: '0' })
})
test('initial list and metadata load independently with their own loading and failure recovery', async t => {
  const list = deferred(), users = deferred(), enums = deferred(), h = setupUiAuthList({ getUiAuthConfig: () => list.promise, getUserName: () => users.promise, getEnum: () => enums.promise }); t.after(h.close)
  const mounting = h.mount(); await flush(); assert.equal(h.listLoading.value, true); assert.equal(h.usersLoading.value, true); assert.equal(h.enumsLoading.value, true)
  list.resolve(authListResponse()); await flush(); assert.equal(h.listLoading.value, false); assert.equal(h.rows.value.length, 1); assert.equal(h.usersLoading.value, true)
  users.reject(Error('network')); enums.reject(Error('network')); await mounting; assert.match(h.usersError.value, /失败/); assert.match(h.enumsError.value, /失败/)
})
test('same-query reads coalesce, while new filters supersede old responses and old finally', async t => {
  const first = deferred(), second = deferred(), h = setupUiAuthList({ getUiAuthConfig: query => query.name === 'New' ? second.promise : first.promise }); t.after(h.close)
  const mounting = h.mount(); await flush(); const duplicate = h.doRefresh(); assert.equal(h.reads.filter(x => x[0] === 'getUiAuthConfig').length, 1)
  h.conditionItems.find(x => x.key === 'name').value = 'New'; const searching = h.onSearchRefresh(); await flush()
  first.resolve(authListResponse([uiAuthRecord({ name: 'Old' })])); await mounting; await duplicate; assert.equal(h.listLoading.value, true); assert.equal(h.rows.value.length, 0)
  second.resolve(authListResponse([uiAuthRecord({ name: 'New' })])); await searching; assert.equal(h.rows.value[0].name, 'New'); assert.equal(h.listLoading.value, false)
})
test('metadata and list network errors can be retried independently without discarding valid other regions', async t => {
  let listFailure = true, usersFailure = true, enumsFailure = true
  const h = setupUiAuthList({ getUiAuthConfig: async () => { if (listFailure) throw Error('network'); return authListResponse() }, getUserName: async () => { if (usersFailure) throw Error('network'); return { code: 200, data: [{ key: 0, title: 'Recovered user' }] } }, getEnum: async () => { if (enumsFailure) throw Error('network') } }); t.after(h.close)
  await h.mount(); assert.match(h.listError.value, /失败/); assert.match(h.usersError.value, /失败/); assert.match(h.enumsError.value, /失败/)
  listFailure = false; await h.doRefresh(); assert.equal(h.rows.value.length, 1); assert.match(h.usersError.value, /失败/)
  usersFailure = false; await h.loadUsers(); assert.equal(h.userOptions.value[0].key, 0); assert.equal(h.usersError.value, ''); assert.match(h.enumsError.value, /失败/)
  enumsFailure = false; await h.loadEnums(); assert.equal(h.enumsError.value, ''); assert.equal(h.rows.value.length, 1)
})
test('pagination failure releases loading, preserves rows and can be retried', async t => {
  let fail = false; const h = setupUiAuthList({ getUiAuthConfig: async () => fail ? { code: 403 } : authListResponse() }); t.after(h.close); await h.mount()
  fail = true; h.pagination.page = 2; await h.pagination.onChange(); assert.equal(h.listLoading.value, false); assert.equal(h.rows.value.length, 1); assert.match(h.listError.value, /加载失败/)
  fail = false; assert.equal(await h.doRefresh(), true); assert.equal(h.listError.value, ''); assert.equal(h.pagination.page, 1)
})
test('last-page correction reloads the actual last page after deletion reduces total', async t => {
  const h = setupUiAuthList({ getUiAuthConfig: async query => authListResponse(query.page === 1 ? [uiAuthRecord()] : [], 1) }); t.after(h.close); await h.mount()
  h.pagination.page = 3; await h.doRefresh(); assert.equal(h.pagination.page, 1); assert.equal(h.rows.value.length, 1)
  assert.deepEqual(h.reads.filter(x => x[0] === 'getUiAuthConfig').slice(-2).map(x => x[1].page), [3, 1])
})
test('navigation uses the leaf product zero, multi-selects serialize and reset clears every filter', async t => {
  const h = setupUiAuthList(); t.after(h.close); await h.mount()
  h.conditionItems.find(x => x.key === 'test_env').value = [0, 3]; h.conditionItems.find(x => x.key === 'auth_type').value = [0]
  await h.onNavigationFilterChange({ projectProduct: [7, 0] }); assert.equal(h.normalizeQuery().project_product, 0); assert.equal(h.normalizeQuery().test_env__in, '0,3'); assert.equal(h.normalizeQuery().auth_type__in, '0')
  await h.onReset(); assert.deepEqual(h.normalizeQuery(), { page: 1, pageSize: 20 }); assert.equal(h.sidebarResetKey.value, 1)
})
test('status changes are backend-confirmed, immutable and locked until actual write settlement', async t => {
  const pending = deferred(), h = setupUiAuthList({ putUiAuthConfigStatus: () => pending.promise }); t.after(h.close); await h.mount(); const row = h.rows.value[0]
  const saving = h.onStatusChange(row, 0); assert.equal(h.isOperationLoading(0, 'status'), true); assert.equal(row.status, 1)
  assert.equal(await h.onClear(row), false); assert.equal(await h.onStatusChange(row, 0), false); assert.equal(h.writes.length, 1)
  pending.resolve({ code: 200 }); assert.equal(await saving, true); assert.equal(row.status, 1); assert.equal(h.rows.value[0].status, 0); assert.equal(h.busy(0), false)
})
test('failed status, refresh and clear operations release their locks without success and allow retry', async () => {
  for (const [method, api, action] of [['onStatusChange', 'putUiAuthConfigStatus', 'status'], ['onRefresh', 'postUiAuthConfigRefresh', 'refresh'], ['onClear', 'postUiAuthConfigClear', 'clear']]) {
    let fail = true; const h = setupUiAuthList({ [api]: async () => ({ code: fail ? 403 : 200 }) })
    try { await h.mount(); const row = h.rows.value[0]; assert.equal(await h[method](row, 0), false); assert.equal(h.isOperationLoading(0, action), false); assert.match(h.operationError.value, /失败/); assert.deepEqual(h.messages, [['error', h.operationError.value]]); fail = false; assert.equal(await h[method](row, 0), true) } finally { h.close() }
  }
})
test('network write failure keeps controlled status unchanged and permits another attempt', async t => {
  const h = setupUiAuthList({ putUiAuthConfigStatus: async () => { throw Error('example-private-network-error') } }); t.after(h.close); await h.mount()
  assert.equal(await h.onStatusChange(h.rows.value[0], 0), false); assert.equal(h.rows.value[0].status, 1); assert.equal(h.busy(0), false); assert.equal(h.operationError.value.includes('example-private-network-error'), false)
})
test('refresh action preserves original unsupported auth-type conditions and only sends fixed IDs', async t => {
  const h = setupUiAuthList(); t.after(h.close); await h.mount()
  for (const auth_type of [1, 3]) assert.equal(await h.onRefresh({ ...h.rows.value[0], auth_type }), false)
  assert.equal(h.writes.length, 0); const row = { ...h.rows.value[0], id: '90071992547409930000' }; await h.onRefresh(row); assert.deepEqual(h.writes[0], ['postUiAuthConfigRefresh', '90071992547409930000'])
})
test('delete uses onBeforeOk, captures ID zero, prevents duplicate dialogs and stays open for retry on failure', async t => {
  let fail = true; const h = setupUiAuthList({ deleteUiAuthConfig: async () => ({ code: fail ? 403 : 200 }) }); t.after(h.close); await h.mount()
  const row = { ...h.rows.value[0] }; h.onDelete(row); h.onDelete(row); assert.equal(h.confirmations.length, 1); const dialog = h.confirmations[0]
  assert.equal(dialog.onOk, undefined); assert.equal(dialog.okButtonProps.status, 'danger'); row.id = 2
  assert.equal(await dialog.onBeforeOk(), false); assert.equal(dialog.closed, false); assert.deepEqual(h.writes[0], ['deleteUiAuthConfig', 0])
  fail = false; assert.equal(await dialog.onBeforeOk(), true); assert.equal(dialog.closed, true)
})
test('delete cancellation and query changes invalidate confirmation callbacks before any write', async t => {
  const h = setupUiAuthList(); t.after(h.close); await h.mount()
  h.onDelete(h.rows.value[0]); const first = h.confirmations[0]; first.onCancel(); assert.equal(await first.onBeforeOk(), false)
  h.onDelete(h.rows.value[0]); const second = h.confirmations[1]; await h.onSearchRefresh(); assert.equal(second.closed, true); assert.equal(await second.onBeforeOk(), false); assert.deepEqual(h.writes, [])
})
test('cancelled pending delete keeps a physical row lock until settlement and does not reopen or toast', async t => {
  const pending = deferred(), h = setupUiAuthList({ deleteUiAuthConfig: () => pending.promise }); t.after(h.close); await h.mount()
  const row = h.rows.value[0]; h.onDelete(row); const dialog = h.confirmations[0], deleting = dialog.onBeforeOk(); dialog.onCancel(); h.onDelete(row)
  assert.equal(h.confirmations.length, 1); assert.equal(h.busy(0), true); pending.resolve({ code: 200 }); assert.equal(await deleting, true); assert.deepEqual(h.messages, []); assert.equal(h.busy(0), false)
})
test('authoritative re-read after a write supersedes an older in-flight list read without showing table loading', async t => {
  const stale = deferred(), fresh = deferred(); let reads = 0
  const h = setupUiAuthList({ getUiAuthConfig: () => ++reads === 1 ? Promise.resolve(authListResponse()) : reads === 2 ? stale.promise : fresh.promise }); t.after(h.close); await h.mount()
  const old = h.doRefresh(); await flush(); await h.onClear(h.rows.value[0]); await flush(); assert.equal(h.listLoading.value, false)
  stale.resolve(authListResponse([uiAuthRecord({ name: 'Stale' })])); await old; assert.notEqual(h.rows.value[0].name, 'Stale')
  fresh.resolve(authListResponse([uiAuthRecord({ name: 'Fresh' })])); await flush(); assert.equal(h.rows.value[0].name, 'Fresh')
})
test('identity changes clear sensitive rows and late operation feedback while new reads recover independently', async () => {
  for (const change of [h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.fullPath += '?id=2']) {
    const pending = deferred(), h = setupUiAuthList({ postUiAuthConfigClear: () => pending.promise })
    try { await h.mount(); const clearing = h.onClear(h.rows.value[0]); change(h); assert.equal(h.rows.value.length, 0); pending.resolve({ code: 200 }); await clearing; await flush(); assert.deepEqual(h.messages, []); assert.equal(h.rows.value.length, 1) } finally { h.close() }
  }
})
test('old identity list responses cannot overwrite fresh rows or release the newer read loading', async t => {
  const old = deferred(), fresh = deferred(); let calls = 0; const h = setupUiAuthList({ getUiAuthConfig: () => ++calls === 1 ? old.promise : fresh.promise }); t.after(h.close)
  const mounting = h.mount(); await flush(); h.user.roleId++; await flush(); old.resolve(authListResponse([uiAuthRecord({ name: 'Old role' })])); await mounting
  assert.equal(h.rows.value.length, 0); assert.equal(h.listLoading.value, true); fresh.resolve(authListResponse([uiAuthRecord({ name: 'New role' })])); await flush(); assert.equal(h.rows.value[0].name, 'New role')
})
test('editor saved event invalidates a pre-save request before authoritative reload', async t => {
  const old = deferred(), fresh = deferred(); let calls = 0
  const h = setupUiAuthList({ getUiAuthConfig: () => ++calls === 1 ? Promise.resolve(authListResponse()) : calls === 2 ? old.promise : fresh.promise }); t.after(h.close); await h.mount()
  const loadingOld = h.doRefresh(); await flush(); const loadingFresh = h.refreshAfterEditor(); await flush(); old.resolve(authListResponse([uiAuthRecord({ name: 'Before save' })])); await loadingOld
  assert.equal(h.listLoading.value, true); fresh.resolve(authListResponse([uiAuthRecord({ name: 'After save' })])); await loadingFresh; assert.equal(h.rows.value[0].name, 'After save')
})
test('background and KeepAlive suspend reads, invalidate dialogs and resume once with fresh data', async () => {
  for (const mode of ['background', 'keepAlive']) {
    const h = setupUiAuthList()
    try {
      await h.mount(); h.onDelete(h.rows.value[0]); const old = h.confirmations[0]
      if (mode === 'background') h.visibility('hidden'); else h.callbacks.deactivate.forEach(fn => fn())
      assert.equal(h.rows.value.length, 0); assert.equal(old.closed, true); const count = h.reads.length; await h.doRefresh(); assert.equal(h.reads.length, count)
      if (mode === 'background') h.visibility('visible'); else h.callbacks.activate.forEach(fn => fn())
      await flush(); assert.equal(h.rows.value.length, 1); assert.equal(await old.onBeforeOk(), false)
    } finally { h.close() }
  }
})
test('unmount ignores pending list and writes, removes lifecycle effects and never resumes requests', async t => {
  const pending = deferred(), h = setupUiAuthList({ postUiAuthConfigClear: () => pending.promise }); t.after(h.close); await h.mount()
  const clearing = h.onClear(h.rows.value[0]); h.callbacks.unmount.forEach(fn => fn()); const count = h.reads.length
  pending.resolve({ code: 200 }); await clearing; h.visibility('hidden'); h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); await flush()
  assert.deepEqual(h.messages, []); assert.equal(h.rows.value.length, 0); assert.equal(h.reads.length, count); assert.equal(h.busy(0), false)
})
function taskWindow() {
  const previous = globalThis.window, timers = new Map(), storage = new Map(); let id = 0
  globalThis.window = { setTimeout: fn => { const next = ++id; timers.set(next, fn); return next }, clearTimeout: key => timers.delete(key), sessionStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) } }
  return { timers, close: () => { globalThis.window = previous }, run: async () => { const values = [...timers]; timers.clear(); values.forEach(([, fn]) => fn()); await flush() } }
}
test('parent lifecycle pauses local observation, suppresses stale terminal reads and resumes without a second POST', async t => {
  const browser = taskWindow(), pending = deferred(); let calls = 0
  const h = setupUiAuthList({ observer: taskStorage, getUiAuthConfig: async () => authListResponse([uiAuthRecord({ auth_type: 1 })]), getExecutorTask: () => ++calls === 1 ? pending.promise : Promise.resolve(taskResponse(91, 0, 'start', 'success')) })
  t.after(() => { h.close(); browser.close() }); await h.mount(); await h.onAutoStart(h.rows.value[0]); assert.equal(h.listLoading.value, false); assert.equal(h.isAuthTaskLoading(0, 'start'), true)
  h.visibility('hidden'); assert.equal(browser.timers.size, 0); h.visibility('visible'); await flush(); assert.equal(calls, 1)
  pending.resolve(taskResponse(91, 0, 'start', 'success')); await flush(); assert.equal(h.messages.length, 0); await browser.run(); assert.equal(calls, 2); assert.match(h.messages[0][1], /浏览器已打开/)
  assert.equal(h.writes.filter(x => x[0] === 'postUiAuthConfigAutoStart').length, 1)
})
test('parent role switch invalidates task feedback and capture completion refreshes the list silently', async t => {
  const browser = taskWindow(), pending = deferred()
  const h = setupUiAuthList({ observer: taskStorage, getUiAuthConfig: async () => authListResponse([uiAuthRecord({ auth_type: 1 })]), getExecutorTask: taskId => taskId === 91 ? pending.promise : Promise.resolve(taskResponse(taskId, 0, 'capture', 'success')) })
  t.after(() => { h.close(); browser.close() }); await h.mount(); await h.onAutoStart(h.rows.value[0]); h.user.roleId++; await flush()
  pending.resolve(taskResponse(91, 0, 'start', 'success')); await flush(); assert.equal(h.messages.length, 0); assert.equal(browser.timers.size, 0)
  const initialReads = h.reads.filter(x => x[0] === 'getUiAuthConfig').length; await h.onAutoCapture(h.rows.value[0]); await flush()
  assert.equal(h.listLoading.value, false); assert.equal(h.reads.filter(x => x[0] === 'getUiAuthConfig').length, initialReads + 1); assert.match(h.messages[0][1], /提取并保存/)
})
test('parent SFC compiles with controlled switch, local loading, real feedback and finite row bindings', async () => {
  const filename = path.join(uiAuthBase, 'index.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'ui-auth-list' }), template = compileTemplate({ source: descriptor.template.content, filename, id: 'ui-auth-list', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, []); const style = await compileStyleAsync({ source: descriptor.styles[0].content, filename, id: 'ui-auth-list', scoped: true }); assert.deepEqual(style.errors, [])
  assert.match(descriptor.template.content, /:model-value="record.status === 1"/); assert.match(descriptor.template.content, /:loading="listLoading"/); assert.doesNotMatch(descriptor.template.content, /#feedback|default-checked/)
})
