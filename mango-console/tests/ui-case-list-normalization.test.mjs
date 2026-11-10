import assert from 'node:assert/strict'
import test from 'node:test'
import { caseRecords as dto, caseRow, caseResponse, uiCaseHarness, lossless } from './helpers/ui-case-list-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const long = '90071992547409930000'
test('finite case list validates identities, preserves zero/long IDs and does not retain permission flags or configuration', () => {
  const row = dto.readUiCaseRow(caseRow({ id: long, is_product_owner: false, front_sql: [{ sql: 'select 1' }] }))
  assert.equal(row.id, long); assert.equal(row.project_product.id, 0); assert.equal(row.level, 0); assert.equal(row.case_people.id, 0); assert.equal('is_product_owner' in row, false); assert.equal('front_sql' in row, false)
  for (const response of [{ code: 403, data: [] }, caseResponse([caseRow(), caseRow()]), caseResponse([caseRow({ publication_status: 'other' })]), caseResponse([caseRow({ publication_status: ['published'] })]), caseResponse([], -1)]) assert.throws(() => dto.readUiCaseList(response))
})
test('metadata initialization and whitelist save preserve zero IDs and never share original tags', () => {
  const row = dto.readUiCaseRow(caseRow()), draft = dto.createMetadataDraft(row); draft.scenario_tags.push('new')
  assert.deepEqual(row.scenario_tags, ['regression']); const value = dto.caseMetadataPayload(draft, 0)
  assert.equal(value.id, 0); assert.equal(value.module, 0); assert.equal(value.project_product, 0); assert.equal(value.case_people, 0); assert.equal('front_sql' in value, false)
  const created = dto.caseMetadataPayload(draft, null); assert.deepEqual(created.front_custom, []); assert.deepEqual(created.front_auth_config, []); assert.equal('id' in created, false)
})
test('suite boundary retains dynamic JSON, false, zero, null and lossless numbers without shared references', () => {
  const value = lossless.parseLosslessJson('[{"name":"Example","parametrize":[{"key":"example","value":90071992547409930000,"test_envs":[0]}]}]')
  const suite = dto.readCaseSuites(value); assert.equal(lossless.stringifyLosslessJson(suite), lossless.stringifyLosslessJson(value)); assert.notEqual(suite[0].parametrize, value[0].parametrize)
  for (const value of [false, 0, null, { nested: true }]) assert.deepEqual(dto.readCaseSuites([{ parametrize: [{ key: 'example', value }] }])[0].parametrize[0].value, value)
})
test('page uses instance-owned search state, collection filters, real product leaf and module subtree', async t => {
  const h = uiCaseHarness(); t.after(h.cleanup); await h.mount(); await flush()
  h.conditionItems.find(item => item.key === 'level').value = [0, 1]; h.conditionItems.find(item => item.key === 'case_people').value = [0]; h.conditionItems.find(item => item.key === 'id').value = '5574、5577'
  await h.onNavigationFilterChange({ projectProduct: ['project:1', 0], module: 0, moduleIds: [0, long] })
  const query = h.reads.filter(([name]) => name === 'getUiCase').at(-1)[1]
  assert.equal(query.project_product, 0); assert.equal(query.module__in, `0,${long}`); assert.equal(query.level__in, '0,1'); assert.equal(query.case_people__in, '0'); assert.equal(query.id, '5574,5577'); assert.equal(query.pageSize, 20); assert.equal('size' in query, false)
  await h.onResetSearch(); assert.deepEqual(h.conditionItems.find(item => item.key === 'level').value, []); assert.equal(h.query().project_product, undefined)
})
test('list/users load independently, reject old search results and old finally cannot clear a replacement read', async t => {
  const first = deferred(), second = deferred(), users = deferred(); let reads = 0
  const h = uiCaseHarness({ api: { getUiCase: () => ++reads === 1 ? first.promise : second.promise, getUserName: () => users.promise } }); t.after(h.cleanup); await h.mount(); await flush()
  h.conditionItems.find(item => item.key === 'name').value = 'new'; const current = h.onSearchRefresh(); await flush(); first.resolve(caseResponse([caseRow({ name: 'old' })])); await flush(); assert.equal(h.list.loading.value, true); assert.equal(h.list.rows.value.length, 0)
  second.resolve(caseResponse([caseRow({ name: 'new' })])); await current; assert.equal(h.list.rows.value[0].name, 'new'); assert.equal(h.list.loading.value, false); assert.equal(h.list.usersLoading.value, true); users.resolve({ code: 200, data: [{ key: 0, title: 'User' }] }); await flush(); assert.equal(h.list.users.value[0].key, 0)
})
test('list and users failures expose separate retries and out-of-range pages recover after deletion', async t => {
  let fail = true; const h = uiCaseHarness({ api: { getUiCase: async query => { if (fail) throw Error('network'); return caseResponse(query.page > 1 ? [] : [caseRow()], 1) }, getUserName: async () => { if (fail) throw Error('network'); return { code: 200, data: [] } } } }); t.after(h.cleanup); await h.mount(); await flush()
  assert.match(h.list.error.value, /重试/); assert.match(h.list.usersError.value, /重试/); assert.equal(h.list.loading.value, false); fail = false; h.pagination.page = 2; await h.doRefresh(); await h.list.loadUsers(); assert.equal(h.pagination.page, 1); assert.equal(h.list.rows.value.length, 1); assert.equal(h.list.usersError.value, '')
})
test('pending/start states silently poll every five seconds, retry failures, pause and resume on visibility and KeepAlive', async t => {
  let fail = false, status = 2
  const h = uiCaseHarness({ api: { getUiCase: async () => { if (fail) throw Error('network'); return caseResponse([caseRow({ status })]) } } }); t.after(h.cleanup); await h.mount(); await flush()
  assert.equal([...h.timers.values()][0].delay, 5000); fail = true; await h.tick(); await flush(); assert.equal(h.list.loading.value, false); assert.equal(h.timers.size, 1); h.visibility('hidden'); assert.equal(h.timers.size, 0); fail = false; status = 3; h.visibility('visible'); await flush(); assert.equal(h.timers.size > 0, true)
  h.callbacks.deactivate.forEach(fn => fn()); assert.equal(h.timers.size, 0); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(h.timers.size > 0, true); status = 1; await h.tick(); await flush(); assert.equal(h.timers.size, 0)
})
test('identity and A-B-A changes discard old reads and close associated windows', async () => {
  for (const change of [h => h.user.roleId++, h => h.user.token = 'example-new', h => h.permission.permissionKeys.push('example:read'), h => { h.user.selected_environment = 2; h.user.selected_environment = 0 }]) {
    const pending = deferred(); let count = 0; const h = uiCaseHarness({ api: { getUiCase: () => ++count === 1 ? pending.promise : Promise.resolve(caseResponse([caseRow({ name: 'new' })])) } })
    try { const closed = []; h.metadataEditorRef.value = { close: () => closed.push(true) }; await h.mount(); await flush(); change(h); await flush(); pending.resolve(caseResponse([caseRow({ name: 'old' })])); await flush(); assert.equal(h.list.rows.value[0].name, 'new'); assert.equal(closed.length > 0, true) } finally { h.cleanup() }
  }
})
test('navigation preserves long IDs and publication actions are never hidden by product-owner flags', async t => {
  const h = uiCaseHarness(); t.after(h.cleanup); const row = dto.readUiCaseRow(caseRow({ id: long, publication_status: 'prepublished', is_product_owner: false })); await h.onClick(row)
  assert.equal(h.navigation[0].query.id, long); assert.equal(h.caseActions(row).find(item => item.label === '通过发布').hidden, false); assert.equal(h.caseActions(row).find(item => item.label === '退回未发布').hidden, false)
})
