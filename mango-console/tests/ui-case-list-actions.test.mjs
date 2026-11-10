import assert from 'node:assert/strict'
import test from 'node:test'
import { uiCaseHarness, caseRow, caseResponse } from './helpers/ui-case-list-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const long = '90071992547409930000'
test('delete confirmation fixes original IDs even if selection changes before confirming', async t => {
  const h = uiCaseHarness({ api: { getUiCase: async () => caseResponse([caseRow(), caseRow({ id: long })]) } }); t.after(h.cleanup); await h.mount(); await flush()
  h.selectedRowKeys.value = [0]; assert.equal(h.actions.remove(h.selectedRowKeys.value), true); h.selectedRowKeys.value = [long]; assert.equal(await h.confirmations[0].onBeforeOk(), true); assert.deepEqual(h.writes[0], ['deleteUiCase', 0]); assert.equal(h.confirmations[0].closed, true)
  assert.equal(h.actions.remove([long]), true)
})
test('actual request stays locked through refresh and old reads cannot override acknowledged state', async t => {
  const write = deferred(), refresh = deferred(); let count = 0
  const h = uiCaseHarness({ api: { getUiCase: () => ++count === 1 ? Promise.resolve(caseResponse()) : refresh.promise, postUiCaseCopy: () => write.promise } }); t.after(h.cleanup); await h.mount(); await flush()
  const copying = h.actions.copy(0); await flush(); assert.equal(h.actions.pending.value.kind, 'copy'); assert.equal(await h.actions.run(0), false); write.resolve({ code: 200 }); await flush(); assert.equal(h.actions.pending.value.kind, 'copy'); refresh.resolve(caseResponse()); assert.equal(await copying, true); assert.equal(h.actions.pending.value, null)
})
test('cancelled/invalidated confirmations cannot dispatch after identity changes or A-B-A', async () => {
  for (const change of [h => h.user.roleId++, h => h.permission.permissionKeys.push('example:read'), h => { h.user.selected_environment = 2; h.user.selected_environment = 0 }, h => h.visibility('hidden')]) {
    const h = uiCaseHarness()
    try { await h.mount(); await flush(); h.actions.remove([0]); change(h); assert.equal(h.confirmations[0].closed, true); assert.equal(await h.confirmations[0].onBeforeOk(), false); assert.equal(h.writes.length, 0) } finally { h.cleanup() }
  }
})
test('stale write retains physical lock but cannot notify or refresh a replacement identity', async t => {
  const pending = deferred(), h = uiCaseHarness({ api: { postUiCaseCopy: () => pending.promise } }); t.after(h.cleanup); await h.mount(); await flush()
  const copying = h.actions.copy(0); await flush(); h.user.token = 'example-new'; await flush(); const reads = h.reads.length, messages = h.messages.length; assert.equal(h.actions.pending.value.kind, 'copy'); assert.equal(await h.actions.copy(0), false); pending.resolve({ code: 200 }); assert.equal(await copying, false); assert.equal(h.actions.pending.value, null); assert.equal(h.reads.length, reads); assert.equal(h.messages.length, messages)
})
test('single and batch execution preserve zero environment and long IDs, reject missing environment and multiple projects', async t => {
  const h = uiCaseHarness({ api: { getUiCase: async () => caseResponse([caseRow({ id: long }), caseRow({ id: 2, project_product: { id: 2, project: { id: 2, name: 'Other project' } } })]) } }); t.after(h.cleanup); await h.mount(); await flush()
  assert.equal(await h.actions.run(long), true); assert.deepEqual(h.writes[0], ['getUiCaseRun', long, 0]); assert.equal(h.actions.batchRun([long, 2]), false)
  assert.equal(h.actions.batchRun([long]), true); await h.confirmations[0].onBeforeOk(); assert.deepEqual(h.writes[1], ['postUiRunCaseBatch', [long], 0]); h.user.selected_environment = null; await flush(); assert.equal(await h.actions.run(long), false)
})
test('publication respects business transitions, revalidates changed rows and keeps acknowledged status after refresh failure', async t => {
  let failRead = false; const h = uiCaseHarness({ api: { getUiCase: async () => { if (failRead) throw Error('network'); return caseResponse() } } }); t.after(h.cleanup); await h.mount(); await flush()
  h.list.rows.value[0].status = 0; assert.equal(h.actions.publication(0, 'prepublished'), false); h.list.rows.value[0].status = 1
  assert.equal(h.actions.publication(0, 'prepublished'), true); h.list.rows.value[0].publication_status = 'published'; assert.equal(await h.confirmations[0].onBeforeOk(), false); assert.equal(h.writes.length, 0)
  h.list.rows.value[0].publication_status = 'unpublished'; h.actions.publication(0, 'prepublished'); failRead = true; assert.equal(await h.confirmations[1].onBeforeOk(), true); assert.equal(h.list.rows.value[0].publication_status, 'prepublished'); assert.match(h.list.error.value, /重试/)
})
test('delete success followed by failed list reload preserves acknowledged deletion and retries GET only', async t => {
  let fail = false; const h = uiCaseHarness({ api: { getUiCase: async () => { if (fail) throw Error('network'); return caseResponse() } } }); t.after(h.cleanup); await h.mount(); await flush(); h.actions.remove([0]); fail = true
  assert.equal(await h.confirmations[0].onBeforeOk(), true); assert.equal(h.list.rows.value.length, 0); assert.equal(h.pagination.pageCount, 0); assert.match(h.list.error.value, /重试/); fail = false; await h.doRefresh(); assert.equal(h.writes.length, 1)
})
test('backend-rejected mutation releases lock, leaves state untouched and allows retry', async t => {
  let fail = true; const h = uiCaseHarness({ api: { postUiCaseCopy: async () => ({ code: fail ? 403 : 200 }) } }); t.after(h.cleanup); await h.mount(); await flush()
  assert.equal(await h.actions.copy(0), false); assert.equal(h.actions.pending.value, null); assert.match(h.actions.error.value, /重试/); assert.equal(h.list.rows.value.length, 1); fail = false; assert.equal(await h.actions.copy(0), true)
})
