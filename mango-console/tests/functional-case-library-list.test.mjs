import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/case-library')
function setup(read) {
  const hooks = { mount: [], activate: [], stop: [], unmount: [] }, calls = []
  const f = harness('CaseEditor', '', { base,
    props: { users: [], contextKey: 'editor', defaults: { projectProduct: 2, module: 3 } },
    api: { getManualCase: query => { calls.push(query); return read(query) } },
    modules: { vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.stop.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) } },
  })
  const rows = vue.ref([]), state = vue.reactive({ context: 'A', identity: 'user-A', available: true, product: 2 })
  let clears = 0
  const scope = vue.effectScope()
  const list = scope.run(() => f.load('composables/useCaseLibraryList.ts').useCaseLibraryList({
    rows, context: () => JSON.stringify([state.identity, state.context]), identity: () => state.identity,
    available: () => state.available, query: () => ({ project_product: state.product, name: '', module: null, unused: undefined, status: 0 }),
    normalize: value => ({ ...value }), clearSelection: () => { ++clears },
  }))
  return { ...list, rows, state, hooks, calls, clears: () => clears, loadFile: f.load,
    cleanup: () => { hooks.unmount.forEach(fn => fn()); scope.stop(); f.close() },
  }
}
const page = (number, total = 6) => ({ data: [{ id: number, title: `Case ${number}` }], totalSize: total })

test('initial load requests four pages of 50, cleans empty query values and appends the next page', async () => {
  const f = setup(async query => page(query.page))
  try {
    await f.loadCases()
    assert.deepEqual(f.calls.map(value => value.page), [1, 2, 3, 4])
    assert.equal(f.rows.value.length, 4); assert.equal(f.pageState.page, 4)
    assert.equal(f.hasMore.value, true); assert.equal(f.loading.value, false); assert.equal(f.loadingMore.value, false)
    for (const query of f.calls) assert.deepEqual(Object.keys(query).sort(), ['page', 'pageSize', 'project_product', 'status'])
    assert.equal(f.calls[0].pageSize, 50); assert.equal(f.calls[0].status, 0)
    await f.loadMoreCases(); assert.equal(f.calls[4].page, 5); assert.equal(f.rows.value.length, 5)
    assert.equal(f.clears(), 5)
  } finally { f.cleanup() }
})

test('first returned page releases table loading while the remaining preload is pending', async () => {
  const slow = deferred()
  const f = setup(query => query.page === 1 ? Promise.resolve(page(1)) : slow.promise)
  try {
    const reading = f.loadCases(); await flush()
    assert.equal(f.loading.value, false); assert.equal(f.loadingMore.value, true)
    assert.equal(f.rows.value.length, 1)
    f.hooks.stop.forEach(fn => fn()); slow.resolve(page(2)); await reading
    assert.equal(f.loadingMore.value, false); assert.equal(f.rows.value.length, 1)
  } finally { f.cleanup() }
})

test('later preload failure keeps loaded rows and retry resumes from the failed page', async () => {
  let fail = true
  const f = setup(async query => { if (query.page === 2 && fail) throw Error('Offline'); return page(query.page, 3) })
  try {
    assert.equal(await f.loadCases(), false)
    assert.equal(f.loadError.value, true); assert.equal(f.loadingMore.value, false)
    assert.equal(f.rows.value.length, 1); assert.equal(f.pageState.page, 1)
    fail = false; assert.equal(await f.retryCases(), true)
    assert.equal(f.calls.at(-1).page, 2); assert.equal(f.rows.value.length, 2)
    assert.equal(f.loadError.value, false)
  } finally { f.cleanup() }
})

test('first-page failure preserves readable rows and retries from page one', async () => {
  let fail = true
  const f = setup(async query => { if (fail) throw Error('Offline'); return page(query.page, 1) })
  try {
    f.rows.value = [{ id: 99 }]; f.pageState.total = 1
    await f.loadCases(); assert.equal(f.rows.value[0].id, 99); assert.equal(f.loadError.value, true)
    fail = false; await f.retryCases(); assert.equal(f.calls.at(-1).page, 1)
    assert.equal(f.rows.value[0].id, 1); assert.equal(f.loadError.value, false)
  } finally { f.cleanup() }
})

test('drafts added or removed during a read use current state, without resurrection or dropped input', async () => {
  const pending = deferred()
  const f = setup(() => pending.promise)
  try {
    f.rows.value = [{ id: 'draft-old', __draft: true }]
    const reading = f.loadCases()
    f.rows.value = [{ id: 'draft-new', __draft: true, title: 'Unsaved' }]
    pending.resolve(page(1, 1)); await reading
    assert.deepEqual(f.rows.value.map(value => value.id), ['draft-new', 1])
    assert.equal(f.rows.value[0].title, 'Unsaved')
  } finally { f.cleanup() }
})

test('local filter automatically finishes loading all pages and stops on failure until explicit retry', async () => {
  let fail = true
  const f = setup(async query => { if (query.page === 5 && fail) throw Error('Offline'); return page(query.page) })
  try {
    await f.loadCases(); f.handleGridFilterChange({ active: true })
    for (let i = 0; i < 8; ++i) await flush()
    assert.equal(f.rows.value.length, 4); assert.equal(f.loadError.value, true)
    assert.equal(f.loadingAllForFilter.value, false); assert.equal(f.calls.length, 5)
    await flush(); assert.equal(f.calls.length, 5)
    fail = false; await f.retryCases()
    for (let i = 0; i < 8; ++i) await flush()
    assert.equal(f.rows.value.length, 6); assert.equal(f.hasMore.value, false)
    assert.equal(f.loadError.value, false); assert.equal(f.loadingAllForFilter.value, false)
  } finally { f.cleanup() }
})

test('clearing the local filter stops requesting further pages after the current read', async () => {
  const pending = deferred()
  const f = setup(query => query.page === 5 ? pending.promise : Promise.resolve(page(query.page)))
  try {
    await f.loadCases(); f.handleGridFilterChange({ active: true }); await flush()
    assert.equal(f.calls.at(-1).page, 5); f.handleGridFilterChange({ active: false })
    pending.resolve(page(5)); await flush()
    assert.equal(f.calls.at(-1).page, 5); assert.equal(f.rows.value.length, 5)
    assert.equal(f.loadingAllForFilter.value, false)
  } finally { f.cleanup() }
})

test('context change suppresses old success/finally, preserves draft input and collapses synchronous filter changes', async () => {
  const first = deferred(), second = deferred()
  const f = setup(query => query.project_product === 2 ? first.promise : second.promise)
  try {
    f.rows.value = [{ id: 'draft-1', __draft: true }]
    const old = f.loadCases(); f.state.product = 4; f.state.context = 'B'; f.state.context = 'C'
    await flush(); assert.equal(f.calls.length, 2)
    first.resolve(page(1, 1)); await old
    assert.equal(f.loading.value, true); assert.deepEqual(f.rows.value.map(value => value.id), ['draft-1'])
    second.resolve({ data: [{ id: 22 }], totalSize: 1 }); await flush()
    assert.equal(f.loading.value, false); assert.deepEqual(f.rows.value.map(value => value.id), ['draft-1', 22])
  } finally { f.cleanup() }
})

test('identity change clears old formal rows and drafts before loading a new identity', async () => {
  const pending = deferred()
  const f = setup(() => pending.promise)
  try {
    f.rows.value = [{ id: 11 }, { id: 'draft-1', __draft: true }]
    f.state.identity = 'user-B'
    assert.deepEqual([...f.rows.value], []); await flush()
    pending.resolve({ data: [{ id: 22 }], totalSize: 1 }); await flush()
    assert.deepEqual(f.rows.value.map(value => value.id), [22])
  } finally { f.cleanup() }
})

test('KeepAlive deactivation invalidates a request, and activation reads again only once', async () => {
  const first = deferred(), second = deferred(); let calls = 0
  const f = setup(() => ++calls === 1 ? first.promise : second.promise)
  try {
    f.hooks.mount.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await flush()
    assert.equal(calls, 1); f.hooks.stop.forEach(fn => fn())
    first.resolve(page(1, 1)); await flush()
    assert.deepEqual([...f.rows.value], []); assert.equal(f.loading.value, false)
    f.hooks.activate.forEach(fn => fn()); await flush(); assert.equal(calls, 2)
    second.resolve(page(2, 1)); await flush()
    assert.equal(f.rows.value[0].id, 2); assert.equal(f.loading.value, false)
  } finally { f.cleanup() }
})

test('A to B to A context changes still reject an original A response', async () => {
  const original = deferred(), latest = deferred(); let calls = 0
  const f = setup(() => ++calls === 1 ? original.promise : latest.promise)
  try {
    const old = f.loadCases(); f.state.context = 'B'; f.state.context = 'A'; await flush()
    original.resolve(page(1, 1)); await old; assert.equal(f.loading.value, true)
    assert.deepEqual([...f.rows.value], [])
    latest.resolve(page(2, 1)); await flush(); assert.equal(f.rows.value[0].id, 2)
  } finally { f.cleanup() }
})

test('empty or repeated pages with an incomplete total surface retry instead of an endless filter loop', async () => {
  const f = setup(async query => ({ data: query.page === 1 ? [{ id: 1 }, { id: 1 }] : [{ id: 1 }], totalSize: 6 }))
  try {
    await f.loadCases(); assert.equal(f.rows.value.length, 1); assert.equal(f.loadError.value, true)
    f.handleGridFilterChange({ active: true }); await flush()
    assert.equal(f.calls.length, 2); assert.equal(f.loadingAllForFilter.value, false)
  } finally { f.cleanup() }
})

test('saved grid preferences map legacy fields, discard invalid sizes and retain default definitions', () => {
  const f = setup(async query => page(query.page, 1))
  try {
    const { mergeLibraryGridColumns } = f.loadFile('config.ts')
    const defaults = [{ field: 'title', title: 'Title', width: 240 }, { field: 'owner_id', title: 'Owner', width: 120 }, { field: 'project_product_id', title: 'Product', width: 200 }, { field: 'module_id', title: 'Module', width: 220 }]
    const merged = mergeLibraryGridColumns(defaults, { layout_version: 1, columns: [
      { field: 'module_path', width: 300 }, { field: 'owner_name', width: -1 }, { field: 'title', width: 400, visible: false },
      { field: 'owner_id', width: 999 }, { field: 'project_product_path', width: 250 }, { field: 'unknown' }, null,
    ] })
    assert.equal(merged.upgrade, true)
    assert.deepEqual(merged.columns.map(value => value.field), ['owner_id', 'title', 'project_product_id', 'module_id'])
    assert.equal(merged.columns[0].width, 120); assert.equal(merged.columns[1].width, 400)
    assert.equal(merged.columns[1].visible, false); assert.equal(merged.columns[3].width, 300)
    assert.equal(merged.columns[0].title, 'Owner'); assert.equal(defaults[0].visible, undefined)
  } finally { f.cleanup() }
})
