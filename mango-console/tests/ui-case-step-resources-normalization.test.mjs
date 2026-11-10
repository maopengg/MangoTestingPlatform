import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred } from './helpers/case-details-harness.mjs'
function setup() {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, state = vue.reactive({ id: 0 }), user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' }), invalidated = [], resumed = []
  const module = loadModule('src/views/uitest/page-steps/details/composables/useStepResources.ts', { vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) }, 'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission } })
  const scope = vue.effectScope(), h = scope.run(() => module.useStepResources({ enabled: () => true, context: () => state.id, invalidated: () => invalidated.push(true), resume: () => resumed.push(true) })); callbacks.mount.forEach(fn => fn())
  return { ...h, state, user, permission, route, callbacks, invalidated, resumed, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) }, cleanup() { callbacks.unmount.forEach(fn => fn()); scope.stop(); globalThis.document = previous } }
}
test('step resource loads and failures are independent and successful retry clears only its error', async t => {
  const h = setup(); t.after(h.cleanup); const pending = deferred(), values = []
  const steps = h.read('steps', () => pending.promise, value => values.push(value)); assert.equal(h.loading.steps, true); assert.equal(h.loading.aliases, false)
  assert.equal(await h.read('aliases', async () => { throw Error('network') }, () => {}), false); assert.match(h.errors.aliases, /重试/); assert.equal(h.loading.steps, true)
  pending.resolve('current'); assert.equal(await steps, true); assert.deepEqual(values, ['current']); assert.equal(await h.read('aliases', async () => [], () => {}), true); assert.equal(h.errors.aliases, '')
})
test('superseded reads cannot apply a result or release newer resource loading', async t => {
  const h = setup(); t.after(h.cleanup); const first = deferred(), second = deferred(), values = []
  const old = h.read('steps', () => first.promise, value => values.push(value)), current = h.read('steps', () => second.promise, value => values.push(value)); first.resolve('old'); assert.equal(await old, false); assert.equal(h.loading.steps, true); second.resolve('new'); assert.equal(await current, true); assert.deepEqual(values, ['new']); assert.equal(h.loading.steps, false)
})
test('changed case/session/permissions and A-B-A invalidate reads and request a fresh embedded view', async () => {
  for (const change of [h => h.state.id = 2, h => { h.state.id = 2; h.state.id = 0 }, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read')]) {
    const h = setup(), pending = deferred(), values = []
    try { const read = h.read('steps', () => pending.promise, value => values.push(value)); change(h); pending.resolve('stale'); assert.equal(await read, false); assert.equal(values.length, 0); assert.equal(h.invalidated.length > 0, true); assert.equal(h.resumed.length > 0, true) } finally { h.cleanup() }
  }
})
test('hidden and deactivated views pause, return resumes, unmounted and departed routes never resume', async () => {
  for (const leave of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn()), h => h.callbacks.unmount.forEach(fn => fn()), h => h.route.path = '/other']) {
    const h = setup(), pending = deferred(), values = []
    try { const read = h.read('elements', () => pending.promise, value => values.push(value)); leave(h); pending.resolve('stale'); assert.equal(await read, false); assert.equal(values.length, 0); const before = h.resumed.length; h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); assert.equal(h.resumed.length > before, h.route.path !== '/other' && leave.toString().includes('unmount') === false) } finally { h.cleanup() }
  }
})
