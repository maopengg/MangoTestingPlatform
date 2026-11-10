import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'

const session = (id = 'example-stream', changes = {}) => ({ code: 200, data: { stream_id: id, subscribe_url: '/example/subscribe', ...changes } })
function setup(overrides = {}) {
  const previous = { document: globalThis.document, window: globalThis.window, WebSocket: globalThis.WebSocket }
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }), timers = new Map(), callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }
  let timerId = 0
  globalThis.document = doc
  globalThis.window = { location: { protocol: 'https:', host: 'example.org', port: '', hostname: 'example.org' }, setTimeout: (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id }, clearTimeout: id => timers.delete(id), setInterval: (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id }, clearInterval: id => timers.delete(id) }
  const sockets = [], creates = [], closes = [], starts = [], messages = []
  globalThis.WebSocket = class {
    static CONNECTING = 0; static OPEN = 1
    readyState = 0; sent = []
    constructor(url) { vue.markRaw(this); this.url = url; sockets.push(this) }
    send(value) { this.sent.push(JSON.parse(value)) }
    close() { this.readyState = 3; this.onclose?.({}) }
    open() { this.readyState = 1; this.onopen?.({}) }
  }
  const user = vue.reactive({ userId: 1, roleId: 2, userName: 'example-user', token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const h = harness('index', 'connect,disconnect,restart,streamId,connecting,connected,errorMessage,frameUrl,readyTicket,controlLoading,pageLoading,sendWorkspaceCommand,refreshPages,controlling', {
    filename: path.resolve('src/components/business/UiLiveStreamPanel.vue'), props: { visible: true, executionType: 'ui_case', executionId: 0, readOnly: true, actuatorUsername: 'example-actuator', ...overrides.props },
    modules: {
      vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@arco-design/web-vue/es/icon': {},
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'info'].map(kind => [kind, value => messages.push([kind, value])])) },
      '@/api/uitest/live-stream': {
        createUiLiveStreamSession: (...args) => { creates.push(args); return overrides.create ? overrides.create(...args) : Promise.resolve(session(`stream-${creates.length}`)) },
        closeUiLiveStreamSession: (...args) => { closes.push(args); return overrides.close ? overrides.close(...args) : Promise.resolve({ code: 200 }) },
        startUiLiveStreamSession: (...args) => { starts.push(args); return overrides.start ? overrides.start(...args) : Promise.resolve({ code: 200 }) },
      },
    },
  })
  return { ...h, callbacks, user, permission, route, sockets, creates, closes, starts, messages, timers,
    mount() { callbacks.mount.forEach(fn => fn()) },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    async tick(delay) { const entries = [...timers.entries()].filter(([, value]) => value.delay === delay); entries.forEach(([id]) => timers.delete(id)); entries.forEach(([, value]) => value.fn()); await flush() },
    cleanup() { callbacks.unmount.forEach(fn => fn()); h.close(); Object.assign(globalThis, previous) },
  }
}
test('session request preserves zero ID and fixed options; duplicate mount/activation do not create another session', async t => {
  const pending = deferred(), h = setup({ create: () => pending.promise }); t.after(h.cleanup); h.mount(); h.callbacks.activate.forEach(fn => fn()); await flush()
  assert.equal(h.creates.length, 1); assert.deepEqual(h.creates[0], ['ui_case', 0, { resourceId: undefined, readOnly: true, actuatorUsername: 'example-actuator' }]); assert.equal(h.connecting.value, true)
  pending.resolve(session()); await flush(); assert.equal(h.sockets.length, 1); h.sockets[0].open(); assert.equal(h.connected.value, true); assert.equal(h.connecting.value, false); await h.connect(); assert.equal(h.creates.length, 1)
})
test('close during creation releases late session and cannot create a socket', async t => {
  const pending = deferred(), h = setup({ create: () => pending.promise }); t.after(h.cleanup); const opening = h.connect(); await flush(); h.props.visible = false; pending.resolve(session()); await opening; await flush()
  assert.deepEqual(h.closes, [['example-stream', true]]); assert.equal(h.sockets.length, 0); assert.equal(h.streamId.value, ''); assert.equal(h.connecting.value, false); assert.equal(h.timers.size, 0)
})
test('close/reopen retains physical creation lock until stale resource cleanup completes', async t => {
  const pending = deferred(), cleanup = deferred(); let count = 0
  const h = setup({ create: () => ++count === 1 ? pending.promise : Promise.resolve(session('new')), close: () => cleanup.promise }); t.after(h.cleanup)
  const opening = h.connect(); await flush(); h.props.visible = false; h.props.visible = true; await flush(); assert.equal(count, 1)
  pending.resolve(session('old')); await flush(); assert.equal(count, 1); assert.equal(h.sockets.length, 0); cleanup.resolve({ code: 200 }); await opening; await flush(); assert.equal(count, 2); assert.equal(h.streamId.value, 'new'); assert.equal(h.sockets.length, 1)
})
test('old socket callbacks cannot mutate or render into its replacement', async t => {
  const h = setup(); t.after(h.cleanup); await h.connect(); const old = h.sockets[0]; old.open(); h.props.executionId = 'new-execution'; await flush(); const current = h.sockets[1]; current.open(); const count = h.events.length
  old.onerror?.({}); old.onopen?.({}); old.onmessage?.({ data: new ArrayBuffer(2) }); old.onclose?.({}); assert.equal(h.errorMessage.value, ''); assert.equal(h.frameUrl.value, ''); assert.equal(h.connected.value, true); assert.equal(h.events.length, count); assert.equal(h.streamId.value, 'stream-2')
})
const changes = [h => h.props.executionId = 'new', h => h.props.resourceId = 2, h => h.props.actuatorUsername = 'other', h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.fullPath += '&other=1', h => { h.user.selected_environment = 2; h.user.selected_environment = 0 }]
test('identity replacement rejects old creates and reconnects with the new fixed context', async () => {
  for (const change of changes) {
    const pending = deferred(); let count = 0; const h = setup({ create: () => ++count === 1 ? pending.promise : Promise.resolve(session('new')) })
    try { const opening = h.connect(); await flush(); change(h); await flush(); assert.equal(count, 1); pending.resolve(session('old')); await opening; await flush(); assert.equal(h.closes[0][0], 'old'); assert.equal(h.streamId.value, 'new'); assert.equal(h.sockets.length, 1); assert.equal(h.sockets[0].url.includes(encodeURIComponent(h.user.token)), true) } finally { h.cleanup() }
  }
})
test('background/KeepAlive pause sockets and recover on return; unmount prevents late creation', async () => {
  for (const pause of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn())]) {
    const h = setup()
    try { h.mount(); await flush(); const old = h.sockets[0]; old.open(); pause(h); await flush(); assert.equal(old.readyState, 3); assert.equal(h.streamId.value, ''); h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(h.sockets.length, 2); assert.equal(h.creates.length, 2) } finally { h.cleanup() }
  }
  const pending = deferred(), h = setup({ create: () => pending.promise })
  try { const opening = h.connect(); await flush(); h.callbacks.unmount.forEach(fn => fn()); pending.resolve(session()); await opening; assert.equal(h.sockets.length, 0); assert.equal(h.closes.length, 1) } finally { h.cleanup() }
})
test('late publisher start cannot schedule timers, focus or errors after closing', async () => {
  for (const reject of [false, true]) {
    const pending = deferred(), h = setup({ start: () => pending.promise })
    try { await h.connect(); const ws = h.sockets[0]; ws.open(); ws.onmessage({ data: JSON.stringify({ type: 'subscriber_ready', ready_ticket: 'example-ticket' }) }); await flush(); h.props.visible = false; if (reject) pending.reject(Error('late')); else pending.resolve({ code: 200 }); await flush(); assert.equal(h.timers.size, 0); assert.equal(h.errorMessage.value, ''); assert.equal(h.messages.length, 0); assert.equal(h.streamId.value, '') } finally { h.cleanup() }
  }
})
test('failed/malformed session uses local feedback and reconnects at the existing retry interval', async () => {
  for (const invalid of [{ code: 403 }, session('bad', { subscribe_url: null })]) {
    let fail = true; const h = setup({ create: async () => fail ? invalid : session() })
    try { await h.connect(); assert.equal(h.sockets.length, 0); assert.equal(h.connecting.value, false); assert.match(h.errorMessage.value, /响应无效/); assert.equal([...h.timers.values()][0].delay, 1000); fail = false; await h.tick(1000); assert.equal(h.sockets.length, 1) } finally { h.cleanup() }
  }
})
test('pending remote-control acquisition cannot issue a command into the replacement session', async t => {
  const h = setup({ props: { readOnly: false } }); t.after(h.cleanup); await h.connect(); h.sockets[0].open(); const command = h.sendWorkspaceCommand('pick_element', { x: 0.5, y: 0.5 }); await flush(); h.props.executionId = 'new'; await flush(); h.sockets[1].open(); assert.equal(await command, false); assert.equal(h.sockets[1].sent.length, 0)
})
test('live session API supports silent cleanup while preserving default behavior and request paths', () => {
  const calls = [], api = loadModule('src/api/uitest/live-stream.ts', { '@/api/http': { deleted: value => calls.push(value), post: value => calls.push(value), get() {} } })
  api.closeUiLiveStreamSession('example'); api.closeUiLiveStreamSession('example', true); assert.equal(calls[0].silentError, false); assert.equal(calls[1].silentError, true); assert.equal(calls[0].url, '/ui/live-stream/session/example')
})
test('all existing live execution modes preserve resource and publisher-start protocols', async () => {
  for (const executionType of ['ui_case', 'page_step_debug', 'element_check', 'element_workspace', 'page_step_workspace']) {
    const h = setup({ props: { executionType, executionId: '90071992547409930000', resourceId: 0 } })
    try { await h.connect(); assert.equal(h.creates[0][0], executionType); assert.equal(h.creates[0][1], '90071992547409930000'); assert.equal(h.creates[0][2].resourceId, 0); h.sockets[0].open(); h.sockets[0].onmessage({ data: JSON.stringify({ type: 'subscriber_ready', ready_ticket: 'example-ticket' }) }); await flush(); assert.deepEqual(h.starts, [['stream-1', 'example-ticket']]); assert.equal([...h.timers.values()][0].delay, executionType.endsWith('workspace') ? 30000 : 35000) } finally { h.cleanup() }
  }
})
test('workspace expiry notifies the current workspace once and does not schedule reconnect', async t => {
  const h = setup({ props: { executionType: 'element_workspace', executionId: 'example-workspace' }, create: async () => { throw { msg: '实时工作区不存在' } } }); t.after(h.cleanup)
  await h.connect(); assert.deepEqual(h.events.filter(value => value[0] === 'workspace-expired'), [['workspace-expired', 'example-workspace']]); assert.equal(h.timers.size, 0); assert.equal(h.sockets.length, 0)
})
test('missing workspace restart requests recreation while stale restart cannot connect another context', async () => {
  const h = setup({ props: { executionType: 'element_workspace', executionId: '' } })
  try { await h.restart(); assert.deepEqual(h.events, [['reconnect-workspace']]); assert.equal(h.creates.length, 0) } finally { h.cleanup() }
  const pending = deferred(), other = setup({ close: () => pending.promise })
  try { await other.connect(); const restarting = other.restart(); other.props.visible = false; pending.resolve({ code: 200 }); await restarting; assert.equal(other.creates.length, 1); assert.equal(other.sockets.length, 1) } finally { other.cleanup() }
})
test('remote cleanup failure cannot display an abandoned stream or prevent a later reconnect', async t => {
  const pending = deferred(); let count = 0; const h = setup({ create: () => ++count === 1 ? pending.promise : Promise.resolve(session('new')), close: async () => { throw Error('network') } }); t.after(h.cleanup)
  const opening = h.connect(); await flush(); h.props.visible = false; h.props.visible = true; pending.resolve(session('old')); await opening; await flush(); assert.equal(h.sockets.length, 1); assert.equal(h.streamId.value, 'new'); assert.equal(h.messages.length, 0)
})
