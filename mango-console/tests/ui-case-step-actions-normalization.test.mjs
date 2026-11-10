import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const assets = loadModule('src/components/business/ui-case-step-create.ts')
const steps = loadModule('src/views/uitest/case/details/step-list.ts', { '@/components/business/ui-case-step-create': assets })
const long = '90071992547409930000'
const pageStep = (changes = {}) => ({ id: long, name: 'Example step', page: { id: 0, name: 'Example page' }, project_product: { id: 0, name: 'Example product', project: null, ui_client_type: 0 }, module: null, ...changes })
const row = (changes = {}) => ({ id: 0, name: 'Example', page_step: pageStep(), case_data: [], status: 2, error_message: null, error_retry: null, switch_step_open_url: 0, ...changes })
function setup(kind, overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], writes = [], refreshes = [], messages = []
  const state = vue.reactive({ id: 0, rows: [row()], busy: false }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const module = loadModule(`src/views/uitest/case/details/composables/useCaseStep${kind}.ts`, {
    vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
    '@arco-design/web-vue': { Message: Object.fromEntries(['error', 'loading'].map(kind => [kind, value => messages.push([kind, value])])) },
    '@/components/business/ui-case-step-create': assets, '../step-list': steps,
    '@/api/uitest/page-steps': {
      getUiStepsTest: (...args) => { writes.push(args); return overrides.run ? overrides.run(...args) : Promise.resolve({ code: 200, msg: 'submitted' }) },
      getUiSteps: (...args) => { reads.push(args); return overrides.read ? overrides.read(...args) : Promise.resolve({ code: 200, data: [pageStep()] }) },
    },
  })
  const scope = vue.effectScope(), h = scope.run(() => module[`useCaseStep${kind}`]({ caseId: () => state.id, rows: () => state.rows, busy: () => state.busy, refresh: async current => { refreshes.push(current); await overrides.refresh?.(current) } }))
  callbacks.mount.forEach(fn => fn())
  return { ...h, state, route, user, permission, reads, writes, refreshes, messages, callbacks,
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    cleanup() { callbacks.unmount.forEach(fn => fn()); scope.stop(); globalThis.document = previous },
  }
}
const changes = [h => h.state.id = 2, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1', h => { h.user.selected_environment = 2; h.user.selected_environment = 0 }]
test('single step submits fixed long step/zero environment IDs and physically locks through refresh', async t => {
  const pending = deferred(), refreshing = deferred(), h = setup('Execution', { run: () => pending.promise, refresh: () => refreshing.promise }); t.after(h.cleanup)
  const executing = h.run(0); assert.equal(h.running.value, true); assert.equal(await h.run(0), false); await flush(); assert.deepEqual(h.writes, [[long, 0]]); assert.equal(h.pending.value.recordId, 0)
  pending.resolve({ code: 200, msg: 'submitted' }); await flush(); assert.equal(h.running.value, true); assert.equal(h.refreshes.length, 1); assert.equal(await h.run(0), false); refreshing.resolve(); assert.equal(await executing, true); assert.equal(h.running.value, false); assert.deepEqual(h.messages, [['loading', 'submitted']])
})
test('single step failure exposes retry with the same request snapshot', async t => {
  let fail = true; const h = setup('Execution', { run: async () => { if (fail) throw Error('network'); return { code: 200 } } }); t.after(h.cleanup)
  assert.equal(await h.run(0), false); assert.match(h.error.value, /提交失败/); assert.equal(h.running.value, false); assert.equal(h.refreshes.length, 0); fail = false; assert.equal(await h.retry(), true); assert.deepEqual(h.writes, [[long, 0], [long, 0]])
})
test('accepted submission refresh failure retries only refresh and never redispatches execution', async t => {
  let fail = true; const h = setup('Execution', { refresh: async () => { if (fail) throw Error('network') } }); t.after(h.cleanup)
  assert.equal(await h.run(0), false); assert.match(h.error.value, /已提交，结果刷新失败/); fail = false; assert.equal(await h.retry(), true); assert.equal(h.writes.length, 1); assert.equal(h.refreshes.length, 2); assert.equal(h.messages.length, 1)
})
test('missing case/environment/row and other physical action cannot dispatch', async t => {
  const h = setup('Execution'); t.after(h.cleanup); h.state.busy = true; assert.equal(await h.run(0), false); h.state.busy = false; h.user.selected_environment = null; assert.equal(await h.run(0), false); assert.equal(h.messages[0][0], 'error'); h.user.selected_environment = 0; h.state.id = null; assert.equal(await h.run(0), false); h.state.id = 0; assert.equal(await h.run(2), false); h.state.rows = [row({ page_step: null })]; assert.equal(await h.run(0), false); assert.deepEqual(h.writes, [])
})
test('single-step scope changes retain the physical lock and reject stale notifications/refresh/retry', async () => {
  for (const change of changes) {
    const pending = deferred(), h = setup('Execution', { run: () => pending.promise })
    try { const executing = h.run(0); await flush(); change(h); assert.equal(h.running.value, true); assert.equal(await h.run(0), false); pending.resolve({ code: 200, msg: 'old' }); assert.equal(await executing, false); assert.equal(h.running.value, false); assert.equal(h.refreshes.length, 0); assert.equal(h.messages.length, 0); assert.equal(await h.retry(), false) } finally { h.cleanup() }
  }
})
test('background/KeepAlive/unmount and removed/rebound records cannot apply a late single-step result', async () => {
  for (const leave of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn()), h => h.callbacks.unmount.forEach(fn => fn()), h => h.state.rows = [], h => h.state.rows = [row({ page_step: pageStep({ id: 2 }) })]]) {
    const pending = deferred(), h = setup('Execution', { run: () => pending.promise })
    try { const executing = h.run(0); await flush(); leave(h); pending.resolve({ code: 200 }); assert.equal(await executing, false); assert.equal(h.refreshes.length, 0); assert.equal(h.messages.length, 0) } finally { h.cleanup() }
  }
})
test('failed retry is invalidated by rebinding the case step', async t => {
  const h = setup('Execution', { run: async () => ({ code: 403 }) }); t.after(h.cleanup); await h.run(0); h.state.rows = [row({ page_step: pageStep({ id: 2 }) })]; assert.equal(await h.retry(), false); assert.equal(h.writes.length, 1)
})
test('complete detail opens without a metadata request and preserves zero page/client type', async t => {
  const h = setup('Detail'); t.after(h.cleanup); assert.equal(await h.open(0), true); assert.equal(h.visible.value, true); assert.deepEqual(h.target.value, { pageStepsId: long, pageId: 0, pageType: 0 }); assert.equal(h.reads.length, 0); h.visible.value = false; assert.equal(h.target.value, null)
})
test('partial metadata has local loading, validates requested step and retries failure', async t => {
  const pending = deferred(); let fail = true; const h = setup('Detail', { read: () => fail ? pending.promise : Promise.resolve({ code: 200, data: [pageStep()] }) }); t.after(h.cleanup); h.state.rows = [row({ page_step: pageStep({ page: null }) })]
  const opening = h.open(0); await flush(); assert.equal(h.visible.value, true); assert.equal(h.loading.value, true); assert.equal(h.open(0), opening); assert.deepEqual(h.reads, [[{ id: long }]])
  pending.resolve({ code: 200, data: [pageStep({ id: 2 })] }); assert.equal(await opening, false); assert.match(h.error.value, /加载失败/); assert.equal(h.loading.value, false); assert.equal(h.target.value, null); fail = false; assert.equal(await h.retry(), true); assert.equal(h.target.value.pageId, 0)
})
test('detail close/reopen rejects old metadata and finally cannot clear the new read loading', async t => {
  const first = deferred(), second = deferred(); let reads = 0; const h = setup('Detail', { read: () => ++reads === 1 ? first.promise : second.promise }); t.after(h.cleanup); h.state.rows = [row({ page_step: pageStep({ page: null }) })]
  const old = h.open(0); await flush(); h.close(); const next = h.open(0); await flush(); first.resolve({ code: 200, data: [pageStep()] }); assert.equal(await old, false); assert.equal(h.loading.value, true); assert.equal(h.target.value, null); second.resolve({ code: 200, data: [pageStep()] }); assert.equal(await next, true); assert.equal(h.loading.value, false)
})
test('detail context changes close the window and reject late metadata including A-B-A', async () => {
  for (const change of [...changes, h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn()), h => h.callbacks.unmount.forEach(fn => fn()), h => h.state.rows = [], h => h.state.rows = [row({ page_step: pageStep({ id: 2 }) })]]) {
    const pending = deferred(), h = setup('Detail', { read: () => pending.promise })
    try { h.state.rows = [row({ page_step: pageStep({ page: null }) })]; const opening = h.open(0); await flush(); change(h); pending.resolve({ code: 200, data: [pageStep()] }); assert.equal(await opening, false); assert.equal(h.visible.value, false); assert.equal(h.target.value, null); assert.equal(h.loading.value, false) } finally { h.cleanup() }
  }
})
test('selecting another case step while loading details cannot display the old target', async t => {
  const pending = deferred(), h = setup('Detail', { read: () => pending.promise }); t.after(h.cleanup); h.state.rows = [row({ page_step: pageStep({ page: null }) }), row({ id: 2, page_step: pageStep({ id: 3 }) })]
  const old = h.open(0); await flush(); assert.equal(await h.open(2), true); pending.resolve({ code: 200, data: [pageStep()] }); assert.equal(await old, false); assert.equal(h.target.value.pageStepsId, 3)
})
test('detail empty/malformed/denied metadata cannot mount an incomplete page', async () => {
  for (const response of [{ code: 403 }, { code: 200, data: [] }, { code: 200, data: {} }, { code: 200, data: [pageStep({ project_product: null })] }]) {
    const h = setup('Detail', { read: async () => response })
    try { h.state.rows = [row({ page_step: pageStep({ project_product: null }) })]; assert.equal(await h.open(0), false); assert.equal(h.target.value, null); assert.match(h.error.value, /重试/); assert.equal(h.loading.value, false) } finally { h.cleanup() }
  }
})
test('single-step API retains GET query and default error behavior without converting long IDs', () => {
  const calls = [], api = loadModule('src/api/uitest/page-steps.ts', { '@/api/http': { get: value => calls.push(value), deleted() {}, put() {}, post() {} } }); api.getUiStepsTest(long, 0)
  assert.equal(calls[0].url, '/ui/page/steps/test'); assert.equal(calls[0].data().page_step_id, long); assert.equal(calls[0].data().te, 0); assert.equal(calls[0].silentError, false)
})
