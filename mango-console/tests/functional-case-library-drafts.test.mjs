import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/case-library')
const defaults = { productId: 2, productPath: 'Project/Product', moduleId: 3, modulePath: 'Parent/Child', ownerId: 1, ownerName: 'Example' }
const record = id => ({ id, version_no: 1, case_no: `CASE-${id}`, title: 'Example', test_point: 'Scene', priority: 0,
  test_types: [0], test_steps: [{ action: 'Act', expected: 'OK' }], story_refs: ['STORY-1'], scenario_tags: ['routine_regression'],
  project_product: { id: 2, name: 'Product', project: { name: 'Project' } }, module: { id: 3, name: 'Child', full_path: 'Parent/Child' }, owner: { id: 1, name: 'Example' }, status: 0 })
function setup(options = {}) {
  const hooks = { stop: [], activate: [], unmount: [] }, dialogs = [], writes = [], deletes = [], messages = []
  const rows = vue.ref([]), selection = vue.ref([])
  const state = vue.reactive({ context: 'A', identity: 'user-A', available: true, blocked: false })
  let count = 0, editing = 0
  const f = harness('CaseEditor', '', { base,
    modules: {
      vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      '@arco-design/web-vue': {
        Message: Object.fromEntries(['success', 'warning', 'error'].map(key => [key, message => messages.push([key, message])])),
        Modal: { confirm: config => {
          const handle = { config, closed: false, close() { this.closed = true; config.onClose?.() } }
          dialogs.push(handle); return handle
        } },
      },
    }, api: {
      postManualCaseBatch: async body => { writes.push(body); return options.write ? options.write(body, writes.length) : { data: body.items.map((_, i) => record(100 + i)) } },
      deleteManualCase: async ids => { deletes.push([...ids]); return options.remove ? options.remove(ids, deletes.length) : {} },
    },
  })
  const mapping = f.load('rows.ts'), scope = vue.effectScope()
  const drafts = scope.run(() => f.load('composables/useCaseDrafts.ts').useCaseDrafts({
    rows, selection, context: () => JSON.stringify([state.context, state.identity]), identity: () => state.identity,
    available: () => state.available, blocked: () => state.blocked, defaults: () => defaults,
    enableEditing: () => { ++editing }, flush: options.flush ?? (async () => true), countChange: delta => { count += delta },
  }))
  function filled() {
    drafts.insertDraftRows({ index: 0, count: 1 })
    const draft = rows.value[0]
    Object.assign(draft, { case_no: 'DRAFT', title: 'Title', test_point: 'Scene', __touched: true })
    return draft
  }
  return { ...drafts, rows, selection, state, hooks, dialogs, writes, deletes, messages, mapping, filled,
    persisted: id => mapping.normalizeLibraryCaseRow(record(id)), count: () => count, editing: () => editing,
    cleanup: () => { hooks.unmount.forEach(fn => fn()); scope.stop(); f.close() },
  }
}

test('row normalization whitelists fields, preserves zero enums and canonical module paths', () => {
  const f = setup()
  try {
    const source = { ...record(1), priority: 0, project_product_id: 8, module_id: 9, owner_id: 10, hidden: 'excluded' }
    const row = f.mapping.normalizeLibraryCaseRow(source)
    assert.equal(row.priority, 0); assert.equal(row.status, 0); assert.equal(row.project_product_id, 8)
    assert.equal(row.module_id, 9); assert.equal(row.owner_id, 10); assert.equal(row.module_path, 'Parent/Child')
    assert.equal('hidden' in row, false); assert.equal(row.__draft, false)
    row.test_steps[0].action = 'Changed'; row.story_refs.push('STORY-2')
    assert.equal(source.test_steps[0].action, 'Act'); assert.deepEqual(source.story_refs, ['STORY-1'])
    assert.throws(() => f.mapping.normalizeLibraryCaseRow({ id: 1 }), /版本缺失/)
    assert.throws(() => f.mapping.normalizeLibraryCaseRow({ ...record(1), test_types: {} }), /多值字段/)
  } finally { f.cleanup() }
})

test('start and insertion own fresh drafts, navigation defaults and editing activation', () => {
  const f = setup()
  try {
    f.startBatchCreate(); assert.equal(f.rows.value.length, 20); assert.equal(f.batchMode.value, true); assert.equal(f.editing(), 1)
    const first = f.rows.value[0], second = f.rows.value[1]
    assert.equal(first.project_product_id, 2); assert.equal(first.module_id, 3); assert.equal(first.owner_id, 1)
    first.test_types.push(1); assert.deepEqual(second.test_types, [0]); assert.equal(new Set(f.rows.value.map(row => row.id)).size, 20)
    f.startBatchCreate(); assert.equal(f.rows.value.length, 20)
    f.insertDraftRows({ index: 1, count: 2.9 }); assert.equal(f.rows.value.length, 22)
  } finally { f.cleanup() }
})

test('copying selected drafts isolates all arrays and steps and does not copy formal cases', () => {
  const f = setup()
  try {
    const source = f.filled()
    source.test_steps = [{ action: 'Act', expected: 'OK' }]; source.story_refs = ['STORY-1']
    const persisted = f.persisted(1); f.rows.value.push(persisted); f.selection.value = [source, persisted]
    f.copyDraftRows(); const copy = f.rows.value[0]
    assert.equal(copy.case_no, 'DRAFT-COPY'); assert.notEqual(copy.id, source.id); assert.equal(copy.__draft, true)
    copy.test_types.push(1); copy.scenario_tags.push('inspection'); copy.story_refs.push('STORY-2'); copy.test_steps[0].action = 'Changed'
    assert.deepEqual(source.test_types, [0]); assert.deepEqual(source.scenario_tags, ['routine_regression'])
    assert.deepEqual(source.story_refs, ['STORY-1']); assert.equal(source.test_steps[0].action, 'Act'); assert.equal(f.rows.value.length, 3)
    assert.deepEqual([...f.selection.value], [])
  } finally { f.cleanup() }
})

test('draft payload is a detached whitelist and keeps legal zero values', () => {
  const f = setup()
  try {
    const draft = f.filled(); draft.priority = 0; draft.status = 0; draft.test_steps = [{ action: 'Act', expected: 'OK' }]
    const payload = f.mapping.libraryDraftPayload(draft)
    draft.test_types.push(1); draft.test_steps[0].action = 'Changed'
    assert.deepEqual(payload.test_types, [0]); assert.equal(payload.test_steps[0].action, 'Act')
    assert.equal(payload.priority, 0); assert.equal(payload.status, 0)
    for (const key of ['id', 'version_no', '__draft', 'owner_name', 'module_path', 'bindings']) assert.equal(key in payload, false)
  } finally { f.cleanup() }
})

test('empty and incomplete drafts do not issue batch requests and stay editable', async () => {
  const f = setup()
  try {
    f.startBatchCreate(); await f.saveDraftRows(); assert.equal(f.writes.length, 0)
    f.rows.value[0].title = 'Partial'; await f.saveDraftRows(); assert.equal(f.writes.length, 0)
    assert.equal(f.batchSaving.value, false); assert.equal(f.rows.value.length, 20)
  } finally { f.cleanup() }
})

test('batch save snapshots input, prevents duplicate writes and preserves unsubmitted drafts', async () => {
  const pending = deferred(), f = setup({ write: () => pending.promise })
  try {
    const submitted = f.filled(); f.insertDraftRows({ index: 1, count: 1 }); const blank = f.rows.value[1]
    const saving = f.saveDraftRows(); await flush(); await f.saveDraftRows()
    f.copyDraftRows(); f.insertDraftRows({ index: 0, count: 10 })
    assert.equal(f.writes.length, 1); assert.equal(f.batchSaving.value, true); assert.equal(f.rows.value.length, 2)
    submitted.title = 'Later input'; submitted.test_types.push(1)
    assert.equal(f.writes[0].items[0].title, 'Title'); assert.deepEqual(f.writes[0].items[0].test_types, [0])
    pending.resolve({ data: [record(100)] }); await saving
    assert.equal(f.rows.value.some(row => row.id === submitted.id), false); assert.equal(f.rows.value.some(row => row.id === blank.id), true)
    assert.equal(f.rows.value[0].id, 100); assert.equal(f.count(), 1); assert.equal(f.batchMode.value, true); assert.equal(f.batchSaving.value, false)
  } finally { f.cleanup() }
})

test('batch failure retains drafts and retry can succeed without losing their values', async () => {
  const f = setup({ write: async (_, n) => { if (n === 1) throw Error('Rejected'); return { data: [record(100)] } } })
  try {
    const draft = f.filled(); await f.saveDraftRows()
    assert.equal(f.rows.value[0].id, draft.id); assert.equal(f.batchSaving.value, false); assert.equal(f.batchMode.value, true)
    await f.saveDraftRows(); assert.equal(f.rows.value[0].id, 100); assert.equal(f.batchMode.value, false)
  } finally { f.cleanup() }
})

test('partial or malformed batch acknowledgement never discards submitted drafts or reports success', async () => {
  for (const data of [[], [{ id: 100 }], [record(100), record(100)]]) {
    const f = setup({ write: async () => ({ data }) })
    try {
      const draft = f.filled(); if (data.length === 2) f.filled()
      await f.saveDraftRows(); assert.equal(f.rows.value.some(row => row.id === draft.id), true)
      assert.equal(f.count(), 0); assert.equal(f.messages.some(([kind]) => kind === 'success'), false)
    } finally { f.cleanup() }
  }
})

test('inline save rejection prevents batch creation and releases loading', async () => {
  const f = setup({ flush: async () => false })
  try {
    f.filled(); await f.saveDraftRows(); assert.equal(f.writes.length, 0); assert.equal(f.batchSaving.value, false)
  } finally { f.cleanup() }
})

test('context changes during the pre-save wait prevent a batch request', async () => {
  const pending = deferred(), f = setup({ flush: () => pending.promise })
  try {
    f.filled(); const saving = f.saveDraftRows(); f.state.context = 'B'
    pending.resolve(true); await saving
    assert.equal(f.writes.length, 0); assert.equal(f.batchSaving.value, false); assert.equal(f.rows.value.length, 1)
  } finally { f.cleanup() }
})

test('an acknowledged row already returned by a concurrent list read is not duplicated or counted twice', async () => {
  const pending = deferred(), f = setup({ write: () => pending.promise })
  try {
    f.filled(); const saving = f.saveDraftRows(); await flush()
    f.rows.value.push(f.persisted(100))
    pending.resolve({ data: [record(100)] }); await saving
    assert.deepEqual(f.rows.value.map(row => row.id), [100]); assert.equal(f.count(), 0)
  } finally { f.cleanup() }
})

test('identity A to B to A rejects a late batch response without releasing its physical mutex early', async () => {
  const pending = deferred(), f = setup({ write: () => pending.promise })
  try {
    f.filled(); const saving = f.saveDraftRows(); await flush()
    f.state.identity = 'user-B'; f.state.identity = 'user-A'
    f.rows.value = [f.persisted(9)]; await f.saveDraftRows()
    assert.equal(f.writes.length, 1); assert.equal(f.batchSaving.value, true)
    pending.resolve({ data: [record(100)] }); await saving
    assert.equal(f.rows.value[0].id, 9); assert.equal(f.count(), 0); assert.equal(f.batchSaving.value, false)
    assert.equal(f.messages.some(([kind]) => kind === 'success'), false)
  } finally { f.cleanup() }
})

test('delete confirmation captures targets and cancellation preserves both mixed draft and formal rows', () => {
  const f = setup()
  try {
    const draft = f.filled(), persisted = f.persisted(1); f.rows.value.push(persisted)
    f.removeGridRows([draft, persisted]); assert.equal(f.rows.value.length, 2); assert.equal(f.dialogs.length, 1)
    assert.equal(f.dialogs[0].config.okButtonProps.status, 'danger'); f.dialogs[0].close()
    assert.equal(f.rows.value.length, 2); assert.equal(f.deletes.length, 0)
    f.removeGridRows([draft]); assert.equal(f.rows.value.length, 1); assert.equal(f.batchMode.value, false)
  } finally { f.cleanup() }
})

test('delete uses awaited confirmation, prevents repeat calls and closes only after success', async () => {
  const pending = deferred(), f = setup({ remove: () => pending.promise })
  try {
    const first = f.persisted(1), second = f.persisted(2); f.rows.value = [first, second]; f.selection.value = [first]
    f.removeGridRows([]); const dialog = f.dialogs[0], deleting = dialog.config.onBeforeOk(); await flush()
    f.selection.value = [second]; await dialog.config.onBeforeOk(); f.removeGridRows([second])
    assert.equal(f.deleting.value, true); assert.deepEqual(f.deletes, [[1]]); assert.equal(dialog.closed, false)
    assert.equal(dialog.config.onBeforeCancel(), false)
    pending.resolve({}); assert.equal(await deleting, false)
    assert.equal(dialog.closed, true); assert.equal(f.deleting.value, false); assert.deepEqual(f.rows.value.map(row => row.id), [2]); assert.equal(f.count(), -1)
  } finally { f.cleanup() }
})

test('delete failure leaves the same confirmation open and restores retry', async () => {
  const f = setup({ remove: async (_, n) => { if (n === 1) throw Error('Rejected'); return {} } })
  try {
    f.rows.value = [f.persisted(1)]; f.removeGridRows([...f.rows.value]); const dialog = f.dialogs[0]
    await dialog.config.onBeforeOk(); assert.equal(dialog.closed, false); assert.equal(f.rows.value.length, 1); assert.equal(f.deleting.value, false)
    await dialog.config.onBeforeOk(); assert.equal(dialog.closed, true); assert.equal(f.rows.value.length, 0); assert.equal(f.deletes.length, 2)
  } finally { f.cleanup() }
})

test('context change while awaiting inline save cancels deletion before its API call', async () => {
  const pending = deferred(), f = setup({ flush: () => pending.promise })
  try {
    f.rows.value = [f.persisted(1)]; f.removeGridRows([...f.rows.value]); const dialog = f.dialogs[0]
    const deleting = dialog.config.onBeforeOk(); f.state.context = 'B'
    assert.equal(dialog.closed, true); pending.resolve(true); await deleting
    assert.equal(f.deletes.length, 0); assert.equal(f.rows.value.length, 1); assert.equal(f.deleting.value, false)
  } finally { f.cleanup() }
})

test('deactivation closes confirmation and late delete success does not remove new-context data', async () => {
  const pending = deferred(), f = setup({ remove: () => pending.promise })
  try {
    f.rows.value = [f.persisted(1)]; f.removeGridRows([...f.rows.value]); const dialog = f.dialogs[0]
    const deleting = dialog.config.onBeforeOk(); await flush()
    f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); f.rows.value = [f.persisted(1)]
    f.removeGridRows([...f.rows.value]); assert.equal(f.dialogs.length, 1); assert.equal(f.deleting.value, true)
    pending.resolve({}); await deleting
    assert.equal(dialog.closed, true); assert.equal(f.rows.value.length, 1); assert.equal(f.count(), 0)
    assert.equal(f.messages.some(([kind]) => kind === 'success'), false)
  } finally { f.cleanup() }
})

test('exit confirmation removes only its draft snapshot and invalidated callbacks cannot remove rows', async () => {
  const f = setup()
  try {
    f.filled(); f.exitBatchCreate(); const dialog = f.dialogs[0]
    f.insertDraftRows({ index: 0, count: 1 }); const later = f.rows.value[0]
    await dialog.config.onBeforeOk(); assert.deepEqual(f.rows.value.map(row => row.id), [later.id]); assert.equal(f.batchMode.value, true)
    f.exitBatchCreate(); const stale = f.dialogs[1]; f.state.context = 'B'
    await stale.config.onBeforeOk(); assert.equal(f.rows.value.length, 1); assert.equal(stale.closed, true)
  } finally { f.cleanup() }
})

test('actual page coordinates canonical navigation defaults, draft edits and acknowledged creation', async () => {
  const previous = globalThis.window
  globalThis.window = { setTimeout, clearTimeout }
  const hooks = [], writes = []
  const route = vue.reactive({ path: '/functional-test/case/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 1, userName: 'Example' })
  const f = harness('index', 'rows,selectedRows,navigationCreateRef,startBatchCreate,saveDraftRows,saveInline,batchMode,pageState,selectedPersistedRows,editor,openEditor', { base,
    api: { postManualCaseBatch: async body => { writes.push(body); return { data: [record(100)] } } },
    modules: {
      vue: { ...vue, onMounted: () => {}, onActivated: () => {}, onDeactivated: fn => hooks.push(fn), onBeforeUnmount: fn => hooks.push(fn) },
      'vue-router': { useRoute: () => route, useRouter: () => ({ push() {} }), onBeforeRouteLeave() {} },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ getEnum: async () => {} }) },
      xlsx: {},
    },
  })
  try {
    f.navigationCreateRef.value = { getCreateDefaults: () => ({ projectProduct: 2, module: 3 }) }
    f.startBatchCreate(); const draft = f.rows.value[0]
    Object.assign(draft, { case_no: 'DRAFT', title: 'Title', test_point: 'Scene' })
    f.saveInline({ row: draft, field: 'title', changes: { title: 'Title' }, displayChanges: {}, oldValues: { title: '' } })
    assert.equal(draft.__touched, true); assert.equal(draft.project_product_id, 2); assert.equal(draft.module_id, 3)
    await f.saveDraftRows()
    assert.equal(writes.length, 1); assert.equal(writes[0].items.length, 1)
    assert.equal(f.rows.value.length, 20); assert.equal(f.pageState.total, 1); assert.equal(f.batchMode.value, true)
    const persisted = f.rows.value.find(row => !row.__draft); f.selectedRows.value = [persisted]
    assert.equal(f.selectedPersistedRows.value.length, 1)
    let opened
    f.editor.value = { open: async row => { opened = row } }; await f.openEditor(persisted)
    assert.equal(opened.module_id, 3); assert.equal(opened.version_no, 1)
  } finally { hooks.forEach(fn => fn()); f.close(); globalThis.window = previous }
})
