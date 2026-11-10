import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

function setup(write, options = {}) {
  const hooks = { stop: [], activate: [], unmount: [] }, writes = [], refreshed = []
  const rows = [vue.reactive({ id: 1, title: 'Original', module_id: 3, module_path: 'Old/Module', tags: [0] }),
    vue.reactive({ id: 2, title: 'Other' })]
  const context = vue.ref('A'), editable = vue.ref(true)
  const f = harness('CaseEditor', '', {
    base: path.resolve('src/views/functional-test/case-library'),
    api: { putFunctionalPlanCase: async body => { writes.push(body); return write ? write(body, writes.length) : { data: body } } },
    modules: {
      vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      '@/components/table/functional-case-grid': { readGridRecord: row => row },
    },
  })
  const scope = vue.effectScope()
  const state = scope.run(() => f.load('../plan/composables/usePlanCaseSave.ts').usePlanCaseSave({
    context: () => context.value, ownsRow: row => rows.includes(row), editable: () => editable.value,
    columns: () => ['title', 'module_id', 'tags'].map(field => ({ field })).concat({ field: 'id', editable: false }),
    refresh: row => { refreshed.push(row); options.refresh?.(row) },
  }))
  const edit = (changes, row = rows[0], displayChanges = {}) => state.savePlanCase({ row, field: Object.keys(changes)[0], changes, displayChanges, oldValues: {} })
  return { ...state, rows, writes, refreshed, hooks, context, editable, edit,
    close: () => { hooks.unmount.forEach(fn => fn()); scope.stop(); f.close() } }
}

test('owner applies patches synchronously and sends IDs without display paths', async () => {
  const pending = deferred(), f = setup(() => pending.promise)
  try {
    const saving = f.edit({ module_id: 9 }, f.rows[0], { module_path: 'New/Module' })
    assert.equal(f.rows[0].module_id, 9); assert.equal(f.rows[0].module_path, 'New/Module')
    assert.equal(f.caseSaving.value, true); await flush()
    assert.deepEqual(f.writes, [{ id: 1, module_id: 9 }])
    pending.resolve({ data: { id: 1, module_id: 9, module_path: 'Canonical/Module' } }); await saving
    assert.equal(f.rows[0].module_path, 'Canonical/Module'); assert.equal(f.savedOnce.value, true)
    assert.equal(f.caseSaving.value, false)
  } finally { f.close() }
})

test('successive pasted cells serialize and old acknowledgement preserves newer fields', async () => {
  const first = deferred(), f = setup((body, count) => count === 1 ? first.promise : { data: body })
  try {
    const one = f.edit({ title: 'First' }); await flush()
    const two = f.edit({ title: 'Latest' }); assert.equal(f.writes.length, 1)
    first.resolve({ data: { id: 1, title: 'First', tags: [1] } }); await one
    assert.equal(f.rows[0].title, 'Latest'); await two
    assert.equal(f.writes.length, 2); assert.equal(f.rows[0].title, 'Latest')
    assert.deepEqual(f.rows[0].tags, [1]); assert.equal(f.caseSaving.value, false)
  } finally { f.close() }
})

test('failure rolls back newer same-row edits, continues other rows and allows retry', async () => {
  const first = deferred(), f = setup((body, count) => count === 1 ? first.promise : { data: body })
  try {
    const one = f.edit({ title: 'First' }); await flush()
    const two = f.edit({ title: 'Latest' }), other = f.edit({ title: 'Other updated' }, f.rows[1])
    first.reject(Error('Offline')); await Promise.all([one, two, other])
    assert.equal(f.rows[0].title, 'Original'); assert.equal(f.rows[1].title, 'Other updated')
    assert.deepEqual(f.writes.map(body => body.id), [1, 2]); assert.equal(f.saveFailed.value, true)
    await f.edit({ title: 'Retry' }); assert.equal(f.rows[0].title, 'Retry'); assert.equal(f.saveFailed.value, false)
  } finally { f.close() }
})

test('relation failure restores IDs and paths together and snapshots arrays', async () => {
  const first = deferred(), f = setup(() => first.promise)
  try {
    const values = [0, 1], saving = f.edit({ module_id: 9, tags: values }, f.rows[0], { module_path: 'New/Module' })
    values.push(2); await flush(); assert.deepEqual(f.writes[0].tags, [0, 1])
    first.reject(Error('Rejected')); await saving
    assert.equal(f.rows[0].module_id, 3); assert.equal(f.rows[0].module_path, 'Old/Module'); assert.deepEqual(f.rows[0].tags, [0])
  } finally { f.close() }
})

for (const mode of ['context', 'deactivate', 'readonly']) {
  test(`${mode} invalidates old writes while keeping the physical request serialized`, async () => {
    const first = deferred(), f = setup((body, count) => count === 1 ? first.promise : { data: body })
    try {
      const old = f.edit({ title: 'Old request' }); await flush()
      if (mode === 'context') f.context.value = 'B'
      if (mode === 'deactivate') { f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()) }
      if (mode === 'readonly') { f.editable.value = false; f.editable.value = true }
      assert.equal(f.rows[0].title, 'Original')
      const fresh = f.edit({ title: 'Fresh' }); await flush(); assert.equal(f.writes.length, 1)
      first.resolve({ data: { id: 1, title: 'Stale', tags: [99] } }); await Promise.all([old, fresh])
      assert.equal(f.writes.length, 2); assert.equal(f.rows[0].title, 'Fresh'); assert.deepEqual(f.rows[0].tags, [0])
    } finally { f.close() }
  })
}

test('alien rows, readonly fields and unmatched display patches do not mutate or write', async () => {
  const f = setup()
  try {
    const alien = { id: 1, title: 'Alien' }
    await f.edit({ title: 'No' }, alien); await f.edit({ id: 5 }); await f.edit({ title: 'No' }, f.rows[0], { module_path: 'No' })
    f.editable.value = false; await f.edit({ title: 'No' })
    assert.equal(alien.title, 'Alien'); assert.equal(f.rows[0].title, 'Original'); assert.deepEqual(f.writes, [])
  } finally { f.close() }
})

test('wrong-row acknowledgement fails and rendering errors cannot reject an accepted save', async () => {
  const f = setup((body, count) => ({ data: count === 1 ? { id: 999, title: 'Wrong' } : body }), { refresh: () => { throw Error('Canvas disposed') } })
  try {
    await f.edit({ title: 'Rejected' }); assert.equal(f.rows[0].title, 'Original'); assert.equal(f.saveFailed.value, true)
    await f.edit({ title: 'Accepted' }); assert.equal(f.rows[0].title, 'Accepted'); assert.equal(f.saveFailed.value, false)
  } finally { f.close() }
})
