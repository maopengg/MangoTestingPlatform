import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import { loadModule } from './helpers/auth-config-harness.mjs'

function setup() {
  const previous = { setTimeout: globalThis.setTimeout, clearTimeout: globalThis.clearTimeout, document: globalThis.document }
  let now = 0, nextId = 0
  const timers = new Map(), listeners = new Map(), hooks = {}, requests = [], errors = []
  globalThis.setTimeout = (callback, delay) => { const id = ++nextId; timers.set(id, { at: now + delay, callback }); return id }
  globalThis.clearTimeout = id => timers.delete(id)
  globalThis.document = { visibilityState: 'visible', addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: name => listeners.delete(name) }
  const runtime = { ...vue }
  for (const name of ['onMounted', 'onActivated', 'onDeactivated', 'onBeforeUnmount']) runtime[name] = fn => { hooks[name] = fn }
  const { useDebouncedSearch } = loadModule('src/hooks/useDebouncedSearch.ts', {
    vue: runtime, '@/utils/load-error': { reportLoadError: (_error, message) => errors.push(message) },
  })
  const values = vue.reactive({ name: '', statuses: [] }), enabled = vue.ref(true), scope = vue.effectScope()
  const search = scope.run(() => useDebouncedSearch(() => { requests.push(JSON.parse(JSON.stringify(values))); return 'queried' }, () => values, { enabled: () => enabled.value }))
  hooks.onMounted()
  return { search, values, enabled, requests, timers, errors, hooks,
    hide() { globalThis.document.visibilityState = 'hidden'; listeners.get('visibilitychange')() },
    async tick(ms) { now += ms; for (const [id, task] of [...timers]) if (task.at <= now) { timers.delete(id); task.callback() }; await vue.nextTick() },
    close() { scope.stop(); Object.assign(globalThis, previous) },
  }
}

test('typing alone does not search; leaving a changed control waits 500ms', async t => {
  const h = setup(); t.after(h.close)
  h.values.name = 'edited'; await h.tick(1000); assert.equal(h.requests.length, 0)
  h.search.schedule(); await h.tick(499); assert.equal(h.requests.length, 0)
  await h.tick(1); assert.deepEqual(h.requests, [{ name: 'edited', statuses: [] }])
})

test('rapid edits across text and selection controls coalesce to the last snapshot', async t => {
  const h = setup(); t.after(h.close)
  h.values.name = 'a'; h.search.schedule(); await h.tick(200)
  h.values.statuses = ['running']; h.search.schedule(); await h.tick(299)
  h.values.name = 'ab'; h.search.schedule(); await h.tick(499)
  assert.equal(h.requests.length, 0); await h.tick(1)
  assert.deepEqual(h.requests, [{ name: 'ab', statuses: ['running'] }])
})

test('unchanged hover/blur events do not query or postpone a pending search', async t => {
  const h = setup(); t.after(h.close)
  h.search.schedule(); assert.equal(h.timers.size, 0)
  h.values.name = 'a'; h.search.schedule(); await h.tick(300)
  h.search.schedule(); await h.tick(200); assert.equal(h.requests.length, 1)
  h.search.schedule(); await h.tick(1000); assert.equal(h.requests.length, 1)
})

test('manual search runs immediately and cancels the pending automatic query', async t => {
  const h = setup(); t.after(h.close)
  h.values.name = 'a'; h.search.schedule(); assert.equal(h.search.run(), 'queried')
  assert.equal(h.requests.length, 1); assert.equal(h.timers.size, 0)
  await h.tick(1000); assert.equal(h.requests.length, 1)
})

test('reverting to the applied values or resetting cancels obsolete queries', async t => {
  const h = setup(); t.after(h.close)
  h.values.name = 'a'; h.search.schedule(); h.values.name = ''; h.search.schedule()
  await h.tick(500); assert.equal(h.requests.length, 0)
  h.values.name = 'b'; h.search.schedule(); h.search.cancel(); h.values.name = ''; h.search.sync()
  h.search.schedule(); await h.tick(500); assert.equal(h.requests.length, 0)
})

test('closing a panel, hiding the browser and leaving the page cancel pending searches', async t => {
  const h = setup(); t.after(h.close)
  h.values.name = 'a'; h.search.schedule(); h.enabled.value = false
  await h.tick(500); assert.equal(h.requests.length, 0)
  h.enabled.value = true; h.values.name = 'b'; h.search.schedule(); h.hide()
  await h.tick(500); assert.equal(h.requests.length, 0)
  globalThis.document.visibilityState = 'visible'
  h.values.name = 'c'; h.search.schedule(); h.hooks.onDeactivated()
  await h.tick(500); assert.equal(h.requests.length, 0)
  h.hooks.onActivated(); h.values.name = 'd'; h.search.schedule()
  h.hooks.onBeforeUnmount(); await h.tick(500); assert.equal(h.requests.length, 0)
})

test('scope disposal clears timers without requiring component unmount', async () => {
  const h = setup()
  h.values.name = 'a'; h.search.schedule(); assert.equal(h.timers.size, 1)
  h.close(); assert.equal(h.timers.size, 0)
})
