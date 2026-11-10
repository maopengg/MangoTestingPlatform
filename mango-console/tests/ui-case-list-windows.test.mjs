import assert from 'node:assert/strict'
import test from 'node:test'
import { uiCaseHarness, caseRecords, caseRow } from './helpers/ui-case-list-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const editor = api => uiCaseHarness({ component: 'UiCaseMetadataEditor', bindings: 'draft,visible,editingId,saving,error,open,close,save', api })
const suiteEditor = api => uiCaseHarness({ component: 'UiCaseSuiteEditor', bindings: 'draft,visible,saving,error,open,close,save', api })
const taskEditor = api => uiCaseHarness({ component: 'UiCaseTaskBindingModal', bindings: 'draft,visible,saving,error,optionsError,optionsLoading,taskOptions,open,close,loadTasks,productChanged,save', api })
test('metadata editor drafts are private, zero IDs use PUT and metadata saves never overwrite case configuration', async t => {
  const h = editor(); t.after(h.cleanup); const row = caseRecords.readUiCaseRow(caseRow()); h.open(row); h.draft.scenario_tags.push('new'); assert.deepEqual(row.scenario_tags, ['regression']); assert.equal(await h.save(), true)
  const [name, value] = h.writes[0]; assert.equal(name, 'putUiCase'); assert.equal(value.id, 0); assert.equal(value.project_product, 0); assert.equal(value.module, 0); assert.equal('front_custom' in value, false); assert.equal(h.visible.value, false)
  h.open(null, { projectProduct: 0, module: 0 }); assert.equal(h.editingId.value, null); assert.equal(h.draft.name, ''); assert.equal(h.draft.project_product, 0)
})
test('new metadata uses fixed defaults and empty configuration arrays, failure retains the current draft', async t => {
  let fail = true; const h = editor({ postUiCase: async () => ({ code: fail ? 403 : 200 }) }); t.after(h.cleanup); h.open(); Object.assign(h.draft, { project_product: ['project:1', 0], module: 0, name: 'Example', level: 0, case_people: 0 })
  assert.equal(await h.save(), false); assert.equal(h.visible.value, true); assert.match(h.error.value, /草稿已保留/); assert.deepEqual(h.writes[0][1].front_custom, []); assert.deepEqual(h.writes[0][1].posterior_sql, []); fail = false; assert.equal(await h.save(), true)
})
test('metadata validation rejects incomplete fields and cancelled changes are reset on reopen', async t => {
  const h = editor(); t.after(h.cleanup); h.open(); assert.equal(await h.save(), false); assert.equal(h.writes.length, 0); h.draft.name = 'Discard'; h.close(); h.open(); assert.equal(h.draft.name, '')
})
test('metadata write snapshot is deep and physically pending until settled across close/identity changes', async t => {
  const pending = deferred(), h = editor({ putUiCase: () => pending.promise }); t.after(h.cleanup); h.open(caseRecords.readUiCaseRow(caseRow())); const saving = h.save(); h.draft.scenario_tags.push('later'); h.user.roleId++; assert.equal(h.visible.value, false); assert.equal(h.saving.value, true); h.open(); assert.equal(h.visible.value, false); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.deepEqual(h.writes[0][1].scenario_tags, ['regression']); assert.equal(h.events.some(event => event[0] === 'saved'), false)
})
test('suite editor clones dynamic values and keeps the drawer open on failed persistence', async t => {
  let fail = true; const h = suiteEditor({ putUiCase: async () => ({ code: fail ? 403 : 200 }) }); t.after(h.cleanup); const row = caseRecords.readUiCaseRow(caseRow({ parametrize: [{ name: 'Example', parametrize: [{ key: 'example', value: { nested: 0 }, test_envs: [0] }] }] }))
  h.open(row); h.draft.value[0].parametrize[0].value.nested = 2; assert.equal(row.parametrize[0].parametrize[0].value.nested, 0); assert.equal(await h.save(h.draft.value), false); assert.equal(h.visible.value, true); assert.match(h.error.value, /草稿已保留/); fail = false; assert.equal(await h.save(h.draft.value), true); assert.equal(h.writes[1][1].id, 0)
})
test('empty suites persist as an empty list and old completion cannot close a replacement context', async t => {
  const pending = deferred(), h = suiteEditor({ putUiCase: () => pending.promise }); t.after(h.cleanup); await h.mount(); h.open(caseRecords.readUiCaseRow(caseRow())); const saving = h.save(h.draft.value); await flush(); assert.deepEqual(h.writes[0][1].parametrize, []); h.visibility('hidden'); h.visibility('visible'); assert.equal(h.saving.value, true); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.equal(h.events.length, 0)
})
test('task binding owns original selected IDs, passes UI case type and supports zero product/module/task IDs', async t => {
  const h = taskEditor(); t.after(h.cleanup); const ids = [0]; h.open(ids); ids.push(2); h.draft.product = 0; h.draft.module = 0; await h.loadTasks(); h.draft.task = 0; assert.equal(await h.save(), true)
  assert.deepEqual(h.reads[0], ['getSystemTasksName', 0, 0, 0]); assert.deepEqual(h.writes[0], ['postSystemTasksBatchSetCases', [0], 0, 0]); assert.equal(h.visible.value, false)
})
test('task cascade rejects old responses and old finally cannot clear a newer loading request', async t => {
  const old = deferred(), next = deferred(); let count = 0; const h = taskEditor({ getSystemTasksName: () => ++count === 1 ? old.promise : next.promise }); t.after(h.cleanup); h.open([0]); h.draft.product = 0; const first = h.loadTasks(); h.draft.product = 1; const second = h.loadTasks(); old.resolve({ code: 200, data: [{ key: 0, title: 'Old' }] }); assert.equal(await first, false); assert.equal(h.optionsLoading.value, true); next.resolve({ code: 200, data: [{ key: 2, title: 'New' }] }); assert.equal(await second, true); assert.equal(h.taskOptions.value[0].title, 'New')
})
test('task option failures are retryable and a closed/reopened modal ignores old responses', async t => {
  let fail = true; const pending = deferred(), h = taskEditor({ getSystemTasksName: async () => { if (fail) throw Error('network'); return pending.promise } }); t.after(h.cleanup); h.open([0]); h.draft.product = 0; assert.equal(await h.loadTasks(), false); assert.match(h.optionsError.value, /重试/); fail = false; const read = h.loadTasks(); h.close(); h.open([2]); pending.resolve({ code: 200, data: [{ key: 0, title: 'Old' }] }); assert.equal(await read, false); assert.equal(h.taskOptions.value.length, 0)
})
test('binding rejects stale task choices, retains draft on backend rejection and prevents duplicate writes', async t => {
  const pending = deferred(), h = taskEditor({ postSystemTasksBatchSetCases: () => pending.promise }); t.after(h.cleanup); h.open([0]); h.draft.product = 0; assert.equal(await h.save(), false); await h.loadTasks(); h.draft.task = 0; const saving = h.save(); assert.equal(await h.save(), false); pending.resolve({ code: 403 }); assert.equal(await saving, false); assert.equal(h.visible.value, true); assert.equal(h.draft.task, 0); assert.match(h.error.value, /重试/)
})
