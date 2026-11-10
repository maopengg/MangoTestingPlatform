import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush, method } from './helpers/case-details-harness.mjs'
import * as observations from '../src/utils/executor-task-observer.mjs'

const assets = loadModule('src/components/business/ui-case-step-create.ts')
const dto = loadModule('src/views/uitest/case/details/case-execution.ts', { '@/components/business/ui-case-step-create': assets })
const runtime = loadModule('src/views/uitest/case/details/runtime-results.ts', { '@/components/business/ui-case-step-create': assets })
const long = '90071992547409930000', scopeOwner = JSON.stringify([1, 2, 0]), scope = dto.caseExecutionScope(scopeOwner)
const submission = (changes = {}) => ({ code: 200, msg: 'submitted', data: { id: 0, test_env: 0, execution_id: 'example-run', task_id: long, ...changes } })
const task = (changes = {}) => { const value = { task_id: long, task_type: 'ui_case', business_type: 'u_case', business_id: 0, status: 'running', result: null, error_message: null, ...changes }; return { code: 200, data: { ...value, terminal: ['success', 'failed', 'interrupted', 'cancelled', 'timeout'].includes(value.status) } } }
const finalResult = (changes = {}) => ({ id: 0, execution_id: 'example-run', test_env: 0, status: 1, steps: [], ...changes })
const active = (...tasks) => ({ code: 200, data: tasks.map(value => value.data) })
const scopedObservation = () => ({ taskId: long, businessType: 'u_case', owner: scopeOwner, environment: 0, executionId: 'example-run' })
function setup(overrides = {}) {
  const previousDocument = globalThis.document, previousWindow = globalThis.window
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }), timers = new Map(), storage = new Map(); let timerId = 0
  const win = { setTimeout: (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id }, clearTimeout: id => timers.delete(id), sessionStorage: { getItem: key => { if (overrides.failRead) throw Error('storage'); return storage.get(key) ?? null }, setItem: (key, value) => { if (overrides.failStore) throw Error('storage'); storage.set(key, value) }, removeItem: key => { if (overrides.failClear) throw Error('storage'); storage.delete(key) } } }
  globalThis.document = doc; globalThis.window = win
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], writes = [], starts = [], finishes = [], notifications = [], messages = []
  const state = vue.reactive({ caseId: 0, busy: false }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const module = loadModule('src/views/uitest/case/details/composables/useCaseExecution.ts', {
    vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
    'vue-router': { useRoute: () => route }, '@arco-design/web-vue': { Message: { loading: value => messages.push(value) }, Notification: Object.fromEntries(['success', 'warning', 'error'].map(kind => [kind, value => notifications.push([kind, value])])) },
    '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@/components/business/ui-case-step-create': assets,
    '../case-execution': dto, '../runtime-results': runtime, '@/utils/executor-task-observer.mjs': observations, '@/utils/executor-task-notification': loadModule('src/utils/executor-task-notification.ts'),
    '@/api/uitest/case': { getUiCaseRun: (...args) => { writes.push(args); return overrides.run ? overrides.run(...args) : Promise.resolve(submission({ id: args[0], test_env: args[1] })) } },
    '@/api/system/executor-task': {
      getActiveExecutorTasks: (query, silent) => { reads.push(['active', query, silent]); return overrides.active ? overrides.active(query) : Promise.resolve(active()) },
      getExecutorTask: (...args) => { reads.push(['task', ...args]); return overrides.task ? overrides.task(...args) : Promise.resolve(task()) },
    },
  })
  const effect = vue.effectScope(), h = effect.run(() => module.useCaseExecution({ caseId: () => state.caseId, name: () => 'Example case', busy: () => state.busy, started: value => starts.push(value), finished: async (value, current) => { finishes.push(value); if (overrides.finish) await overrides.finish(value, current) } }))
  return { ...h, state, route, user, permission, callbacks, reads, writes, starts, finishes, notifications, messages, storage, timers,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    async tick(delay) { const entries = [...timers.entries()].filter(([, value]) => delay === undefined || value.delay === delay); entries.forEach(([id]) => timers.delete(id)); entries.forEach(([, value]) => value.fn()); await flush(); await flush() },
    store(observation = scopedObservation(), ownScope = scope) { observations.saveExecutorTaskObservation(ownScope, 0, observation) }, stored(ownScope = scope) { return observations.loadExecutorTaskObservation(ownScope, 0) },
    launch(prepare = async () => ({ withLive: false })) { return h.start(prepare) },
    close() { callbacks.unmount.forEach(fn => fn()); effect.stop(); globalThis.document = previousDocument; globalThis.window = previousWindow },
  }
}
test('submission/task/observation boundaries preserve zero case/environment and long task IDs', () => {
  assert.deepEqual(dto.readCaseExecutionSubmission(submission(), 0, 0), { taskId: long, executionId: 'example-run', message: 'submitted' })
  assert.equal(dto.readCaseExecutionTask(task(), 0, long).terminal, false)
  assert.deepEqual(dto.readCaseExecutionObservation({ ...scopedObservation(), businessId: '0' }, 0, 0, scopeOwner, false), { taskId: long, executionId: 'example-run', legacy: false })
  assert.deepEqual(dto.readCaseExecutionObservation({ taskId: long, businessId: 0, businessType: 'u_case' }, 0, 0, scopeOwner, true), { taskId: long, executionId: '', legacy: true })
  for (const value of [submission({ id: 2 }), submission({ test_env: 2 }), submission({ execution_id: '' }), submission({ task_id: 0 }), { code: 403 }]) assert.throws(() => dto.readCaseExecutionSubmission(value, 0, 0))
  for (const changes of [{ task_id: 2 }, { task_type: 'auth_start' }, { business_type: 'other' }, { business_id: 2 }, { status: 'unknown' }]) assert.throws(() => dto.readCaseExecutionTask(task(changes), 0, long))
  assert.throws(() => dto.readCaseExecutionTask({ code: 200, data: { ...task().data, terminal: true } }, 0, long))
})
test('launch recovers first, snapshots request values, persists provenance and blocks duplicate submit', async t => {
  const pending = deferred(), h = setup({ run: () => pending.promise }); t.after(h.close)
  const saving = h.launch(async () => ({ withLive: true, actuatorUsername: 'example-actuator' })); assert.equal(h.submitting.value, true); assert.equal(await h.launch(), false); await flush(); await flush()
  assert.deepEqual(h.reads[0], ['active', { business_type: 'u_case', business_id: 0 }, true]); assert.deepEqual(h.writes, [[0, 0, 'example-actuator']])
  pending.resolve(submission()); assert.equal(await saving, true); assert.equal(h.active.value, true); assert.equal(h.submitting.value, false); assert.equal(h.executionId.value, 'example-run'); assert.deepEqual(h.starts, [{ withLive: true, actuatorUsername: 'example-actuator', executionId: 'example-run' }])
  const stored = h.stored(); assert.equal(stored.owner, scopeOwner); assert.equal(stored.environment, 0); assert.equal(stored.executionId, 'example-run'); assert.equal(JSON.stringify(stored).includes('example-session'), false)
})
test('known active task prevents another launch; pending polls use one second and silent errors', async t => {
  const h = setup(); t.after(h.close); await h.launch(); await flush(); assert.equal(await h.launch(), false); assert.equal(h.writes.length, 1); assert.ok(h.reads.some(value => value[0] === 'task' && value[2] === true)); assert.equal([...h.timers.values()][0].delay, 1000)
})
test('context replacement during preparation cannot submit a request for the new case', async t => {
  const pending = deferred(), h = setup(); t.after(h.close); const saving = h.launch(() => pending.promise); await flush(); await flush(); h.state.caseId = 2; pending.resolve({ withLive: false }); assert.equal(await saving, false); assert.deepEqual(h.writes, []); assert.deepEqual(h.starts, [])
})
test('submitted request keeps a physical lock across environment changes and persists only original owner', async t => {
  const pending = deferred(), h = setup({ run: () => pending.promise }); t.after(h.close); const saving = h.launch(); await flush(); await flush(); h.user.selected_environment = 2; await flush(); assert.equal(h.submitting.value, true); assert.equal(await h.launch(), false)
  pending.resolve(submission()); assert.equal(await saving, false); assert.equal(h.submitting.value, false); assert.equal(h.stored().environment, 0); assert.deepEqual(h.starts, []); assert.deepEqual(h.messages, []); assert.equal(h.executionId.value, '')
})
test('failed/ambiguous submission triggers recovery instead of blindly submitting again', async t => {
  let fail = true; const h = setup({ run: async () => { if (fail) throw Error('network'); return submission() } }); t.after(h.close); assert.equal(await h.launch(), false); assert.match(h.error.value, /核对/); assert.equal(h.active.value, true); assert.equal([...h.timers.values()][0].delay, 1500)
  fail = false; await h.tick(1500); assert.equal(h.active.value, false); assert.equal(await h.launch(), true); assert.equal(h.writes.length, 2)
})
test('metadata failure keeps task active and retries at 1500ms without loading the page', async t => {
  let fail = true; const h = setup({ task: async () => { if (fail) throw Error('network'); return task() } }); t.after(h.close); h.store(); await h.recover(); await flush(); assert.match(h.error.value, /重试/); assert.equal(h.active.value, true); assert.equal(h.recovering.value, false); assert.equal([...h.timers.values()][0].delay, 1500)
  fail = false; await h.tick(1500); assert.equal(h.error.value, ''); assert.equal([...h.timers.values()][0].delay, 1000)
})
test('terminal outcomes notify once and clear only the completed observation', async () => {
  for (const status of ['success', 'failed', 'interrupted', 'cancelled', 'timeout']) {
    const h = setup({ task: async () => task({ status, result: finalResult(), error_message: 'Example failure' }) })
    try { h.store(); await h.recover(); await flush(); assert.equal(h.active.value, false); assert.equal(h.finishes.length, 1); assert.equal(h.notifications.length, 1); assert.equal(h.notifications[0][0], status === 'success' ? 'success' : status === 'cancelled' ? 'warning' : 'error'); assert.equal(h.stored(), null); await h.recover(); await flush(); assert.equal(h.notifications.length, 1) } finally { h.close() }
  }
})
test('accepted terminal task is not rerun when refreshing its result fails', async t => {
  const h = setup({ task: async () => task({ status: 'success', result: finalResult() }), finish: async () => { throw Error('render') } }); t.after(h.close); h.store(); await h.recover(); await flush(); assert.match(h.error.value, /结果加载失败/); assert.equal(h.active.value, false); assert.equal(h.notifications.length, 1); assert.deepEqual(h.writes, []); assert.equal(h.stored(), null)
})
test('legacy recovery does not bind an unknown environment before terminal result validation', async () => {
  for (const environment of [0, 2]) {
    let completed = false; const h = setup({ task: async () => completed ? task({ status: 'success', result: finalResult({ test_env: environment }) }) : task() })
    try { h.store({ taskId: long, businessType: 'u_case' }, 'ui-case-run'); await h.recover(); await flush(); assert.equal(h.executionId.value, ''); assert.equal(h.stored(), null); assert.match(h.error.value, /核对执行环境/); assert.equal(h.active.value, true); completed = true; await h.tick(1000); assert.equal(h.stored('ui-case-run'), null); assert.equal(h.notifications.length, environment === 0 ? 1 : 0); assert.equal(h.finishes.length, environment === 0 ? 1 : 0) } finally { h.close() }
  }
})
test('multiple unscoped tasks are not arbitrarily selected and recovery retries without dispatching', async t => {
  let many = true; const h = setup({ active: async () => many ? active(task(), task({ task_id: 2 })) : active() }); t.after(h.close); assert.equal(await h.launch(), false); assert.deepEqual(h.writes, []); assert.match(h.error.value, /多个/); assert.equal(h.reads.some(value => value[0] === 'task'), false); many = false; await h.tick(1500); assert.equal(h.active.value, false)
})
test('invalid task scope never applies a result or clears an unrelated stored task', async t => {
  const h = setup({ task: async () => task({ business_id: 2, status: 'success', result: finalResult() }) }); t.after(h.close); h.store(); await h.recover(); await flush(); assert.equal(h.active.value, true); assert.deepEqual(h.notifications, []); assert.deepEqual(h.finishes, []); assert.notEqual(h.stored(), null); assert.match(h.error.value, /重试/)
})
test('corrupt local observation is not queried and server recovery remains available', async t => {
  const h = setup(); t.after(h.close); h.store({ ...scopedObservation(), owner: 'other' }); assert.equal(await h.recover(), true); assert.equal(h.reads.some(value => value[0] === 'task'), false); assert.equal(h.stored(), null); assert.equal(h.active.value, false)
})
const changes = [h => h.state.caseId = 2, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1']
test('identity changes reject late terminal effects and leave snapshots scoped to the original context', async () => {
  for (const change of changes) {
    const pending = deferred(), h = setup({ task: () => pending.promise })
    try { h.store(); await h.recover(); await flush(); change(h); pending.resolve(task({ status: 'success', result: finalResult() })); await flush(); assert.deepEqual(h.finishes, []); assert.deepEqual(h.notifications, []); assert.notEqual(h.stored(), null) } finally { h.close() }
  }
})
test('background/KeepAlive pause timers, reject outstanding poll and resume without overlapping reads', async () => {
  for (const leave of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn())]) {
    const pending = deferred(); let calls = 0; const h = setup({ task: () => ++calls === 1 ? pending.promise : Promise.resolve(task()) })
    try { h.store(); h.mount(); await h.recover(); await flush(); leave(h); h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(calls, 1); pending.resolve(task({ status: 'success', result: finalResult() })); await flush(); assert.deepEqual(h.notifications, []); assert.equal([...h.timers.values()][0].delay, 0); await h.tick(0); assert.equal(calls, 2); assert.equal(h.active.value, true) } finally { h.close() }
  }
})
test('unmount cancels retries and pending submit cannot emit or notify into another page', async t => {
  const pending = deferred(), h = setup({ run: () => pending.promise }); t.after(h.close); const saving = h.launch(); await flush(); await flush(); h.callbacks.unmount.forEach(fn => fn()); pending.resolve(submission()); assert.equal(await saving, false); assert.equal(h.submitting.value, false); assert.deepEqual(h.starts, []); assert.deepEqual(h.notifications, []); assert.equal(h.timers.size, 0); assert.notEqual(h.stored(), null)
})
test('storage failures keep the accepted execution observable and show a local warning', async t => {
  const h = setup({ failStore: true }); t.after(h.close); assert.equal(await h.launch(), true); assert.equal(h.active.value, true); assert.match(h.error.value, /观察记录保存失败/); assert.equal(h.writes.length, 1)
})
test('missing case/environment and another physical action do not issue a run', async t => {
  const h = setup(); t.after(h.close); h.state.busy = true; assert.equal(await h.launch(), false); h.state.busy = false; h.user.selected_environment = null; assert.equal(await h.launch(), false); h.state.caseId = null; assert.equal(await h.launch(), false); assert.deepEqual(h.writes, [])
})
test('unavailable storage cannot prevent backend discovery or observing a newly accepted run', async t => {
  const h = setup({ failRead: true, failClear: true, failStore: true }); t.after(h.close); assert.equal(await h.launch(), true); assert.equal(h.active.value, true); assert.equal(h.writes.length, 1); assert.match(h.error.value, /观察记录保存失败/)
})
test('old terminal cleanup preserves a newer observation stored for the same case', async t => {
  const pending = deferred(), h = setup({ task: () => pending.promise }); t.after(h.close); h.store(); await h.recover(); await flush(); h.store({ ...scopedObservation(), taskId: '90071992547409930001' }); pending.resolve(task({ status: 'success', result: finalResult() })); await flush(); assert.equal(h.stored().taskId, '90071992547409930001'); assert.equal(h.notifications.length, 1)
})
test('active task discovery failure retries silently and suspends while hidden', async t => {
  let fail = true; const h = setup({ active: async () => { if (fail) throw Error('network'); return active() } }); t.after(h.close); h.mount(); await h.recover(); assert.equal(h.active.value, true); assert.match(h.error.value, /恢复失败/); h.visibility('hidden'); assert.equal(h.timers.size, 0); fail = false; h.visibility('visible'); await flush(); assert.equal(h.active.value, false); assert.equal(h.writes.length, 0); assert.ok(h.reads.filter(value => value[0] === 'active').every(value => value[2] === true))
})
test('executor API keeps exact query keys while supporting silent automatic discovery', () => {
  const calls = [], api = loadModule('src/api/system/executor-task.ts', { '@/api/http': { get: value => calls.push(value), post: () => {} } })
  api.getActiveExecutorTasks({ business_type: 'u_case', business_id: 0 }, true); api.getExecutorTask(long, true)
  assert.equal(calls[0].url, '/system/executor/task/active'); assert.deepEqual(calls[0].data(), { business_type: 'u_case', business_id: 0 }); assert.equal(calls[0].silentError, true); assert.deepEqual(calls[1].data(), { task_id: long }); assert.equal(calls[1].silentError, true)
  api.getActiveExecutorTasks({ business_type: 'u_page_step', business_id: 0 }); assert.equal(calls[2].silentError, false)
})
test('prepared actuator/live options remain the submitted snapshot during network wait', async t => {
  const pending = deferred(), launch = { withLive: true, actuatorUsername: 'original' }, h = setup({ run: () => pending.promise }); t.after(h.close)
  const saving = h.launch(async () => launch); await flush(); await flush(); launch.withLive = false; launch.actuatorUsername = 'changed'; pending.resolve(submission()); assert.equal(await saving, true); assert.deepEqual(h.writes, [[0, 0, 'original']]); assert.equal(h.starts[0].actuatorUsername, 'original'); assert.equal(h.starts[0].withLive, true)
})
test('environment A-B-A retains the physical read lock but rejects its pre-switch completion', async t => {
  const pending = deferred(); let calls = 0; const h = setup({ task: () => ++calls === 1 ? pending.promise : Promise.resolve(task()) }); t.after(h.close); h.store(); h.mount(); await h.recover(); await flush(); h.user.selected_environment = 2; h.user.selected_environment = 0; await flush(); assert.equal(calls, 1); pending.resolve(task({ status: 'success', result: finalResult() })); await flush(); assert.deepEqual(h.notifications, []); assert.deepEqual(h.finishes, []); await h.tick(0); assert.equal(calls, 2)
})
test('parent terminal refresh cannot close a live session opened in a later context', async () => {
  const pending = deferred(), calls = []; let valid = true
  const finish = method('handleCaseExecutionFinished', { applyCaseFinalResult: value => calls.push(value), requireLatestCaseResult: () => calls.push('latest'), doRefresh: () => pending.promise, liveStreamVisible: { value: true }, scheduleCaseLiveAutoClose: () => calls.push('close') }, 'src/views/uitest/case/details/index.vue')
  const finishing = finish({ result: finalResult() }, () => valid); valid = false; pending.resolve(); await finishing; assert.equal(calls.includes('close'), false)
})
test('parent start preserves already arrived progress for the acknowledged execution', () => {
  const value = runtime.mergeCaseRuntimeStep(null, runtime.readCaseRuntimeStep({ id: 0, case_step_details_id: 0, execution_id: 'example-run', test_env: 0, status: 3, element_result_list: [] }), 0), rows = { value: [{ id: 0, status: 3, error_message: null }, { id: 2, status: 1, error_message: null }] }, reset = []
  const run = method('resetCaseRuntimeState', { resetCaseResults: id => reset.push(id), caseSteps: rows, latestUiCaseResult: { value }, applyCaseRuntimeRows: runtime.applyCaseRuntimeRows, replaceCaseSteps: values => rows.value = values }, 'src/views/uitest/case/details/index.vue')
  run('example-run'); assert.deepEqual(reset, ['example-run']); assert.equal(rows.value[0].status, 3); assert.equal(rows.value[1].status, 2)
})
test('terminal continuation becomes stale when another run starts in the same page context', async t => {
  const finish = deferred(), run = deferred(); let continuation, calls = 0
  const h = setup({ run: () => run.promise, task: async () => ++calls === 1 ? task({ status: 'success', result: finalResult() }) : task({ task_id: '90071992547409930001' }), finish: async (_task, current) => { continuation = current; await finish.promise } }); t.after(h.close)
  h.store(); await h.recover(); await flush(); assert.equal(continuation(), true); const saving = h.launch(); assert.equal(continuation(), false); await flush(); await flush(); run.resolve(submission({ task_id: '90071992547409930001', execution_id: 'new-run' })); assert.equal(await saving, true); assert.equal(continuation(), false); finish.resolve(); await flush(); assert.equal(h.executionId.value, 'new-run'); assert.equal(h.active.value, true)
})
