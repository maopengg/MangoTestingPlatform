import assert from 'node:assert/strict'
import test from 'node:test'
import { deferred, flush, method } from './helpers/case-details-harness.mjs'
import { ref } from 'vue'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { pageHarness, records, pageRow, pageList } from './helpers/ui-page-list-harness.mjs'

test('page DTO and payload preserve zero/long IDs, private drafts and the editable whitelist', () => {
  const input = pageRow({ id: '900719925474099399', extra: 'not writable' }), row = records.readUiPage(input), draft = records.createPageDraft(row)
  row.project_product.name = 'Local'; assert.equal(input.project_product.name, 'Example product')
  draft.name = 'Edited'; draft.project_product = [3, 0]; assert.equal(row.name, 'Example page')
  assert.deepEqual(records.pagePayload(draft, row.id), { id: '900719925474099399', name: 'Edited', url: 'https://example.com/page', project_product: 0, module: 0 })
  assert.equal(records.createPageDraft(null, { projectProduct: 0, module: 0 }).module, 0)
  assert.equal(records.pageId(Number.MAX_SAFE_INTEGER + 1), null)
  assert.throws(() => records.pagePayload({ ...draft, name: ' ' }, 0)); assert.throws(() => records.readPageList(pageList([pageRow(), pageRow()])))
  assert.throws(() => records.readPageList({ code: 500, data: [], totalSize: 0 }))
})
test('two page instances own independent searches; multiple filters reset to arrays and query omits empties', async () => {
  const a = pageHarness(), b = pageHarness()
  try {
    a.conditionItems.find(item => item.key === 'name').value = 'Example'
    a.conditionItems.find(item => item.key === 'project_product').value = [4, 0]
    a.conditionItems.find(item => item.key === 'project_product__ui_client_type').value = [0, 2]
    a.conditionItems.find(item => item.key === 'update_user').value = [0]
    assert.equal(b.conditionItems.find(item => item.key === 'name').value, '')
    await a.doRefresh(); assert.deepEqual(a.reads[0][1], { page: 1, pageSize: 20, name: 'Example', project_product: 0, project_product__ui_client_type__in: '0,2', update_user__in: '0' })
    a.pagination.page = 4; await a.onResetSearch(); assert.equal(a.pagination.page, 1)
    assert.deepEqual(a.conditionItems.find(item => item.key === 'update_user').value, [])
    assert.deepEqual(a.reads.at(-1)[1], { page: 1, pageSize: 20 })
  } finally { b.cleanup(); a.cleanup() }
})
test('list, users and client options resolve independently and failures support local retry', async t => {
  const pending = deferred(); let fail = true
  const h = pageHarness({ api: { getUserName: () => pending.promise, getUiPage: async () => { if (fail) throw Error('Example unavailable'); return pageList() } } }); t.after(h.cleanup)
  h.initialize(); await flush(); assert.equal(h.listLoading.value, false); assert.equal(h.usersLoading.value, true); assert.equal(h.enumsLoading.value, false); assert.ok(h.listError.value)
  fail = false; assert.equal(await h.doRefresh(), true); assert.equal(h.listError.value, ''); assert.equal(h.rows.value[0].id, 0)
  pending.resolve({ code: 200, data: [{ key: 0, title: 'Example' }] }); await flush(); assert.equal(h.userOptions.value[0].key, 0)
})
test('new search resets pagination and rejects an older list response', async t => {
  const pending = deferred(); let count = 0
  const h = pageHarness({ api: { getUiPage: () => ++count === 1 ? pending.promise : Promise.resolve(pageList([pageRow({ name: 'Current' })])) } }); t.after(h.cleanup)
  const old = h.doRefresh(); h.pagination.page = 3; await h.onSearch(); pending.resolve(pageList([pageRow({ name: 'Old' })])); await old
  assert.equal(h.rows.value[0].name, 'Current'); assert.equal(h.pagination.page, 1); assert.equal(h.listLoading.value, false)
})
test('page requests preserve descendant selection as the original exact-module protocol and recover an invalid last page', async t => {
  const h = pageHarness({ api: { getUiPage: async query => query.page > 1 ? pageList([], 1) : pageList() } }); t.after(h.cleanup)
  await h.onSidebarFilterChange({ projectProduct: [2, 0], module: 0 }); assert.equal(h.reads[0][1].module, 0); assert.equal(h.reads[0][1].project_product, 0)
  h.pagination.page = 4; await h.doRefresh(); assert.equal(h.pagination.page, 1); assert.equal(h.rows.value.length, 1)
})
test('user options and enum failures are independent and explicitly retryable', async t => {
  let fail = true; const h = pageHarness({ api: { getUserName: async () => { if (fail) throw Error(); return { code: 200, data: [] } } }, enums: { getEnum: async () => { if (fail) throw Error() } } }); t.after(h.cleanup)
  await Promise.all([h.loadUsers(), h.loadEnums()]); assert.ok(h.usersError.value); assert.ok(h.enumsError.value); assert.equal(h.usersLoading.value, false)
  fail = false; await Promise.all([h.loadUsers(), h.loadEnums()]); assert.equal(h.usersError.value, ''); assert.equal(h.enumsError.value, ''); assert.equal(h.clientOptions.value[0].key, 0)
})
test('role/token/permission/environment and route A-B-A reject old reads', async () => {
  for (const change of [h => h.user.roleId++, h => h.user.token = 'example-next', h => h.permission.permissionKeys.push('ui.page:change'), h => h.user.selected_environment++, h => { const path = h.route.fullPath; h.route.fullPath = '/example'; h.route.fullPath = path }]) {
    const pending = deferred(), h = pageHarness({ api: { getUiPage: () => pending.promise } })
    try { const loading = h.doRefresh(); change(h); pending.resolve(pageList()); await loading; assert.equal(h.rows.value.length, 0); assert.equal(h.listLoading.value, false) } finally { h.cleanup() }
  }
})
test('background/KeepAlive closes owned windows, pauses requests and resumes the current list', async t => {
  const h = pageHarness(); t.after(h.cleanup); let closed = 0; h.editorRef.value = { close() { closed++ }, open() {} }
  h.mount(); await flush(); h.visibility('hidden'); assert.equal(h.rows.value.length, 0); assert.ok(closed)
  h.callbacks.deactivate.forEach(fn => fn()); const count = h.reads.length; h.visibility('visible'); await flush(); assert.equal(h.reads.length, count)
  h.callbacks.activate.forEach(fn => fn()); await flush(); assert.ok(h.reads.length > count); assert.equal(h.rows.value.length, 1)
})
test('new page defaults use the navigation selection and editing uses a normalized private record', t => {
  const h = pageHarness(); t.after(h.cleanup); const opened = []
  h.editorRef.value = { open: (...args) => opened.push(args), close() {} }
  h.conditionItems.find(item => item.key === 'project_product').value = 0; h.conditionItems.find(item => item.key === 'module').value = 0
  h.onAdd(); assert.deepEqual(opened[0], [null, { projectProduct: 0, module: 0 }])
  const row = pageRow(); h.onUpdate(row); opened[1][0].project_product.name = 'Draft'; assert.equal(row.project_product.name, 'Example product')
  h.editingBusy.value = true; h.onAdd(); assert.equal(opened.length, 2)
})
test('selection accepts only visible IDs and navigation preserves long ID without numeric coercion', async t => {
  const id = '900719925474099399', h = pageHarness({ api: { getUiPage: async () => pageList([pageRow({ id })]) } }); t.after(h.cleanup)
  await h.doRefresh(); h.onSelectionChange([id, 9, {}]); assert.deepEqual(h.selectedRowKeys.value, [id])
  h.onElements(h.rows.value[0]); assert.deepEqual(h.routes[0], { path: '/uitest/page/elements', query: { id } }); assert.equal(h.pageData.record.id, id)
})
test('delete confirmation freezes original IDs, failure retains selection and does not refresh', async t => {
  let fail = true; const h = pageHarness({ api: { deleteUiPage: async () => { if (fail) throw Error(); return { code: 200 } } } }); t.after(h.cleanup)
  h.selectedRowKeys.value = [0, '900719925474099399']; h.onDelete(null); h.selectedRowKeys.value = [9]
  assert.equal(await h.confirmations[0].onBeforeOk(), false); assert.deepEqual(h.writes[0][1], [0, '900719925474099399']); assert.deepEqual(h.selectedRowKeys.value, [9]); assert.equal(h.reads.length, 0)
  fail = false; assert.equal(await h.confirmations[0].onBeforeOk(), true); assert.equal(h.deleting.value, false)
})
test('accepted delete survives GET failure and duplicate clicks issue exactly one request', async t => {
  const pending = deferred(), h = pageHarness({ api: { deleteUiPage: () => pending.promise, getUiPage: async () => { throw Error() } } }); t.after(h.cleanup)
  h.rows.value = [records.readUiPage(pageRow())]; h.onDelete(h.rows.value[0]); const deleting = h.confirmations[0].onBeforeOk(); assert.equal(await h.confirmations[0].onBeforeOk(), false)
  pending.resolve({ code: 200 }); assert.equal(await deleting, true); await flush(); assert.equal(h.rows.value.length, 0); assert.ok(h.listError.value); assert.equal(h.writes.length, 1)
})
test('context replacement closes confirmation without releasing an outstanding delete lock', async t => {
  const pending = deferred(), h = pageHarness({ api: { deleteUiPage: () => pending.promise } }); t.after(h.cleanup)
  h.onDelete(pageRow()); const writing = h.confirmations[0].onBeforeOk(); h.user.roleId++; assert.equal(h.confirmations[0].closed, true); assert.equal(h.deleting.value, true)
  h.onDelete(pageRow({ id: 2 })); assert.equal(h.confirmations.length, 1); pending.resolve({ code: 200 }); assert.equal(await writing, false); assert.equal(h.reads.length, 0)
})
test('filter change invalidates an unsubmitted confirmation', async t => {
  const h = pageHarness(); t.after(h.cleanup); h.onDelete(pageRow()); const confirm = h.confirmations[0]; await h.onSearch(); assert.equal(confirm.closed, true); assert.equal(await confirm.onBeforeOk(), false); assert.equal(h.writes.length, 0)
})
test('editor cancel/reopen resets private drafts, keeps zero IDs and saves only writable fields', async t => {
  const h = pageHarness({ component: true }); t.after(h.cleanup)
  const row = pageRow(); h.open(row); h.draft.name = 'Edited'; assert.equal(row.name, 'Example page'); h.close(); h.open(null, { projectProduct: 0, module: 0 }); assert.equal(h.draft.name, '')
  h.open(pageRow({ id: 0 })); h.draft.name = 'Saved'; assert.equal(await h.save(), true)
  assert.deepEqual(h.writes[0], ['putUiPage', { id: 0, project_product: 0, module: 0, name: 'Saved', url: 'https://example.com/page' }]); assert.equal(h.visible.value, false); assert.ok(h.events.some(([name]) => name === 'saved'))
})
test('editor validation and write failures keep the draft and allow explicit retry', async t => {
  let fail = true; const h = pageHarness({ component: true, api: { postUiPage: async () => { if (fail) throw Error(); return { code: 200 } } } }); t.after(h.cleanup)
  h.open(); assert.equal(await h.save(), false); assert.equal(h.writes.length, 0)
  Object.assign(h.draft, { project_product: [3, 0], module: 0, name: 'Example', url: 'https://example.com' }); assert.equal(await h.save(), false); assert.equal(h.saving.value, false); assert.equal(h.draft.name, 'Example'); assert.ok(h.error.value)
  fail = false; assert.equal(await h.save(), true); assert.equal(h.writes[1][1].project_product, 0)
})
test('editor write snapshot and actual lock survive close and identity replacement; stale acceptance never saves a new window', async t => {
  const pending = deferred(), h = pageHarness({ component: true, api: { putUiPage: () => pending.promise } }); t.after(h.cleanup)
  h.open(pageRow()); const writing = h.save(); h.draft.name = 'After'; assert.equal(await h.save(), false); h.user.roleId++; assert.equal(h.visible.value, false); h.open(pageRow({ id: 2 })); assert.equal(h.visible.value, false)
  assert.equal(h.saving.value, true); pending.resolve({ code: 200 }); assert.equal(await writing, false); assert.equal(h.writes[0][1].name, 'Example page'); assert.equal(h.events.some(([name]) => name === 'saved'), false); assert.equal(h.saving.value, false)
})
test('editor hide and unmount invalidate unfinished saves without keeping a loading latch', async () => {
  for (const change of [h => { h.mount(); h.visibility('hidden') }, h => h.callbacks.unmount.forEach(fn => fn())]) {
    const pending = deferred(), h = pageHarness({ component: true, api: { putUiPage: () => pending.promise } })
    try { h.open(pageRow()); const writing = h.save(); change(h); pending.reject(Error()); assert.equal(await writing, false); assert.equal(h.visible.value, false); assert.equal(h.saving.value, false); assert.equal(h.error.value, '') } finally { h.cleanup() }
  }
})
test('page API keeps existing HTTP paths/methods, payloads, zero and mixed long IDs', () => {
  const calls = [], api = loadModule('src/api/uitest/page.ts', { '@/api/http': Object.fromEntries(['get', 'post', 'put', 'deleted'].map(method => [method, request => calls.push([method, request.url, request.data()])])) })
  api.getUiPage({ page: 1, pageSize: 20 }); api.postUiPage({ name: 'Example' }); api.putUiPage({ id: 0 }); api.deleteUiPage('900719925474099399'); api.deleteUiPage([0, '900719925474099399'])
  assert.deepEqual(calls, [['get', '/ui/page', { page: 1, pageSize: 20 }], ['post', '/ui/page', { name: 'Example' }], ['put', '/ui/page', { id: 0 }], ['deleted', '/ui/page', { id: '900719925474099399' }], ['deleted', '/ui/page', { id: [0, '900719925474099399'] }]])
})
test('reset and identity changes remove the previous navigation defaults before a new editor opens', async t => {
  const h = pageHarness(), opened = []; t.after(h.cleanup)
  h.editorRef.value = { open: (...args) => opened.push(args), close() {} }
  await h.onSidebarFilterChange({ projectProduct: 0, module: 0 }); await h.onResetSearch(); h.onAdd()
  assert.deepEqual(opened.at(-1), [null, { projectProduct: null, module: null }])
  await h.onSidebarFilterChange({ projectProduct: 0, module: 0 }); h.user.roleId++; h.onAdd()
  assert.deepEqual(opened.at(-1), [null, { projectProduct: null, module: null }]); assert.equal(h.pagination.page, 1)
})
test('old options cannot populate a replacement identity or end a newer loading indicator', async t => {
  const oldUsers = deferred(), currentUsers = deferred(), oldEnums = deferred(), currentEnums = deferred(); let users = 0, enums = 0
  const h = pageHarness({ api: { getUserName: () => ++users === 1 ? oldUsers.promise : currentUsers.promise }, enums: { getEnum: () => ++enums === 1 ? oldEnums.promise : currentEnums.promise } }); t.after(h.cleanup)
  const firstUsers = h.loadUsers(), firstEnums = h.loadEnums(); h.user.roleId++; const nextUsers = h.loadUsers(), nextEnums = h.loadEnums()
  oldUsers.resolve({ code: 200, data: [{ key: 2, title: 'Old' }] }); oldEnums.resolve(); await Promise.all([firstUsers, firstEnums])
  assert.deepEqual(h.userOptions.value, []); assert.deepEqual(h.clientOptions.value, []); assert.equal(h.usersLoading.value, true); assert.equal(h.enumsLoading.value, true)
  currentUsers.resolve({ code: 200, data: [{ key: 0, title: 'Current' }] }); currentEnums.resolve(); await Promise.all([nextUsers, nextEnums]); assert.equal(h.userOptions.value[0].title, 'Current'); assert.equal(h.usersLoading.value, false)
})
test('failed lazy route navigation reports a local error only to its current context', async () => {
  for (const stale of [false, true]) {
    const pending = deferred(), actionError = ref(''); let current = true
    const navigate = method('onElements', { scope: { available: () => true, capture: () => () => current }, readUiPage: records.readUiPage, pageData: { setRecord() {} }, router: { push: () => pending.promise }, actionError }, 'src/views/uitest/page/index.vue')
    navigate(pageRow()); if (stale) current = false; pending.reject(Error('Example lazy route failure')); await flush()
    assert.equal(Boolean(actionError.value), !stale)
  }
})
