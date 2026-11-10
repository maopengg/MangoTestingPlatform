import assert from 'node:assert/strict'
import test from 'node:test'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { elementsHarness, records, elementRow, listResponse, pageRow } from './helpers/ui-elements-harness.mjs'

test('element DTO preserves zero/long IDs, independent event drafts and finite writable fields', () => {
  const raw = elementRow({ id: '900719925474099399', expected_event: { ope_key: 'example', ope_value: [{ f: 'x', v: { flag: false, count: 0 } }] }, unknown: 'evidence' })
  const row = records.readElementRow(raw); row.expected_event.ope_value[0].v.count = 2
  assert.equal(row.id, '900719925474099399'); assert.equal(row.exp, 0); assert.equal(raw.expected_event.ope_value[0].v.count, 0); assert.equal(row.unknown, undefined)
  assert.equal(records.expectedEventParamSummary({ ope_key: 'x', ope_value: [{ f: 'x', v: false }, { f: 'y', v: 0 }] }), 'x=false；y=0')
})
test('explicit route and embedded IDs preserve zero and do not fall back to a stale cached asset', t => {
  const h = elementsHarness({ props: { pageId: 0 }, query: { id: 9 }, cached: pageRow({ id: 8 }) }); t.after(h.cleanup); assert.equal(h.currentPageId.value, 0)
  h.props.pageId = ''; assert.equal(h.currentPageId.value, 9); h.route.query.id = {}; assert.equal(h.currentPageId.value, null)
})
test('page, categories and list load independently; category query uses pageSize and preserves zero', async t => {
  const page = deferred(), cats = deferred(), h = elementsHarness({ api: { getUiPage: () => page.promise, getUiElementCategory: () => cats.promise } }); t.after(h.cleanup)
  const loading = h.initialize(); await flush(); assert.equal(h.pageLoading.value, true); assert.equal(h.categoryLoading.value, true); assert.equal(h.listLoading.value, false); assert.equal(h.elementRows.value.length, 1)
  assert.deepEqual(h.reads.find(([name]) => name === 'getUiElement')[1], { page: 1, pageSize: 20, page_id: 0 }); page.resolve({ code: 200, data: [pageRow()] }); cats.resolve({ code: 200, data: [] }); await loading; await flush()
})
test('list failure stops local loading and can be retried without hiding loaded categories', async t => {
  let fail = true; const h = elementsHarness({ api: { getUiElement: async () => { if (fail) throw Error('Example unavailable'); return listResponse() } } }); t.after(h.cleanup)
  await h.loadCategories(); assert.equal(await h.doRefresh(), false); assert.equal(h.listLoading.value, false); assert.equal(h.listError.value, 'Example unavailable'); assert.equal(h.resources.categories.value.length, 2)
  fail = false; assert.equal(await h.doRefresh(), true); assert.equal(h.listError.value, ''); assert.equal(h.elementRows.value[0].id, 0)
})
test('out-of-order list requests do not overwrite current category results', async t => {
  const old = deferred(); let count = 0; const h = elementsHarness({ api: { getUiElement: () => ++count === 1 ? old.promise : Promise.resolve(listResponse([elementRow({ name: 'Current' })])) } }); t.after(h.cleanup)
  const first = h.doRefresh(); h.onCategorySelect(['Example']); await flush(); old.resolve(listResponse([elementRow({ name: 'Old' })])); await first
  assert.equal(h.elementRows.value[0].name, 'Current'); assert.equal(h.reads.filter(([name]) => name === 'getUiElement')[1][1].category, 'Example')
})
test('last-page deletion recovers to a valid page without leaving loading active', async t => {
  const h = elementsHarness({ api: { getUiElement: async query => query.page > 1 ? listResponse([], 1) : listResponse() } }); t.after(h.cleanup)
  h.pagination.page = 3; await h.doRefresh(); assert.equal(h.pagination.page, 1); assert.equal(h.listLoading.value, false); assert.equal(h.elementRows.value.length, 1)
})
test('identity, environment, resource A-B-A and route changes reject stale reads', async () => {
  for (const change of [h => h.user.roleId++, h => h.user.token = 'example-next', h => h.user.selected_environment++, h => { h.props.pageId = 2; h.props.pageId = 0 }, h => h.route.fullPath += '&x=1']) {
    const pending = deferred(), h = elementsHarness({ props: { pageId: 0 }, api: { getUiElement: () => pending.promise } })
    try { const load = h.doRefresh(); change(h); pending.resolve(listResponse()); await load; assert.equal(h.elementRows.value.length, 0); assert.equal(h.listLoading.value, false) } finally { h.cleanup() }
  }
})
test('background/KeepAlive pause owned workbench and resume current resources on return', async t => {
  const h = elementsHarness(); t.after(h.cleanup); h.mount(); await flush(); h.liveWorkbenchVisible.value = true; h.batchAddVisible.value = true; h.visibility('hidden')
  assert.equal(h.liveWorkbenchVisible.value, false); assert.equal(h.batchAddVisible.value, false); assert.equal(h.elementRows.value.length, 0)
  h.callbacks.deactivate.forEach(fn => fn()); const count = h.reads.length; h.visibility('visible'); await flush(); assert.equal(h.reads.length, count); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.ok(h.reads.length > count)
})
test('deletion freezes original IDs and failure retains selection for explicit retry', async t => {
  let fail = true; const h = elementsHarness({ api: { deleteUiElement: async () => { if (fail) throw Error('Example rejection'); return { code: 200 } } } }); t.after(h.cleanup)
  h.selectedRowKeys.value = [0, '900719925474099399']; h.onDelete(null); h.selectedRowKeys.value = [9]
  assert.equal(await h.confirmations[0].onBeforeOk(), false); assert.deepEqual(h.writes[0][1], [0, '900719925474099399']); assert.deepEqual(h.selectedRowKeys.value, [9]); assert.equal(h.reads.length, 0)
  fail = false; assert.equal(await h.confirmations[0].onBeforeOk(), true); assert.equal(h.writes.length, 2); assert.equal(h.deleting.value, false)
})
test('accepted deletion survives reload failure and duplicate confirm clicks cannot issue another write', async t => {
  const pending = deferred(), h = elementsHarness({ api: { deleteUiElement: () => pending.promise, getUiElement: async () => { throw Error('Example read failure') } } }); t.after(h.cleanup)
  h.elementRows.value = [records.readElementRow(elementRow())]; h.onDelete(h.elementRows.value[0]); const deleting = h.confirmations[0].onBeforeOk(); assert.equal(await h.confirmations[0].onBeforeOk(), false)
  pending.resolve({ code: 200 }); assert.equal(await deleting, true); assert.equal(h.elementRows.value.length, 0); assert.equal(h.writes.length, 1); assert.equal(h.listError.value, 'Example read failure')
})
test('closing or replacing a context does not release an outstanding delete lock', async t => {
  const pending = deferred(), h = elementsHarness({ api: { deleteUiElement: () => pending.promise } }); t.after(h.cleanup)
  h.selectedRowKeys.value = [0]; h.onDelete(null); const deleting = h.confirmations[0].onBeforeOk(); h.user.roleId++; assert.equal(h.confirmations[0].closed, true); h.onDelete(records.readElementRow(elementRow()))
  assert.equal(h.confirmations.length, 1); assert.equal(h.deleting.value, true); pending.resolve({ code: 200 }); assert.equal(await deleting, false); assert.equal(h.reads.length, 0); assert.equal(h.deleting.value, false)
})
