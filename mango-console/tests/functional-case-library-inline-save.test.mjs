import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/case-library')
const row = (id = 11) => ({ id, version_no: 1, update_time: 'old', title: 'Original', case_no: `CASE-${id}`,
  project_product_id: 2, project_product_path: 'Example/Product', module_id: 3, module_path: 'First/Second/Third',
  owner_id: 4, test_types: [0], scenario_tags: ['routine_regression'],
})
const ack = (value, overrides = {}) => ({ id: value.id, version_no: Number(value.version_no) + 1, update_time: 'updated',
  project_product_id: value.changes.project_product_id ?? 2, project_product_path: 'Example/Product',
  module_id: value.changes.module_id ?? 3, module_path: `Module/${value.changes.module_id ?? 3}`, ...overrides,
})
function setup(api = {}, extra = {}) {
  const hooks = { activate: [], stop: [], unmount: [] }, refreshed = [], messages = []
  const f = harness('CaseEditor', '', { base,
    props: { users: [], contextKey: 'context-1', defaults: { projectProduct: 2, module: 3 } },
    api: { putManualCaseBatch: async ({ updates }) => ({ data: { updated: updates.map(value => ack(value)), conflicts: [] } }), ...api },
    modules: {
      vue: { ...vue, onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.stop.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      '@arco-design/web-vue': { Message: { error: value => messages.push(value), warning: value => messages.push(value), success() {} } },
    },
  })
  const rows = [row()]
  const scope = vue.effectScope()
  const state = scope.run(() => f.load('composables/useCaseInlineSave.ts').useCaseInlineSave({
    context: () => f.props.contextKey, ownsRow: value => rows.includes(value),
    refreshCells: (...args) => refreshed.push(args), reload: extra.reload ?? (async () => {}),
  }))
  return { ...state, rows, hooks, refreshed, messages, props: f.props, cleanup: () => { hooks.unmount.forEach(fn => fn()); scope.stop(); f.close() } }
}
function edit(f, field, value, target = f.rows[0]) {
  f.saveInline({ row: target, field, changes: { [field]: value }, displayChanges: {}, oldValues: { [field]: target[field] } })
}

test('450ms debounce coalesces latest cells with one versioned request', async () => {
  const writes = []
  const f = setup({ putManualCaseBatch: async body => { writes.push(body); return { data: { updated: body.updates.map(value => ack(value)) } } } })
  try {
    edit(f, 'title', 'First'); edit(f, 'title', 'Latest'); edit(f, 'case_no', 'CASE-NEW')
    assert.equal(writes.length, 0); assert.equal(f.pendingInlineCellCount.value, 2)
    await new Promise(resolve => setTimeout(resolve, 490))
    assert.equal(writes.length, 1)
    assert.deepEqual(writes[0], { updates: [{ id: 11, version_no: 1, changes: { title: 'Latest', case_no: 'CASE-NEW' } }] })
    assert.equal(f.rows[0].version_no, 2); assert.equal(f.inlineSavingCount.value, 0)
    assert.equal(f.inlineSaveState.value, 'saved')
  } finally { f.cleanup() }
})

test('edits during an in-flight request drain serially using the acknowledged version', async () => {
  const first = deferred(), writes = []
  const f = setup({ putManualCaseBatch: async body => { writes.push(body); return writes.length === 1 ? first.promise : { data: { updated: body.updates.map(value => ack(value)) } } } })
  try {
    edit(f, 'title', 'First'); const saving = f.flushInlineUpdates()
    edit(f, 'title', 'Second'); const waiting = f.flushInlineUpdates()
    assert.equal(writes.length, 1); assert.equal(f.inflightInlineCellCount.value, 1)
    first.resolve({ data: { updated: [ack(writes[0].updates[0])] } })
    assert.equal(await saving, true); assert.equal(await waiting, true)
    assert.equal(writes.length, 2); assert.equal(writes[1].updates[0].version_no, 2)
    assert.equal(writes[1].updates[0].changes.title, 'Second'); assert.equal(f.rows[0].version_no, 3)
    assert.equal(f.inlineSavingCount.value, 0)
  } finally { f.cleanup() }
})

test('an old relation acknowledgement cannot overwrite a newer queued module or path', async () => {
  const first = deferred(), second = deferred(), writes = []
  const f = setup({ putManualCaseBatch: body => { writes.push(body); return writes.length === 1 ? first.promise : second.promise } })
  try {
    edit(f, 'module_id', 5); f.rows[0].module_path = 'Module/5'
    const saving = f.flushInlineUpdates()
    edit(f, 'module_id', 6); f.rows[0].module_path = 'Module/6'
    first.resolve({ data: { updated: [ack(writes[0].updates[0])] } }); await flush()
    assert.equal(f.rows[0].module_id, 6); assert.equal(f.rows[0].module_path, 'Module/6')
    assert.equal(writes.length, 2); assert.equal(writes[1].updates[0].version_no, 2)
    second.resolve({ data: { updated: [ack(writes[1].updates[0])] } }); await saving
    assert.equal(f.rows[0].version_no, 3); assert.equal(f.rows[0].module_id, 6)
  } finally { f.cleanup() }
})

test('queued and submitted enum arrays are copied instead of sharing mutable cell arrays', async () => {
  const pending = deferred(), writes = []
  const f = setup({ putManualCaseBatch: body => { writes.push(body); return pending.promise } })
  try {
    const values = [0, 1]; edit(f, 'test_types', values); values.push(2)
    const saving = f.flushInlineUpdates(); f.rows[0].test_types.push(3)
    assert.deepEqual(writes[0].updates[0].changes.test_types, [0, 1])
    pending.resolve({ data: { updated: [ack(writes[0].updates[0])] } }); await saving
  } finally { f.cleanup() }
})

test('failed request rolls back both the in-flight batch and later queued edits; a new edit can retry', async () => {
  const pending = deferred(); let calls = 0, reloads = 0
  const f = setup({ putManualCaseBatch: async body => { ++calls; return calls === 1 ? pending.promise : { data: { updated: body.updates.map(value => ack(value)) } } } }, { reload: async () => { ++reloads } })
  try {
    edit(f, 'title', 'First'); const saving = f.flushInlineUpdates()
    edit(f, 'title', 'Second'); edit(f, 'case_no', 'NEW')
    pending.reject(Error('Rejected')); assert.equal(await saving, false)
    assert.equal(f.rows[0].title, 'Original'); assert.equal(f.rows[0].case_no, 'CASE-11')
    assert.equal(f.inlineSaveState.value, 'error'); assert.equal(f.inlineSavingCount.value, 0)
    assert.equal(reloads, 1); edit(f, 'title', 'Retried'); await f.flushInlineUpdates()
    assert.equal(calls, 2); assert.equal(f.inlineSaveState.value, 'saved')
  } finally { f.cleanup() }
})

test('relation failure restores IDs and display paths even if reloading also fails', async () => {
  const f = setup({ putManualCaseBatch: async () => { throw Error('Rejected') } }, { reload: async () => { throw Error('Offline') } })
  try {
    const target = f.rows[0]
    f.saveInline({ row: target, field: 'module_id', changes: { project_product_id: 8, module_id: 9 }, displayChanges: { project_product_path: 'New/Product', module_path: 'New/Module' }, oldValues: { project_product_id: 2, module_id: 3, project_product_path: 'Example/Product', module_path: 'First/Second/Third' } })
    assert.equal(await f.flushInlineUpdates(), false)
    assert.equal(target.project_product_id, 2); assert.equal(target.module_id, 3)
    assert.equal(target.project_product_path, 'Example/Product'); assert.equal(target.module_path, 'First/Second/Third')
    assert.equal(f.inlineSaveState.value, 'error'); assert.equal(f.inlineSavingCount.value, 0)
  } finally { f.cleanup() }
})

test('version conflict clears queued writes and refreshes without resubmitting old edits', async () => {
  let calls = 0, reloads = 0
  const f = setup({ putManualCaseBatch: async () => { ++calls; return { data: { conflicts: [{ id: 11, expected_version: 1, current_version: 2 }] } } } }, { reload: async () => { ++reloads } })
  try {
    edit(f, 'title', 'Conflict'); assert.equal(await f.flushInlineUpdates(), false)
    assert.equal(f.rows[0].title, 'Original'); assert.equal(f.inlineSaveState.value, 'conflict')
    assert.equal(f.inlineSavingCount.value, 0); assert.equal(reloads, 1)
    assert.equal(await f.flushInlineUpdates(), false); assert.equal(calls, 1)
  } finally { f.cleanup() }
})

test('recovery blocks new cell writes until the replacement list finishes loading', async () => {
  const pending = deferred(); let calls = 0
  const f = setup({ putManualCaseBatch: async () => { ++calls; throw Error('Rejected') } }, { reload: () => pending.promise })
  try {
    edit(f, 'title', 'Rejected'); const saving = f.flushInlineUpdates(); await flush()
    assert.equal(f.inlineRecovering.value, true); assert.equal(f.rows[0].title, 'Original')
    edit(f, 'title', 'During recovery')
    assert.equal(f.rows[0].title, 'Original'); assert.equal(f.pendingInlineCellCount.value, 0)
    assert.equal(calls, 1); pending.resolve(); await saving
    assert.equal(f.inlineRecovering.value, false); assert.equal(f.inlineSaveState.value, 'error')
  } finally { f.cleanup() }
})

for (const kind of ['missing row', 'stale version', 'relation mismatch']) {
  test(`${kind} acknowledgement fails before applying any row metadata`, async () => {
    let reloads = 0
    const f = setup({ putManualCaseBatch: async body => ({ data: { updated: body.updates.flatMap((value, index) => {
      if (index === 1 && kind === 'missing row') return []
      return [ack(value, index === 1 ? kind === 'stale version' ? { version_no: 1 } : { module_id: 999 } : {})]
    }) } }) }, { reload: async () => { ++reloads } })
    try {
      f.rows.push(row(12)); edit(f, 'title', 'First', f.rows[0]); edit(f, 'module_id', 6, f.rows[1])
      assert.equal(await f.flushInlineUpdates(), false)
      assert.equal(f.rows[0].version_no, 1); assert.equal(f.rows[1].version_no, 1)
      assert.equal(f.rows[0].title, 'Original'); assert.equal(f.rows[1].module_id, 3)
      assert.equal(reloads, 1); assert.equal(f.inlineSaveState.value, 'error')
    } finally { f.cleanup() }
  })
}

test('scope change suppresses old success/finally and serializes a new scope write behind the physical request', async () => {
  const first = deferred(), second = deferred(), writes = []
  const f = setup({ putManualCaseBatch: body => { writes.push(body); return writes.length === 1 ? first.promise : second.promise } })
  try {
    const oldRow = f.rows[0]; edit(f, 'title', 'Old scope'); const old = f.flushInlineUpdates()
    f.props.contextKey = 'new-role'; f.rows.splice(0, 1, row(22)); edit(f, 'title', 'New scope')
    const fresh = f.flushInlineUpdates(); assert.equal(writes.length, 1)
    first.resolve({ data: { updated: [ack(writes[0].updates[0])] } }); await old; await flush()
    assert.equal(oldRow.version_no, 1); assert.equal(writes.length, 2)
    assert.equal(writes[1].updates[0].id, 22); assert.equal(f.inflightInlineCellCount.value, 1)
    second.resolve({ data: { updated: [ack(writes[1].updates[0])] } }); await fresh
    assert.equal(f.rows[0].version_no, 2); assert.equal(f.inlineSavingCount.value, 0)
  } finally { f.cleanup() }
})

test('old failure after scope change cannot roll back new rows or trigger an old reload', async () => {
  const pending = deferred(); let reloads = 0
  const f = setup({ putManualCaseBatch: () => pending.promise }, { reload: async () => { ++reloads } })
  try {
    edit(f, 'title', 'Old'); const saving = f.flushInlineUpdates()
    f.props.contextKey = 'new-environment'; f.rows.splice(0, 1, row(22))
    pending.reject(Error('Late failure')); await saving
    assert.equal(f.rows[0].title, 'Original'); assert.equal(reloads, 0)
    assert.equal(f.inlineSaveState.value, 'saved'); assert.deepEqual(f.messages, [])
  } finally { f.cleanup() }
})

test('deactivation cancels queued debounce; activation permits fresh edits', async () => {
  let calls = 0
  const f = setup({ putManualCaseBatch: async body => { ++calls; return { data: { updated: body.updates.map(value => ack(value)) } } } })
  try {
    edit(f, 'title', 'Unsaved'); f.hooks.stop.forEach(fn => fn())
    assert.equal(f.rows[0].title, 'Original'); assert.equal(await f.flushInlineUpdates(), false)
    assert.equal(calls, 0); f.hooks.activate.forEach(fn => fn())
    edit(f, 'title', 'Resumed'); await f.flushInlineUpdates(); assert.equal(calls, 1)
  } finally { f.cleanup() }
})

test('draft edits only mark touched; readonly/unknown cells never enter the write protocol', async () => {
  let calls = 0
  const f = setup({ putManualCaseBatch: async () => { ++calls } })
  try {
    const draft = { ...row(), id: 'draft-1', __draft: true }; f.rows.push(draft)
    edit(f, 'title', 'Draft', draft); assert.equal(draft.__touched, true)
    f.saveInline({ row: f.rows[0], field: 'version_no', changes: { version_no: 99 } })
    f.saveInline({ row: f.rows[0], field: 'title', changes: { title: { invalid: true }, unknown: 'forbidden' } })
    await f.flushInlineUpdates(); assert.equal(calls, 0)
    assert.equal(f.inlineSavingCount.value, 0)
  } finally { f.cleanup() }
})

test('queued rows removed from the current list are not submitted later', async () => {
  let calls = 0
  const f = setup({ putManualCaseBatch: async () => { ++calls } })
  try {
    edit(f, 'title', 'Removed'); f.rows.splice(0)
    await f.flushInlineUpdates(); assert.equal(calls, 0); assert.equal(f.inlineSavingCount.value, 0)
  } finally { f.cleanup() }
})

test('an acknowledged version older than a currently displayed row never downgrades it', async () => {
  const pending = deferred()
  const f = setup({ putManualCaseBatch: () => pending.promise })
  try {
    edit(f, 'title', 'First'); const saving = f.flushInlineUpdates()
    f.rows[0].version_no = 3; f.rows[0].update_time = 'newer'
    pending.resolve({ data: { updated: [ack({ id: 11, version_no: 1, changes: {} })] } }); await saving
    assert.equal(f.rows[0].version_no, 3); assert.equal(f.rows[0].update_time, 'newer')
  } finally { f.cleanup() }
})
