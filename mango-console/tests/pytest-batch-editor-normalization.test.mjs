import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush as flushVue, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/pytest/case')
const response = data => ({ code: 200, data })
const record = (id = 1, patch = {}) => ({ id, name: 'Fixture ' + id, project_product: { id: 50, project_product: { id: 10, name: 'Product', project: { id: 20, name: 'Project' } } }, module: { id: 30 }, asset_status: 0, publication_status: 'unpublished', level: 1, scenario_layer: 0, scenario_type: 0, scenario_tags: ['regression'], scenario_description: '', case_people: { id: 2 }, ...patch })
const scopes = () => [{ key: 'a', label: 'Project A', caseIds: [1, 2] }, { key: 'b', label: 'Project B', caseIds: [3] }]
async function flush() { await flushVue(); await new Promise(resolve => setImmediate(resolve)) }
function setup(api = {}, extraProps = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/pytest/case/index' }), reads = [], writes = [], inferences = [], messages = [], confirmations = []
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }
  const oldDocument = globalThis.document, doc = Object.assign(new EventTarget(), { hidden: false }), listeners = new Set()
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (type, fn) => { listeners.add(fn); add(type, fn) }
  doc.removeEventListener = (type, fn) => { listeners.delete(fn); remove(type, fn) }
  globalThis.document = doc
  const h = harness('PytestCaseBatchEditor', 'localVisible,loading,saving,aiInferring,loadFailed,rows,originals,selectedScopeKey,scopeOptions,changedCount,assetStatusOptions,loadRows,save,inferWithAi,requestScopeChange,closeDialog:close', {
    base, props: { visible: false, scopes: scopes(), initialScopeKey: 'a', userOptions: [], currentUserId: 1, ...extraProps }, modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ pytest_asset_status: [0, 1, 2, 3, 4].map(key => ({ key, title: String(key) })) }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(key => [key, value => messages.push([key, value])])), Modal: { confirm: options => {
        const modal = { options, closed: false, close() { modal.closed = true } }; confirmations.push(modal); return modal
      } } },
      '@/api/pytest/case': {
        getPytestCase: query => { reads.push(query); return api.read ? api.read(query) : Promise.resolve(response(query.id__in.split(',').map(id => record(Number(id))))) },
        putPytestCaseBatchUpdate: payload => { writes.push(payload); return api.save ? api.save(payload) : Promise.resolve(response({ updated_count: payload.updates.length })) },
        postPytestCaseAiInfer: payload => { inferences.push(payload); return api.infer ? api.infer(payload) : Promise.resolve(response({ predictions: payload.case_ids.map(id => ({ id, name: 'AI ' + id })) })) },
      },
    },
  })
  return { ...h, user, route, reads, writes, inferences, messages, confirmations, listeners, boundary: h.load('batch-editor.ts'),
    async open() { h.props.visible = true; await flush() },
    async reopen() { h.props.visible = false; await flush(); h.props.visible = true; await flush() },
    mount() { life.mount.forEach(fn => fn()) }, pause() { life.deactivate.forEach(fn => fn()) }, resume() { life.activate.forEach(fn => fn()) },
    hide() { doc.hidden = true; doc.dispatchEvent(new Event('visibilitychange')) },
    show() { doc.hidden = false; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = oldDocument },
  }
}

test('batch mapping restricts scope, preserves zero/null, orders records and detaches tags and nested labels', () => {
  const h = setup(), input = record(1, { extra: 'ignored' })
  const rows = h.boundary.readBatchRows(response([record(2), input]), [1, 2])
  assert.deepEqual(rows.map(row => row.id), [1, 2]); assert.equal(rows[0].scenario_layer, 0)
  assert.equal(rows[0].projectProductId, 10); assert.equal(rows[0].projectProductLabel, 'Project/Product')
  assert.equal('extra' in rows[0], false)
  input.scenario_tags.push('changed'); assert.deepEqual(rows[0].scenario_tags, ['regression'])
  assert.equal(h.boundary.readBatchRows(response([record(1, { module: null, case_people: null })]), [1])[0].module, null)
  for (const bad of [response([record(3)]), response([record(1), record(1)]), response(null), { code: 403, data: [] }, response([record(1, { publication_status: 'unknown' })]), response([record(1, { level: false })]), response([record(1, { scenario_tags: {} })])]) assert.throws(() => h.boundary.readBatchRows(bad, [1, 2]))
  h.close()
})

test('scope and save/prediction boundaries reject bad IDs, oversized ranges, duplicate predictions and mismatched counts', () => {
  const h = setup()
  for (const scope of [null, { caseIds: [] }, { caseIds: [1, 1] }, { caseIds: [0] }, { caseIds: [true] }, { caseIds: Array.from({ length: 501 }, (_, i) => i + 1) }, { caseIds: [1], disabled: true }]) assert.throws(() => h.boundary.batchScopeIds(scope))
  assert.equal(h.boundary.readBatchSaveCount(response({ updated_count: 1 }), 1), 1)
  for (const data of [{ updated_count: 0 }, { updated_count: false }, {}, { updated_count: 2 }]) assert.throws(() => h.boundary.readBatchSaveCount(response(data), 1))
  for (const predictions of [null, [{ id: 3 }], [{ id: 1 }, { id: 1 }], [{ id: 1, module: false }], [{ id: 1, name: [] }]]) assert.throws(() => h.boundary.readBatchPredictions(response({ predictions }), [1, 2]))
  const prediction = h.boundary.readBatchPredictions(response({ predictions: [{ id: 1, scenario_layer: 0, case_people: 99, publication_status: 'published', extra: true }] }), [1]).get(1)
  assert.deepEqual(prediction, { scenario_layer: 0 })
  h.close()
})

test('opening loads selected range once, coalesces reads and only emits visibility rather than mutating parent props', async () => {
  const pending = deferred(), h = setup({ read: () => pending.promise })
  h.mount(); await h.open()
  const first = h.loadRows(), second = h.loadRows()
  assert.equal(h.reads.length, 1); assert.equal(h.loading.value, true)
  pending.resolve(response([record(2), record(1)])); await Promise.all([first, second])
  assert.deepEqual(h.rows.value.map(row => row.id), [1, 2]); assert.equal(h.changedCount.value, 0)
  h.closeDialog(); assert.equal(h.props.visible, true)
  assert.deepEqual(h.events.at(-1), ['update:visible', false]); assert.deepEqual(h.rows.value, [])
  h.close(); assert.equal(h.listeners.size, 0)
})

test('scope change A-B-A never reuses old load or lets old success/error/finalizers replace current rows', async () => {
  const pending = [deferred(), deferred(), deferred()]
  let index = 0
  const h = setup({ read: () => pending[index++].promise })
  await h.open()
  h.props.initialScopeKey = 'b'; await flush()
  h.props.initialScopeKey = 'a'; await flush()
  pending[0].resolve(response([record(1, { name: 'Old A' })])); pending[1].reject(Error('Old B')); await flush()
  assert.deepEqual(h.rows.value, []); assert.equal(h.loading.value, true)
  pending[2].resolve(response([record(1, { name: 'Current A' })])); await flush()
  assert.equal(h.rows.value[0].name, 'Current A'); assert.equal(h.loading.value, false)
  h.close()
})

test('bad and rejected reads show a retryable error rather than successful empty data', async () => {
  let value = { code: 403, data: [] }, fail = false
  const h = setup({ read: () => { if (fail) throw Error('Synchronous failure'); return Promise.resolve(value) } })
  await h.open(); assert.equal(h.loadFailed.value, true); assert.equal(h.loading.value, false)
  fail = true; assert.equal(await h.loadRows(), false); assert.equal(h.loading.value, false)
  fail = false; value = response([]); assert.equal(await h.loadRows(), true)
  assert.equal(h.loadFailed.value, false); assert.deepEqual(h.rows.value, [])
  h.close()
})

test('save submits only changed fields with a detached snapshot and has a physical duplicate/AI/scope lock', async () => {
  const pending = deferred(), h = setup({ save: () => pending.promise })
  await h.open(); h.rows.value[0].name = 'Changed'
  const saving = h.save(); assert.equal(h.saving.value, true)
  assert.equal(await h.save(), false); assert.equal(await h.inferWithAi(), false)
  h.requestScopeChange('b'); assert.equal(h.selectedScopeKey.value, 'a')
  assert.deepEqual(h.writes[0], { updates: [{ id: 1, changes: { name: 'Changed' } }] })
  h.rows.value[0].name = 'Changed after snapshot'
  assert.equal(h.writes[0].updates[0].changes.name, 'Changed')
  pending.resolve(response({ updated_count: 1 })); assert.equal(await saving, true)
  assert.equal(h.localVisible.value, false); assert.equal(h.saving.value, false)
  assert.deepEqual(h.events.at(-1), ['saved', 1])
  h.close()
})

test('save validation and business failure retain drafts; a zero/missing count cannot be reported as a fake successful save', async () => {
  let value = response({ updated_count: 0 })
  const h = setup({ save: () => Promise.resolve(value) })
  await h.open(); h.rows.value[0].name = ''
  assert.equal(await h.save(), false); assert.equal(h.writes.length, 0)
  h.rows.value[0].name = 'Changed'
  assert.equal(await h.save(), false); assert.equal(h.localVisible.value, true); assert.equal(h.saving.value, false)
  value = { code: 403 }; assert.equal(await h.save(), false)
  value = response({ updated_count: 1 }); assert.equal(await h.save(), true)
  h.close()
})

test('cancel/reopen during a save keeps the physical lock and defers fresh rows until the old write settles without closing the new drawer', async () => {
  const pending = deferred(), h = setup({ save: () => pending.promise })
  await h.open(); h.rows.value[0].name = 'Old request'
  const saving = h.save(); h.closeDialog(); await h.reopen()
  assert.equal(h.localVisible.value, true); assert.equal(h.saving.value, true)
  assert.deepEqual(h.rows.value, []); assert.equal(h.reads.length, 1)
  pending.resolve(response({ updated_count: 1 })); assert.equal(await saving, false); await flush()
  assert.equal(h.localVisible.value, true); assert.equal(h.saving.value, false)
  assert.equal(h.reads.length, 2); assert.equal(h.rows.value.length, 2)
  assert.equal(h.events.some(event => event[0] === 'saved'), false)
  h.close()
})

test('AI inference is a snapshot operation, ignores owner/publication extras and never overwrites intervening manual edits', async () => {
  const pending = deferred(), h = setup({ infer: () => pending.promise })
  await h.open()
  h.rows.value[1].name = ' Leading whitespace '
  const inference = h.inferWithAi(); assert.equal(h.aiInferring.value, true)
  assert.equal(await h.inferWithAi(), false); assert.equal(await h.save(), false)
  h.rows.value[0].name = 'Manual edit'; h.rows.value[0].case_people = 9
  pending.resolve(response({ predictions: [{ id: 1, name: 'AI 1', scenario_tags: ['smoke'], case_people: 99, publication_status: 'published' }, { id: 2, name: 'AI 2', scenario_layer: 0 }] }))
  assert.equal(await inference, true)
  assert.equal(h.rows.value[0].name, 'Manual edit'); assert.equal(h.rows.value[0].case_people, 9)
  assert.deepEqual(h.rows.value[0].scenario_tags, ['smoke'])
  assert.equal(h.rows.value[0].publication_status, 'unpublished')
  assert.equal(h.rows.value[1].name, 'AI 2'); assert.equal(h.rows.value[1].case_people, 1)
  assert.equal(h.aiInferring.value, false)
  h.close()
})

test('AI failure retries without mutating draft; identity change cannot apply late inference or prematurely release its lock', async () => {
  const pending = deferred()
  let value = { code: 403 }
  const h = setup({ infer: () => Promise.resolve(value) })
  await h.open(); assert.equal(await h.inferWithAi(), false)
  assert.equal(h.changedCount.value, 0); assert.equal(h.aiInferring.value, false)
  value = pending.promise
  const inference = h.inferWithAi()
  h.user.roleId = 2; h.user.roleId = 1
  assert.equal(h.localVisible.value, false); assert.equal(h.aiInferring.value, true)
  pending.resolve(response({ predictions: [{ id: 1, name: 'Old prediction' }] })); assert.equal(await inference, false)
  assert.deepEqual(h.rows.value, []); assert.equal(h.aiInferring.value, false)
  assert.equal(h.messages.some(message => message[0] === 'success'), false)
  h.close()
})

test('cancel/reopen during inference defers the new read and never applies old suggestions or owner changes', async () => {
  const pending = deferred(), h = setup({ infer: () => pending.promise })
  await h.open()
  const inference = h.inferWithAi()
  h.closeDialog(); await h.reopen()
  assert.equal(h.aiInferring.value, true); assert.deepEqual(h.rows.value, [])
  assert.equal(h.reads.length, 1)
  pending.resolve(response({ predictions: [{ id: 1, name: 'Old AI' }, { id: 2, name: 'Old AI 2' }] }))
  assert.equal(await inference, false); await flush()
  assert.equal(h.rows.value[0].name, 'Fixture 1'); assert.equal(h.rows.value[0].case_people, 2)
  assert.equal(h.localVisible.value, true); assert.equal(h.reads.length, 2)
  h.close()
})

test('dirty scope switching uses a guarded confirmation; old confirmations cannot change a reopened window', async () => {
  const h = setup()
  await h.open(); h.rows.value[0].name = 'Dirty'
  h.requestScopeChange('b')
  const old = h.confirmations.at(-1)
  assert.equal(h.selectedScopeKey.value, 'a')
  h.closeDialog(); assert.equal(old.closed, true)
  await h.reopen()
  assert.equal(old.options.onBeforeOk(), false)
  h.rows.value[0].name = 'Dirty again'; h.requestScopeChange('b')
  assert.equal(h.confirmations.at(-1).options.onBeforeOk(), true); await flush()
  assert.equal(h.selectedScopeKey.value, 'b'); assert.equal(h.rows.value[0].id, 3)
  h.close()
})

test('mutating the parent range invalidates in-flight reads; disabled and over-limit scopes cannot send requests', async () => {
  const pending = deferred()
  let count = 0
  const h = setup({ read: query => ++count === 1 ? pending.promise : Promise.resolve(response(query.id__in.split(',').map(id => record(Number(id))))) })
  await h.open(); h.props.scopes[0].caseIds = [3]; await flush()
  pending.resolve(response([record(1), record(2)])); await flush()
  assert.deepEqual(h.rows.value.map(row => row.id), [3])
  h.props.scopes = [{ key: 'a', label: 'Too many', caseIds: Array.from({ length: 501 }, (_, i) => i + 1) }]; await flush()
  assert.equal(h.loadFailed.value, true); assert.equal(h.reads.length, 2)
  h.close()
})

test('user, role, token, environment, route, background and KeepAlive close the drawer and remove listeners on unmount', async () => {
  const h = setup(); h.mount()
  for (const [field, value] of [['userId', 2], ['roleId', 2], ['token', 'fixture-b'], ['selected_environment', 1]]) {
    await h.reopen(); h.user[field] = value
    assert.equal(h.localVisible.value, false); assert.deepEqual(h.rows.value, [])
  }
  await h.reopen(); h.route.fullPath = '/other'; assert.equal(h.localVisible.value, false)
  await h.reopen(); h.hide(); assert.equal(h.localVisible.value, false)
  h.show(); await h.reopen(); h.pause(); assert.equal(h.localVisible.value, false)
  h.resume(); await h.reopen(); assert.equal(h.rows.value.length, 2)
  h.close(); assert.equal(h.listeners.size, 0)
})

test('unmount during save suppresses late callbacks and preserves the original physical lock until settlement', async () => {
  const pending = deferred(), h = setup({ save: () => pending.promise })
  await h.open(); h.rows.value[0].name = 'Dirty'
  const saving = h.save(); h.close()
  assert.equal(h.saving.value, true)
  pending.resolve(response({ updated_count: 1 })); assert.equal(await saving, false)
  assert.equal(h.saving.value, false); assert.equal(h.events.some(event => event[0] === 'saved'), false)
})

test('asset status choices preserve publication business constraints and the actual SFC compiles', () => {
  const h = setup()
  assert.deepEqual(h.assetStatusOptions({ publication_status: 'prepublished', asset_status: 0 }).map(option => option.key), [0])
  assert.deepEqual(h.assetStatusOptions({ publication_status: 'published', asset_status: 1 }).map(option => option.key), [1])
  assert.deepEqual(h.assetStatusOptions({ publication_status: 'unpublished', asset_status: 0 }).map(option => option.key), [0, 2, 3, 4])
  h.close()
  const filename = path.join(base, 'components/PytestCaseBatchEditor.vue'), { descriptor } = parse(readFileSync(filename, 'utf8'), { filename })
  const script = compileScript(descriptor, { id: filename })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
})
