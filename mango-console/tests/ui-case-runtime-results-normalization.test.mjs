import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const assets = loadModule('src/components/business/ui-case-step-create.ts')
const dto = loadModule('src/views/uitest/case/details/runtime-results.ts', { '@/components/business/ui-case-step-create': assets })
const report = loadModule('src/components/reports/ui-report.ts')
const long = '90071992547409930000'
const node = (id = 0, changes = {}) => ({ id, status: 1, next_node_id: long, picture_path: 'example.png', ass_msg: 'kept', locator_engine: { used_source: 'configured' }, ...changes })
const step = (changes = {}) => ({ id: 0, case_step_details_id: 0, execution_id: 'example-run', test_env: 0, progress_sequence: 1, status: 3, is_final: false, cache_data: { nested: { value: 'keep' } }, data_factory_cache_data: { factory: [1] }, element_result_list: [node()], ...changes })
const result = (changes = {}) => ({ id: 0, execution_id: 'example-run', test_env: 0, status: 1, video_path: 'example.webm', steps: [step({ is_final: true, status: 1 })], ...changes })
const response = (value = result(), changes = {}) => ({ code: 200, data: { source_type: 'page', target_type: 'ui_case', target_id: 0, test_env: 0, result_data: value, ...changes } })
function setup(read = async () => response(null)) {
  const previousDocument = globalThis.document, previousWindow = globalThis.window
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }), timers = new Map(); let timerId = 0
  const win = Object.assign(new EventTarget(), { setTimeout: (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id }, clearTimeout: id => timers.delete(id) })
  globalThis.document = doc; globalThis.window = win
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], updates = [], refreshes = [], finished = []
  const state = vue.reactive({ caseId: 0, executionId: '', stepIds: [0] }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const config = { UI_CASE_RESULT_SOCKET_EVENTS: ['u_page_steps', 'u_page_step_node_progress', 'u_test_case', 'u_test_suite_details'] }
  const module = loadModule('src/views/uitest/case/details/composables/useCaseRuntimeResults.ts', {
    vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
    '@/components/business/ui-case-step-create': assets, '../runtime-results': dto, '../config': config,
    '@/api/system/execution_result': { getExecutionResultLatestResolved: query => { reads.push(query); return read(query) } },
  })
  const scope = vue.effectScope(), h = scope.run(() => module.useCaseRuntimeResults({ caseId: () => state.caseId, executionId: () => state.executionId, stepIds: () => state.stepIds, updated: (...args) => updates.push(args), refresh: () => refreshes.push(true), finished: value => finished.push(value) }))
  return { ...h, state, route, user, permission, callbacks, reads, updates, refreshes, finished, timers,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    send(name, args) { const event = new Event('mango:websocket-message'); event.detail = { data: { func_name: name, func_args: args } }; win.dispatchEvent(event) },
    tick() { const values = [...timers.values()]; timers.clear(); values.forEach(item => item.fn()) },
    close() { callbacks.unmount.forEach(fn => fn()); scope.stop(); globalThis.document = previousDocument; globalThis.window = previousWindow },
  }
}
test('finite projection and view adapter retain zero/long IDs, cache, screenshot, assertion and locator evidence', () => {
  const value = dto.readCaseRuntimeStep(step()), wire = dto.caseRuntimeStepEvidence(value)
  assert.equal(value.detailId, 0); assert.equal(value.nodes[0].nextId, long); assert.deepEqual(wire.cache_data, { nested: { value: 'keep' } }); assert.equal(wire.element_result_list[1].id, long); assert.equal(wire.element_result_list[1].runtime_pending, true)
  const view = report.normalizeUiRuntime(wire.element_result_list[0]); assert.equal(view.picture_path, 'example.png'); assert.equal(view.ass_msg, 'kept'); assert.equal(view.locator_engine.used_source, 'configured')
  assert.equal(dto.readCaseRuntimeResult(result()).evidence.video_path, 'example.webm'); assert.equal(Object.isFrozen(value.evidence), true)
})
test('pending node marker is presentation only, not duplicated, and is absent for failed/final/empty steps', () => {
  for (const changes of [{ is_final: true }, { element_result_list: [] }, { element_result_list: [node(0, { status: 0 })] }, { element_result_list: [node(0, { next_node_id: 0 })] }]) {
    const value = dto.readCaseRuntimeStep(step(changes)); assert.equal(dto.caseRuntimeStepEvidence(value).element_result_list.length, value.nodes.length)
  }
  const value = dto.readCaseRuntimeStep(step({ element_result_list: [node(0, { next_node_id: 2 }), { id: 2, status: 3, runtime_pending: true }] })); assert.equal(value.nodes.length, 1); assert.equal(dto.caseRuntimeStepEvidence(value).element_result_list.length, 2)
})
test('latest response validates code, source, target, owner, environment and result fields', () => {
  for (const value of [{ code: 403 }, response(result(), { source_type: 'suite' }), response(result(), { target_type: 'api_case' }), response(result(), { target_id: 2 }), response(result(), { test_env: 2 }), response(result({ id: 2 })), response(result({ test_env: 2 })), response(result({ status: false }))]) assert.throws(() => dto.readLatestCaseRuntime(value, 0, 0))
  assert.equal(dto.readLatestCaseRuntime({ code: 200, data: null }, 0, 0), null); assert.equal(dto.readLatestCaseRuntime(response(null), 0, 0), null)
})
test('step merge rejects out-of-order sequence, short partial snapshots and increments after final', () => {
  const first = dto.mergeCaseRuntimeStep(null, dto.readCaseRuntimeStep(step({ progress_sequence: 3 })), 0)
  assert.equal(dto.mergeCaseRuntimeStep(first, dto.readCaseRuntimeStep(step({ progress_sequence: 2 })), 0), first)
  assert.equal(dto.mergeCaseRuntimeStep(first, dto.readCaseRuntimeStep(step({ progress_sequence: 4, element_result_list: [] })), 0), first)
  const final = dto.mergeCaseRuntimeStep(first, dto.readCaseRuntimeStep(step({ progress_sequence: 4, is_final: true, status: 0 })), 0)
  assert.equal(final.status, 0); assert.equal(dto.mergeCaseRuntimeStep(final, dto.readCaseRuntimeStep(step({ progress_sequence: 5 })), 0), final)
  const complete = dto.readCaseRuntimeResult(result()); assert.equal(dto.mergeCaseRuntimeStep(complete, dto.readCaseRuntimeStep(step()), 0), complete)
})
test('node progress updates same ID immutably, rejects lower completed count and respects final snapshot', () => {
  const first = dto.mergeCaseRuntimeStep(null, dto.readCaseRuntimeStep(step()), 0)
  const progress = dto.readCaseNodeProgress({ id: 0, case_step_details_id: 0, execution_id: 'example-run', completed_count: 2, element_result: node(long, { next_node_id: null }) })
  const second = dto.mergeCaseNodeProgress(first, progress, 0, 0); assert.equal(second.steps[0].nodes.length, 2); assert.equal(first.steps[0].nodes.length, 1)
  assert.equal(dto.mergeCaseNodeProgress(second, { ...progress, count: 1 }, 0, 0), second)
  assert.equal(dto.mergeCaseNodeProgress(dto.readCaseRuntimeResult(result()), progress, 0, 0).final, true)
  assert.equal(dto.mergeCaseNodeProgress(second, { ...progress, executionId: 'other' }, 0, 0), second)
})
test('row projection updates ID zero and clears only missing final rows; caches fall back to last populated step', () => {
  const rows = [{ id: 0, status: 2, error_message: 'old', error_retry: 8 }, { id: 2, status: 0, error_message: 'old' }], value = dto.readCaseRuntimeResult(result())
  const next = dto.applyCaseRuntimeRows(rows, value, true); assert.equal(next[0].status, 1); assert.equal(next[0].error_retry, 8); assert.equal(next[1].status, 2); assert.equal(next[1].error_message, null); assert.equal(rows[1].status, 0)
  assert.equal(dto.applyCaseRuntimeRows(rows, value, false)[1], rows[1]); assert.deepEqual(dto.caseRuntimeCache(value), { nested: { value: 'keep' } }); assert.deepEqual(dto.caseRuntimeCache(value, true), { factory: [1] })
})
test('latest reads deduplicate and provide exact query with local loading and failure retry', async t => {
  let fail = true; const h = setup(async () => fail ? { code: 403 } : response()); t.after(h.close)
  const first = h.load(), duplicate = h.load(); assert.equal(first, duplicate); assert.equal(h.loading.value, true); assert.equal(await first, false); assert.equal(h.loading.value, false); assert.match(h.error.value, /失败/)
  fail = false; assert.equal(await h.load(), true); assert.equal(h.result.value.id, 0); assert.equal(h.error.value, ''); assert.deepEqual(h.reads[0], { source_type: 'page', target_type: 'ui_case', target_id: 0, test_env: 0, page: 1, pageSize: 1 })
})
test('failed or not-yet-persisted current execution remains pending for silent retry', async t => {
  let data = response(null); const h = setup(async () => data); t.after(h.close); h.state.executionId = 'example-run'
  assert.equal(await h.load(true, false), false); assert.equal(h.pending.value, true); assert.equal(h.loading.value, false)
  data = response(result({ execution_id: 'other' })); assert.equal(await h.load(), false); assert.equal(h.pending.value, true)
  data = response(); assert.equal(await h.load(), true); assert.equal(h.pending.value, false)
})
test('socket updates invalidate earlier HTTP and old finally cannot dismiss a new read', async t => {
  const first = deferred(), second = deferred(); let reads = 0; const h = setup(() => ++reads === 1 ? first.promise : second.promise); t.after(h.close)
  const old = h.load(); await flush(); assert.equal(h.acceptStep(step()), true); const latest = h.load(); await flush(); first.resolve(response()); assert.equal(await old, false); assert.equal(h.loading.value, true); assert.equal(h.result.value.final, false)
  second.resolve(response()); assert.equal(await latest, true); assert.equal(h.loading.value, false)
})
test('history from a previous run cannot replace an already observed in-progress external execution', async t => {
  const h = setup(async () => response(result({ execution_id: 'old-history' }))); t.after(h.close)
  assert.equal(h.acceptStep(step()), true); assert.equal(await h.load(), false); assert.equal(h.result.value.executionId, 'example-run'); assert.equal(h.result.value.final, false)
})
test('socket processing validates membership/environment/execution and cannot regress after case final', async t => {
  const h = setup(); t.after(h.close); h.state.executionId = 'example-run'; h.mount(); await flush()
  h.send('u_page_steps', step({ case_step_details_id: 2 })); h.send('u_page_steps', step({ test_env: 2 })); h.send('u_page_steps', step({ execution_id: 'other' })); assert.equal(h.updates.length, 0)
  h.send('u_page_steps', step()); assert.equal(h.updates.length, 1); assert.equal(h.timers.size, 1); assert.equal([...h.timers.values()][0].delay, 500)
  h.send('u_page_step_node_progress', { id: 0, case_step_details_id: 0, execution_id: 'example-run', completed_count: 2, element_result: node(long) }); assert.equal(h.result.value.steps[0].nodes.length, 2)
  h.send('u_test_case', result()); assert.equal(h.result.value.final, true); assert.deepEqual(h.finished, ['example-run']); const count = h.updates.length
  h.send('u_page_steps', step({ progress_sequence: 99 })); h.send('u_page_step_node_progress', { id: 0, case_step_details_id: 0, execution_id: 'example-run', element_result: node() }); assert.equal(h.updates.length, count)
  h.tick(); assert.deepEqual(h.refreshes, [true])
})
test('unscoped lightweight nodes cannot select an arbitrary execution, but known run can bootstrap nodes', async t => {
  const h = setup(); t.after(h.close); const progress = { id: 0, case_step_details_id: 0, execution_id: 'example-run', element_result: node() }
  assert.equal(h.acceptNode(progress), false); h.state.executionId = 'example-run'; assert.equal(h.acceptNode(progress), true); assert.equal(h.result.value.steps[0].detailId, 0)
})
const changes = [h => h.state.caseId = 2, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1', h => { h.state.caseId = 2; h.state.caseId = 0 }]
test('identity changes including A-B-A clear previous results and invalidate GET/debounced refresh', async () => {
  for (const change of changes) {
    const pending = deferred(); let reads = 0
    const h = setup(query => ++reads === 1 ? pending.promise : Promise.resolve(response(result({ id: query.target_id, test_env: query.test_env, execution_id: 'new-context' }), { target_id: query.target_id, test_env: query.test_env })))
    try { h.mount(); h.send('u_page_steps', step()); assert.equal(h.timers.size, 1); const old = h.load(); await flush(); change(h); assert.equal(h.result.value, null); pending.resolve(response()); assert.equal(await old, false); await flush(); h.tick(); assert.deepEqual(h.refreshes, []); assert.equal(h.error.value, ''); assert.notEqual(h.result.value?.executionId, 'example-run') } finally { h.close() }
  }
})
test('background/KeepAlive reject messages and late reads, cancel debounce and resume silently', async () => {
  for (const leave of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn())]) {
    const pending = deferred(); let reads = 0; const h = setup(() => ++reads === 1 ? pending.promise : Promise.resolve(response()))
    try { h.mount(); const old = h.load(); await flush(); h.send('u_page_steps', step()); leave(h); const count = h.updates.length; h.send('u_test_case', result()); assert.equal(h.updates.length, count); assert.equal(h.timers.size, 0); pending.resolve(response()); assert.equal(await old, false); h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(h.result.value.final, true); assert.equal(h.loading.value, false) } finally { h.close() }
  }
})
test('unmount removes subscriptions, clears evidence and rejects outstanding work', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close); h.mount(); const old = h.load(); await flush(); h.callbacks.unmount.forEach(fn => fn()); pending.resolve(response()); assert.equal(await old, false); h.send('u_test_case', result()); assert.equal(h.result.value, null); assert.deepEqual(h.finished, []); assert.equal(h.timers.size, 0)
})
test('execution ID change invalidates history reads and old run messages, retaining new pending state', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close); const old = h.load(false); await flush(); h.state.executionId = 'new-run'; pending.resolve(response()); assert.equal(await old, false); assert.equal(h.result.value, null); assert.equal(h.pending.value, true); assert.equal(h.acceptFinal(result()), false)
})
test('malformed messages and unrelated protocol functions do not mutate or schedule refresh', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  h.send('unrelated', result()); h.send('u_page_steps', { status: 'bad' }); h.send('u_page_step_node_progress', { id: 0, element_result: [] }); h.send('u_test_case', result({ id: 2 })); assert.deepEqual(h.updates, []); assert.equal(h.timers.size, 0)
})
test('submission acknowledgement preserves matching progress that arrived before its HTTP response', async t => {
  const h = setup(); t.after(h.close); assert.equal(h.acceptStep(step()), true); const progress = h.result.value; h.state.executionId = 'example-run'; assert.equal(h.result.value, progress); h.reset('example-run'); assert.equal(h.result.value, progress); assert.equal(h.pending.value, true); h.state.executionId = 'different-run'; assert.equal(h.result.value, null)
})
