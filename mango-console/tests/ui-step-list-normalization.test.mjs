import assert from 'node:assert/strict'
import test from 'node:test'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { stepHarness, stepRecords as r, stepRow, stepList } from './helpers/ui-step-list-harness.mjs'

test('finite DTO, independent drafts, zero and long IDs, write whitelist and query', () => {
  const source = stepRow({ id: '900719925474099399', extra: 'ignored' }), row = r.readStepListRow(source), draft = r.createStepDraft(row)
  row.module.name = 'Local'; assert.equal(source.module.name, 'Example module')
  draft.name = 'Edited'; draft.project_product = [2, 0]; assert.equal(row.name, 'Example step')
  assert.deepEqual(r.stepListPayload(draft, row.id), { id: row.id, parent_id: row.id, project_product: 0, module: 0, page: 0, name: 'Edited' })
  assert.deepEqual(r.stepListQuery({ project_product: [1, 0], module: 0, name: '', status__in: '2,3', page_id__in: '0,2' }, 1, 20), { page: 1, pageSize: 20, project_product: 0, module: 0, status__in: '2,3', page_id__in: '0,2' })
  assert.equal(r.stepListId(Number.MAX_SAFE_INTEGER + 1), null)
  assert.throws(() => r.stepListPayload({ ...draft, name: ' ' }, 0))
  assert.throws(() => r.readStepList(stepList([stepRow(), stepRow()])))
  assert.throws(() => r.readStepList({ code: 500, data: [], totalSize: 0 }))
})
test('independent search instances, collection queries and reset', async () => {
  const a = stepHarness(), b = stepHarness()
  try {
    a.conditionItems.find(item => item.key === 'page_id').value = [0, '900719925474099399']
    a.conditionItems.find(item => item.key === 'status').value = [2, 3]
    assert.deepEqual(b.conditionItems.find(item => item.key === 'page_id').value, [])
    await a.doRefresh(); assert.deepEqual(a.reads[0], ['getUiSteps', { page: 1, pageSize: 20, page_id__in: '0,900719925474099399', status__in: '2,3' }, false])
    a.pagination.page = 4; await a.onResetSearch(); assert.equal(a.pagination.page, 1)
    assert.deepEqual(a.conditionItems.find(item => item.key === 'page_id').value, [])
  } finally { b.cleanup(); a.cleanup() }
})
test('list and three option regions load independently and failed reads are retryable', async t => {
  const users = deferred(); let fail = true
  const h = stepHarness({ api: { getUserName: () => users.promise, getUiSteps: async () => { if (fail) throw Error(); return stepList() } } }); t.after(h.cleanup)
  h.initialize(); await flush(); assert.equal(h.usersLoading.value, true); assert.equal(h.listLoading.value, false); assert.equal(h.pagesLoading.value, false); assert.ok(h.listError.value)
  fail = false; await h.doRefresh(); assert.equal(h.rows.value[0].id, 0); assert.equal(h.listError.value, '')
  users.resolve({ code: 200, data: [{ key: 0, title: 'Current' }] }); await flush(); assert.equal(h.userOptions.value[0].title, 'Current')
})
test('new search invalidates older list; final page is corrected after deletion', async t => {
  const old = deferred(); let count = 0
  const h = stepHarness({ api: { getUiSteps: query => ++count === 1 ? old.promise : Promise.resolve(stepList(query.page > 1 ? [] : [stepRow({ name: 'Current' })], 1)) } }); t.after(h.cleanup)
  const reading = h.doRefresh(); await h.onSearch(); old.resolve(stepList([stepRow({ name: 'Old' })])); await reading
  assert.equal(h.rows.value[0].name, 'Current'); h.pagination.page = 9; await h.doRefresh(); assert.equal(h.pagination.page, 1)
})
test('polling handles waiting and running silently, retains data on failure and retries', async t => {
  let status = 2, fail = false
  const h = stepHarness({ api: { getUiSteps: async () => { if (fail) throw Error(); return stepList([stepRow({ status })]) } } }); t.after(h.cleanup)
  await h.doRefresh(); assert.equal(h.polling.enabled(), true)
  h.editorRef.value = { close() { throw Error('Polling must not close windows') } }
  status = 3; await h.polling.refresh(); assert.equal(h.listLoading.value, false); assert.equal(h.polling.enabled(), true)
  fail = true; await h.polling.refresh(); assert.equal(h.rows.value[0].status, 3); assert.equal(h.polling.enabled(), true); assert.ok(h.listError.value)
  fail = false; status = 1; await h.polling.refresh(); assert.equal(h.polling.enabled(), false); assert.equal(h.listError.value, '')
  h.editorRef.value = null
})
test('navigation page options reject older module responses and never own editor choices', async t => {
  const old = deferred(); let count = 0
  const h = stepHarness({ api: { getUiPageName: () => ++count === 1 ? old.promise : Promise.resolve({ code: 200, data: [{ key: 2, title: 'Current' }] }) } }); t.after(h.cleanup)
  await h.onSidebarFilterChange({ projectProduct: [2, 0], module: 0 }); await h.onSidebarFilterChange({ projectProduct: 0, module: 2 })
  old.resolve({ code: 200, data: [{ key: 1, title: 'Old' }] }); await flush(); assert.equal(h.pageOptions.value[0].key, 2)
  assert.equal(h.reads.find(call => call[0] === 'getUiPageName')[1], 0)
})
test('delete freezes batch IDs, prevents duplicate writes and closes after accepted deletion even if reread fails', async t => {
  const pending = deferred(), h = stepHarness({ api: { deleteUiSteps: () => pending.promise, getUiSteps: async () => { throw Error() } } }); t.after(h.cleanup)
  h.rows.value = [r.readStepListRow(stepRow()), r.readStepListRow(stepRow({ id: 2 }))]; h.onSelectionChange([0]); h.onDelete(null)
  h.selectedRowKeys.value = [2]; const writing = h.confirmations[0].onBeforeOk(); assert.equal(await h.confirmations[0].onBeforeOk(), false)
  assert.deepEqual(h.writes[0], ['deleteUiSteps', [0]])
  pending.resolve({ code: 200 }); assert.equal(await writing, true); await flush(); assert.equal(h.confirmations[0].closed, true); assert.equal(h.rows.value[0].id, 2); assert.ok(h.listError.value)
})
test('delete failure keeps confirmation open and is retryable', async t => {
  let fail = true; const h = stepHarness({ api: { deleteUiSteps: async () => ({ code: fail ? 500 : 200 }) } }); t.after(h.cleanup)
  h.onDelete(stepRow()); assert.equal(await h.confirmations[0].onBeforeOk(), false); assert.equal(h.confirmations[0].closed, false); assert.equal(h.deleting.value, false)
  fail = false; assert.equal(await h.confirmations[0].onBeforeOk(), true)
})
test('identity replacement invalidates confirmation but holds actual delete lock', async t => {
  const pending = deferred(), h = stepHarness({ api: { deleteUiSteps: () => pending.promise } }); t.after(h.cleanup)
  h.onDelete(stepRow()); const writing = h.confirmations[0].onBeforeOk(); h.user.roleId++; assert.equal(h.confirmations[0].closed, true); assert.equal(h.deleting.value, true)
  h.onDelete(stepRow({ id: 3 })); assert.equal(h.confirmations.length, 1); pending.resolve({ code: 200 }); assert.equal(await writing, false)
})
test('debug freezes ID and environment, prevents duplicate submissions including environment replacement', async t => {
  const pending = deferred(), h = stepHarness({ api: { getUiStepsTest: () => pending.promise } }); t.after(h.cleanup)
  const writing = h.onRunCase(stepRow({ id: '900719925474099399' })); await h.onRunCase(stepRow()); h.user.selected_environment = 2
  assert.notEqual(h.runningId.value, null); await h.onRunCase(stepRow()); assert.equal(h.reads.filter(call => call[0] === 'getUiStepsTest').length, 1)
  assert.deepEqual(h.reads[0], ['getUiStepsTest', '900719925474099399', 0]); pending.resolve({ code: 200 }); await writing; assert.equal(h.runningId.value, null); assert.equal(h.messages.length, 0)
})
test('debug and route entries preserve zero/long IDs and show retryable local errors', async t => {
  const h = stepHarness({ api: { getUiStepsTest: async () => { throw Error() } } }); t.after(h.cleanup)
  h.user.selected_environment = null; await h.onRunCase(stepRow()); assert.equal(h.reads.length, 0)
  h.user.selected_environment = 0; await h.onRunCase(stepRow()); assert.ok(h.actionError.value); assert.equal(h.runningId.value, null)
  h.onSteps(stepRow({ id: '900719925474099399' })); assert.deepEqual(h.routes[0].query, { id: '900719925474099399' })
})
test('editor has private draft, correct field mapping, defaults and whitelist', async t => {
  const h = stepHarness({ component: 'StepEditor' }); t.after(h.cleanup)
  const row = stepRow(); h.open(row); h.draft.name = 'Edited'; assert.equal(row.name, 'Example step'); assert.equal(h.draft.page, 0)
  h.close(); h.open(null, { projectProduct: 0, module: 0 }); assert.equal(h.draft.name, ''); assert.equal(h.draft.page, null)
  h.open(row); assert.equal(await h.save(), true); assert.deepEqual(h.writes[0], ['putUiSteps', { project_product: 0, module: 0, page: 0, name: 'Example step', id: 0, parent_id: 0 }])
})
test('editor validation and failed saves retain draft and permit retry', async t => {
  let fail = true; const h = stepHarness({ component: 'StepEditor', api: { postUiSteps: async () => ({ code: fail ? 500 : 200 }) } }); t.after(h.cleanup)
  h.open(); assert.equal(await h.save(), false); assert.equal(h.writes.length, 0)
  Object.assign(h.draft, { project_product: [3, 0], module: 0, page: 0, name: 'New' }); assert.equal(await h.save(), false); assert.equal(h.draft.name, 'New'); assert.equal(h.saving.value, false)
  fail = false; assert.equal(await h.save(), true); assert.equal(h.visible.value, false)
})
test('editor module options reject A-B-A responses and never clear a newer selection on failure', async t => {
  const old = deferred(); let count = 0
  const h = stepHarness({ component: 'StepEditor', api: { getUiPageName: () => ++count === 1 ? old.promise : Promise.resolve({ code: 200, data: [{ key: 2, title: 'Current' }] }) } }); t.after(h.cleanup)
  h.open(stepRow()); h.draft.module = 2; h.changeModule(); h.draft.page = 2; await flush(); old.reject(Error()); await flush()
  assert.equal(h.draft.page, 2); assert.equal(h.pagesError.value, ''); assert.equal(h.pageOptions.value[0].key, 2)
})
test('editor actual lock and submitted snapshot survive close/reopen/identity replacement', async t => {
  const pending = deferred(), h = stepHarness({ component: 'StepEditor', api: { putUiSteps: () => pending.promise } }); t.after(h.cleanup)
  h.open(stepRow()); const writing = h.save(); h.draft.name = 'After'; assert.equal(await h.save(), false); h.user.roleId++; h.open(stepRow({ id: 2 })); assert.equal(h.visible.value, false)
  pending.resolve({ code: 200 }); assert.equal(await writing, false); assert.equal(h.writes[0][1].name, 'Example step'); assert.equal(h.saving.value, false)
})
test('reference drawer rejects replaced/closed responses; failure supports local retry', async t => {
  const old = deferred(); let count = 0, fail = false
  const h = stepHarness({ component: 'StepReferencesPanel', api: { getUiPageStepReferencedCases: () => ++count === 1 ? old.promise : fail ? Promise.reject(Error()) : Promise.resolve({ code: 200, data: [stepRow({ id: 2 })] }) } }); t.after(h.cleanup)
  h.open(stepRow()); h.open(stepRow({ id: 3 })); await flush(); old.resolve({ code: 200, data: [stepRow({ id: 1 })] }); await flush(); assert.equal(h.rows.value[0].id, 2)
  fail = true; await h.loadReferences(); assert.ok(h.error.value); assert.equal(h.loading.value, false); fail = false; await h.loadReferences(); assert.equal(h.error.value, '')
  h.openCase(h.rows.value[0]); assert.equal(h.selectedCase.value.id, 2); h.close(); assert.equal(h.caseVisible.value, false); assert.equal(h.selectedCase.value, null)
})
test('reference nested case uses zero ID and closes on context replacement', async t => {
  const h = stepHarness({ component: 'StepReferencesPanel' }); t.after(h.cleanup)
  h.open(stepRow()); await flush(); h.openCase(h.rows.value[0]); assert.equal(h.caseVisible.value, true); assert.equal(h.selectedCase.value.id, 0)
  h.user.token = 'example-replacement'; assert.equal(h.visible.value, false); assert.equal(h.caseVisible.value, false); assert.equal(h.rows.value.length, 0)
})
test('background, KeepAlive, route A-B-A and unmount invalidate old reads and restart only in active context', async () => {
  for (const pause of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn()), h => { h.route.path = '/example/other'; h.route.fullPath = '/example/other' }, h => h.callbacks.unmount.forEach(fn => fn())]) {
    const old = deferred(), h = stepHarness({ api: { getUiSteps: () => old.promise } })
    try { h.mount(); pause(h); old.resolve(stepList()); await flush(); assert.equal(h.rows.value.length, 0); assert.equal(h.listLoading.value, false); assert.equal(h.polling.enabled(), false) } finally { h.cleanup() }
  }
  const h = stepHarness(); try { h.mount(); await flush(); h.visibility('hidden'); h.visibility('visible'); await flush(); assert.equal(h.rows.value.length, 1); assert.equal(h.polling.enabled(), true) } finally { h.cleanup() }
})
test('API paths and methods remain stable with zero/long and mixed IDs', () => {
  const calls = [], api = loadModule('src/api/uitest/page-steps.ts', { '@/api/http': Object.fromEntries(['get', 'post', 'put', 'deleted'].map(method => [method, request => calls.push([method, request.url, request.data()])])) })
  api.deleteUiSteps([0, '900719925474099399']); api.getUiPageStepReferencedCases(0); api.putUiSteps({ id: 0, parent_id: 0 }); api.getUiStepsTest('900719925474099399', 0)
  assert.deepEqual(calls.slice(0, 3), [['deleted', '/ui/page/steps', { id: [0, '900719925474099399'] }], ['get', '/ui/page/steps/cases', { page_step_id: 0 }], ['put', '/ui/page/steps', { id: 0, parent_id: 0 }]])
  assert.equal(calls[3][2].page_step_id, '900719925474099399'); assert.equal(calls[3][2].te, 0)
})
test('closed/reopened editor ignores a late option response, and option errors retry locally', async t => {
  const old = deferred(); let count = 0, fail = true
  const h = stepHarness({ component: 'StepEditor', api: { getUiPageName: () => ++count === 1 ? old.promise : fail ? Promise.reject(Error()) : Promise.resolve({ code: 200, data: [{ key: 2, title: 'Current' }] }) } }); t.after(h.cleanup)
  h.open(stepRow()); h.close(); h.open(stepRow({ id: 2, page: { id: 2, name: 'Current' } })); await flush()
  assert.ok(h.pagesError.value); assert.equal(h.draft.page, 2); old.resolve({ code: 200, data: [{ key: 1, title: 'Old' }] }); await flush(); assert.equal(h.pageOptions.value[0].key, 2)
  fail = false; await h.loadPages(); assert.equal(h.pagesError.value, ''); assert.equal(h.pageOptions.value[0].key, 2)
})
test('search invalidates unsubmitted deletion and stale accepted saves only request a fresh reconciliation', async () => {
  const a = stepHarness(); try { a.onDelete(stepRow()); const confirm = a.confirmations[0]; await a.onSearch(); assert.equal(confirm.closed, true); assert.equal(await confirm.onBeforeOk(), false); assert.equal(a.writes.length, 0) } finally { a.cleanup() }
  const pending = deferred(), b = stepHarness({ component: 'StepEditor', api: { putUiSteps: () => pending.promise } })
  try { b.open(stepRow()); const write = b.save(); b.user.roleId++; pending.resolve({ code: 200 }); assert.equal(await write, false); assert.equal(b.events.some(([name]) => name === 'saved'), false); assert.equal(b.events.some(([name]) => name === 'reconcile'), true) } finally { b.cleanup() }
})
test('editor and reference window background/unmount reject late responses and close nested content', async () => {
  for (const component of ['StepEditor', 'StepReferencesPanel']) {
    for (const pause of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn()), h => h.callbacks.unmount.forEach(fn => fn())]) {
      const old = deferred(), h = stepHarness({ component, api: { getUiPageName: () => old.promise, getUiPageStepReferencedCases: () => old.promise } })
      try { h.mount(); h.open(stepRow()); pause(h); old.resolve({ code: 200, data: [] }); await flush(); assert.equal(h.visible.value, false); assert.equal(component === 'StepEditor' ? h.pagesLoading.value : h.loading.value, false); assert.equal(component === 'StepEditor' ? h.pageOptions.value.length : h.rows.value.length, 0) } finally { h.cleanup() }
    }
  }
})
test('editor scope changes cannot turn an unfinished physical save into another submission', async t => {
  const old = deferred(), h = stepHarness({ component: 'StepEditor', api: { putUiSteps: () => old.promise } }); t.after(h.cleanup)
  h.mount(); h.open(stepRow()); const write = h.save(); h.visibility('hidden'); h.visibility('visible'); h.open(stepRow({ id: 4 })); assert.equal(h.visible.value, false); assert.equal(h.saving.value, true)
  old.reject(Error()); assert.equal(await write, false); assert.equal(h.saving.value, false); assert.equal(h.error.value, '')
  h.open(stepRow({ id: 4 })); assert.equal(h.editingId.value, 4)
})
test('outdated identity option reads cannot clear new loading or repopulate old records', async t => {
  const old = deferred(), newer = deferred(); let count = 0
  const h = stepHarness({ api: { getUserName: () => ++count === 1 ? old.promise : newer.promise } }); t.after(h.cleanup)
  const first = h.loadUsers(); h.user.roleId++; const second = h.loadUsers(); old.resolve({ code: 200, data: [{ key: 1, title: 'Old' }] }); await first
  assert.equal(h.usersLoading.value, true); assert.equal(h.userOptions.value.length, 0)
  newer.resolve({ code: 200, data: [{ key: 2, title: 'Current' }] }); await second; assert.equal(h.usersLoading.value, false); assert.equal(h.userOptions.value[0].key, 2)
})
