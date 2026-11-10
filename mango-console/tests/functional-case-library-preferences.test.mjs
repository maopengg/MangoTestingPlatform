import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/case-library')
const column = width => [{ field: 'title', title: 'Title', width }]
const stored = width => ({ data: [{ is_default: true, config: { layout_version: 2, columns: column(width) } }] })
function setup(api = {}) {
  const previous = globalThis.window
  globalThis.window = { setTimeout, clearTimeout }
  const hooks = { mount: [], activate: [], stop: [], unmount: [], leave: [] }
  const route = vue.reactive({ path: '/functional-test/case/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 1 })
  const f = harness('index', 'columns,userOptions,setupLoading,setupError,loadSetup,saveGridView,flushGridView,viewSaving,viewSaveError,rows,loading,loadError,refreshCases,saveInline,flushInlineUpdates', {
    base,
    api: { getUserName: async () => ({ data: [{ key: 1, title: 'Example' }] }), getFunctionalGridView: async () => stored(240), ...api },
    modules: {
      vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.stop.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      'vue-router': { useRoute: () => route, useRouter: () => ({ push: async () => {} }), onBeforeRouteLeave: fn => hooks.leave.push(fn) },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ getEnum: async () => {} }) },
      xlsx: {},
    },
  })
  return { ...f, hooks, route, user, cleanup: () => { hooks.unmount.forEach(fn => fn()); f.close(); globalThis.window = previous } }
}

test('view save snapshots column settings and retries rejected writes with separate feedback', async () => {
  let fail = true; const writes = []
  const f = setup({ saveFunctionalGridView: async body => { writes.push(body); if (fail) throw Error('Rejected') } })
  try {
    f.saveGridView(column(400)); f.columns.value[0].width = 999
    await f.flushGridView()
    assert.equal(writes[0].config.columns[0].width, 400)
    assert.equal(f.viewSaveError.value, true); assert.equal(f.viewSaving.value, false)
    assert.equal(f.setupError.value, false)
    fail = false; await f.flushGridView()
    assert.equal(writes.length, 2); assert.equal(writes[1].config.columns[0].width, 400)
    assert.equal(f.viewSaveError.value, false); assert.equal(f.viewSaving.value, false)
  } finally { f.cleanup() }
})

test('view writes are serial and a newer queued layout is saved after the in-flight layout', async () => {
  const first = deferred(), second = deferred(), writes = []
  const f = setup({ saveFunctionalGridView: body => { writes.push(body); return writes.length === 1 ? first.promise : second.promise } })
  try {
    f.saveGridView(column(400)); const old = f.flushGridView(); await flush()
    f.saveGridView(column(500)); const current = f.flushGridView()
    assert.equal(writes.length, 1); assert.equal(f.viewSaving.value, true)
    first.resolve({ data: {} }); await flush()
    assert.equal(writes.length, 2); assert.equal(writes[1].config.columns[0].width, 500)
    second.resolve({ data: {} }); await Promise.all([old, current])
    assert.equal(f.viewSaving.value, false); assert.equal(f.viewSaveError.value, false)
  } finally { f.cleanup() }
})

test('late saved-view read does not overwrite a user layout changed while metadata loaded', async () => {
  const reading = deferred(), writes = []
  const f = setup({ getFunctionalGridView: () => reading.promise, saveFunctionalGridView: async body => { writes.push(body) } })
  try {
    const loading = f.loadSetup(); await flush()
    f.saveGridView(column(450)); reading.resolve(stored(100)); await loading
    assert.equal(f.columns.value[0].width, 450); assert.equal(f.setupLoading.value, false)
    await f.flushGridView(); assert.equal(writes[0].config.columns[0].width, 450)
  } finally { f.cleanup() }
})

test('identity change cancels a pending view debounce before it can use a new account context', async () => {
  const writes = []
  const f = setup({ saveFunctionalGridView: async body => { writes.push(body) } })
  try {
    f.saveGridView(column(400)); f.user.roleId = 2; await flush()
    await f.flushGridView(); assert.equal(writes.length, 0)
    assert.equal(f.viewSaveError.value, false)
  } finally { f.cleanup() }
})

test('A to B to A role changes suppress an old view failure and old loading cleanup', async () => {
  const pending = deferred()
  const f = setup({ saveFunctionalGridView: () => pending.promise })
  try {
    f.saveGridView(column(400)); const writing = f.flushGridView(); await flush()
    f.user.roleId = 2; f.user.roleId = 1; await flush()
    pending.reject(Error('Late failure')); await writing; await flush()
    assert.equal(f.viewSaveError.value, false); assert.equal(f.viewSaving.value, false)
    assert.equal(f.setupError.value, false)
  } finally { f.cleanup() }
})

test('activation waits for an old physical view write before rereading saved preferences', async () => {
  const pending = deferred(); let reads = 0
  const f = setup({ saveFunctionalGridView: () => pending.promise, getFunctionalGridView: async () => { ++reads; return stored(450) } })
  try {
    f.saveGridView(column(450)); const writing = f.flushGridView(); await flush()
    f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await flush()
    assert.equal(reads, 0); assert.equal(f.setupLoading.value, true)
    pending.resolve({ data: {} }); await writing; await flush()
    assert.equal(reads, 1); assert.equal(f.columns.value.find(value => value.field === 'title').width, 450)
    assert.equal(f.setupLoading.value, false)
  } finally { f.cleanup() }
})

test('metadata failure can retry without replacing the list or claiming a successful view save', async () => {
  let fail = true
  const f = setup({ getFunctionalGridView: async () => { if (fail) throw Error('Offline'); return stored(350) } })
  try {
    f.rows.value = [{ id: 11 }]
    await f.loadSetup(); assert.equal(f.setupError.value, true); assert.equal(f.setupLoading.value, false)
    assert.equal(f.rows.value[0].id, 11); assert.equal(f.viewSaveError.value, false)
    fail = false; await f.loadSetup()
    assert.equal(f.setupError.value, false); assert.equal(f.columns.value.find(value => value.field === 'title').width, 350)
  } finally { f.cleanup() }
})

test('old metadata cannot refill user options after the page deactivates', async () => {
  const pending = deferred()
  const f = setup({ getUserName: () => pending.promise })
  try {
    const loading = f.loadSetup(); await flush(); f.hooks.stop.forEach(fn => fn())
    pending.resolve({ data: [{ key: 99, title: 'Old context' }] }); await loading
    assert.deepEqual([...f.userOptions.value], []); assert.equal(f.setupLoading.value, false)
  } finally { f.cleanup() }
})

test('route-leave guard awaits the accepted view write instead of losing its debounce', async () => {
  const pending = deferred(); let calls = 0, completed = false
  const f = setup({ saveFunctionalGridView: async () => { ++calls; await pending.promise } })
  try {
    f.saveGridView(column(400))
    const leaving = f.hooks.leave[0]().then(value => { completed = true; return value })
    await flush(); assert.equal(calls, 1); assert.equal(completed, false)
    pending.resolve({ data: {} }); assert.equal(await leaving, true)
  } finally { f.cleanup() }
})
