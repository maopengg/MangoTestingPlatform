import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const assets = loadModule('src/components/business/ui-case-step-create.ts')
const dto = loadModule('src/views/uitest/case/details/live-actuators.ts', { '@/components/business/ui-case-step-create': assets })
const actuator = (changes = {}) => ({ username: 'example-actuator', name: 'Example', web_live_stream_supported: true, is_owner: true, is_full: false, active_user_count: 0, max_user_count: 5, users: [], ...changes })
const response = (...rows) => ({ code: 200, data: { available_actuators: rows } })
function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, messages = [], reads = [], shown = []
  const state = vue.reactive({ id: 0, busy: false, executing: false }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const user = vue.reactive({ userId: 1, userName: 'example-user', roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const module = loadModule('src/views/uitest/case/details/composables/useCaseLiveStream.ts', {
    vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
    '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning'].map(kind => [kind, value => messages.push([kind, value])])) },
    '@/api/system/socket_api': { getSystemSocketCurrentActuatorStatus: () => { reads.push(true); return overrides.read ? overrides.read() : Promise.resolve(response(actuator())) } },
    '@/utils/minimum-loading': { waitForMinimumLoading: () => overrides.minimum?.() ?? Promise.resolve() }, '../live-actuators': dto,
  })
  const scope = vue.effectScope(), h = scope.run(() => module.useCaseLiveStream({ caseId: () => state.id, busy: () => state.busy, executionActive: () => state.executing, shown: async current => { shown.push(current); await overrides.shown?.(current) } }))
  callbacks.mount.forEach(fn => fn())
  return { ...h, state, route, user, permission, reads, messages, shown, callbacks,
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    closeHarness() { callbacks.unmount.forEach(fn => fn()); scope.stop(); globalThis.document = previous },
  }
}
test('actuator boundary validates occupancy and retains only finite display fields', () => {
  const [row] = dto.readCaseLiveActuators(response(actuator({ max_user_count: 0, ip: 'example.org', connection_id: 'private', users: [{ username: 'example-user', user_id: 1 }] }), actuator({ username: 'unsupported', web_live_stream_supported: false })))
  assert.deepEqual(row, { username: 'example-actuator', name: 'Example', owner: true, full: false, activeUsers: 0, maxUsers: 0, users: ['example-user'] })
  for (const value of [{ code: 403 }, { code: 200, data: {} }, response(actuator({ username: '' })), response(actuator({ is_full: 'yes' })), response(actuator({ active_user_count: -1 })), response(actuator({ users: {} })), response(actuator(), actuator())]) assert.throws(() => dto.readCaseLiveActuators(value))
})
test('opening has one request, local loading, eligible-owner selection and immutable preparation', async t => {
  const pending = deferred(), h = setup({ read: () => pending.promise }); t.after(h.closeHarness)
  const opening = h.open(); assert.equal(h.open(), opening); await flush(); assert.equal(h.opening.value, true); assert.equal(h.loading.value, true); assert.equal(h.visible.value, true); assert.equal(h.reads.length, 1)
  pending.resolve(response(actuator({ username: 'full-owner', is_full: true }), actuator({ username: 'guest', is_owner: false }), actuator()))
  assert.equal(await opening, true); assert.equal(h.selected.value, 'example-actuator'); assert.equal(h.shown.length, 1); assert.equal(h.loading.value, false); assert.equal(h.opening.value, false)
  const launch = await h.prepare(true, () => true); h.selected.value = 'guest'; assert.deepEqual(launch, { withLive: true, actuatorUsername: 'example-actuator' })
  h.selected.value = 'full-owner'; assert.equal(h.selected.value, 'guest'); h.state.busy = true; h.selected.value = 'example-actuator'; assert.equal(h.selected.value, 'guest'); h.state.busy = false; h.state.executing = true; h.selected.value = ''; assert.equal(h.selected.value, 'guest')
})
test('full executor remains selectable by its occupying user and zero case IDs are valid', async t => {
  const h = setup({ read: async () => response(actuator({ is_full: true, users: [{ username: 'example-user' }] })) }); t.after(h.closeHarness)
  await h.open(); assert.equal(h.choices.value[0].disabled, false); assert.deepEqual(await h.prepare(true, () => true), { withLive: true, actuatorUsername: 'example-actuator' }); assert.deepEqual(await h.prepare(false, () => true), { withLive: false })
})
test('failure retains last options and manual retry recovers without swallowing local feedback', async t => {
  let fail = false; const h = setup({ read: async () => { if (fail) throw Error('network'); return response(actuator()) } }); t.after(h.closeHarness)
  await h.open(); fail = true; assert.equal(await h.load(), false); assert.equal(h.loading.value, false); assert.equal(h.choices.value.length, 1); assert.match(h.error.value, /重试/); assert.equal(await h.prepare(true, () => true), null)
  fail = false; assert.equal(await h.load(true), true); assert.equal(h.error.value, ''); assert.equal(h.messages.length, 1)
})
test('empty list prevents live launch while non-live launch remains available', async t => {
  const h = setup({ read: async () => response() }); t.after(h.closeHarness); await h.open()
  assert.equal(await h.prepare(true, () => true), null); assert.match(h.error.value, /请选择/); assert.deepEqual(await h.prepare(false, () => true), { withLive: false }); assert.equal(h.loading.value, false)
})
test('close and reopen cannot let the previous opening clear the new loading state', async t => {
  const waits = [], h = setup({ minimum: () => { const pending = deferred(); waits.push(pending); return pending.promise } }); t.after(h.closeHarness)
  const first = h.open(); await flush(); h.close(); const second = h.open(); await flush(); assert.equal(waits.length, 2); assert.equal(h.opening.value, true)
  waits[0].resolve(); await first; assert.equal(h.opening.value, true); waits[1].resolve(); await second; assert.equal(h.opening.value, false); assert.equal(h.visible.value, true)
})
test('close while reading never scrolls a hidden live view or restores execution identifiers', async t => {
  const pending = deferred(), h = setup({ read: () => pending.promise }); t.after(h.closeHarness)
  const opening = h.open(); await flush(); h.close(); pending.resolve(response(actuator())); assert.equal(await opening, false); assert.equal(h.visible.value, false); assert.equal(h.shown.length, 0); assert.equal(h.executionId.value, '')
})
const changes = [h => h.state.id = 2, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1']
test('identity replacement rejects late metadata, view opening and preparation including A-B-A', async () => {
  for (const change of [...changes, h => { h.state.id = 2; h.state.id = 0 }]) {
    const pending = deferred(), h = setup({ read: () => pending.promise })
    try { const opening = h.open(), launch = h.prepare(true, () => true); await flush(); change(h); pending.resolve(response(actuator())); assert.equal(await opening, false); assert.equal(await launch, null); assert.equal(h.visible.value, false); assert.deepEqual(h.choices.value, []); assert.equal(h.shown.length, 0); assert.equal(h.loading.value, false) } finally { h.closeHarness() }
  }
})
test('background and KeepAlive hide the view, reject old metadata and restore intent silently', async () => {
  for (const pause of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn())]) {
    const pending = deferred(); let calls = 0; const h = setup({ read: () => ++calls === 1 ? pending.promise : Promise.resolve(response(actuator({ name: 'New' }))) })
    try { const opening = h.open(); await flush(); pause(h); assert.equal(h.visible.value, false); assert.equal(h.opening.value, false); h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(h.visible.value, true); assert.equal(h.loading.value, false); pending.resolve(response(actuator({ name: 'Old' }))); assert.equal(await opening, false); assert.equal(h.choices.value[0].name, 'New'); assert.equal(h.messages.length, 0) } finally { h.closeHarness() }
  }
})
test('ready and matching completion notify once; manually hidden view is never reopened', async t => {
  const h = setup(); t.after(h.closeHarness); await h.open(); h.started({ withLive: true, executionId: 'example-run', actuatorUsername: 'example-actuator' }); h.state.executing = true
  h.ready(); h.ready(); assert.equal(h.messages.length, 1); h.finish('old'); assert.equal(h.visible.value, true); h.close(); assert.equal(h.executionId.value, 'example-run'); h.finish('example-run'); assert.equal(h.messages.length, 1); assert.equal(h.visible.value, false)
  await h.open(); h.finish('example-run'); assert.equal(h.visible.value, false); assert.equal(h.messages.length, 2); h.finish('example-run'); assert.equal(h.messages.length, 2)
})
test('unmount invalidates pending metadata without later notifications or scrolling', async t => {
  const pending = deferred(), h = setup({ read: () => pending.promise }); t.after(h.closeHarness)
  const opening = h.open(); await flush(); h.callbacks.unmount.forEach(fn => fn()); pending.resolve(response(actuator())); assert.equal(await opening, false); assert.deepEqual(h.choices.value, []); assert.equal(h.messages.length, 0); assert.equal(h.shown.length, 0); assert.equal(await h.open(), false)
})
test('non-live launch and terminal hidden view cannot retain an earlier execution as the current live source', async t => {
  const h = setup(); t.after(h.closeHarness); await h.open(); h.started({ withLive: true, executionId: 'old', actuatorUsername: 'example-actuator' }); h.state.executing = true; h.close()
  h.started({ withLive: false, executionId: 'new' }); assert.equal(h.executionId.value, ''); assert.equal(h.actuator.value, '')
  h.started({ withLive: true, executionId: 'current' }); h.state.executing = false; h.finish('current'); assert.equal(h.executionId.value, ''); assert.equal(h.messages.length, 0)
})
