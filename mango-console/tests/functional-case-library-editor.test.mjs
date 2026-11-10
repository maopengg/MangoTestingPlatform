import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { compileScript, compileStyle, compileTemplate, parse } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/case-library')
const record = (overrides = {}) => ({
  id: 11, version_no: 7, case_no: 'CASE-11', title: 'Example case', test_point: 'Example point',
  project_product: { id: 2 }, module: { id: 3 }, owner: { id: 4 }, priority: 0, status: 0,
  test_types: [0], story_refs: ['STORY-1'], scenario_tags: ['routine_regression'],
  test_steps: [{ action: 'Example action', expected: 'Example result' }], ...overrides,
})
function setup(overrides = {}) {
  return harness('CaseEditor', 'open, form, visible, saving, saveError, saveCase, canCancel, invalidate, categoryOptions, categoryLoading, categoryError, loadCategoryOptions', {
    base, props: { users: [], contextKey: 'context-1', defaults: { projectProduct: 2, module: 3 } },
    ...overrides,
  })
}

test('form factory isolates arrays/steps, preserves zero and excludes row metadata', async () => {
  const f = setup()
  try {
    const { createLibraryCaseForm, libraryCasePayload } = f.load('form.ts')
    const source = record({ update_time: 'old', owner_name: 'Display', bindings: [1] })
    const form = createLibraryCaseForm(source)
    form.test_types.push(1); form.story_refs.push('STORY-2'); form.scenario_tags.push('other')
    form.test_steps[0].action = 'Changed'
    assert.deepEqual(source.test_types, [0]); assert.deepEqual(source.story_refs, ['STORY-1'])
    assert.equal(source.test_steps[0].action, 'Example action')
    form.project_product = [1, 2]
    form.test_steps.push({ action: '', expected: '' })
    const payload = libraryCasePayload({ ...form, update_time: 'leak', project_product_id: 999, module_id: 999, owner_id: 999 })
    assert.equal(payload.priority, 0); assert.equal(payload.status, 0)
    assert.equal(payload.project_product, 2); assert.equal(payload.owner, 4); assert.equal(payload.module, 3)
    assert.equal(payload.version_no, 7); assert.equal(payload.id, 11)
    assert.equal(payload.test_steps.length, 1)
    for (const key of ['owner_name', 'update_time', 'bindings', 'project_product_id']) assert.equal(key in payload, false)
    const fresh = libraryCasePayload(createLibraryCaseForm())
    assert.equal('id' in fresh, false); assert.equal('version_no' in fresh, false)
    const another = createLibraryCaseForm(); another.test_types.push(9)
    assert.deepEqual(createLibraryCaseForm().test_types, [0])
  } finally { f.close() }
})

test('cancel and reopen discard edits without changing the source record', async () => {
  const f = setup()
  try {
    const source = record()
    await f.open(source)
    f.form.test_steps[0].action = 'Unsaved'; f.form.story_refs.push('Unsaved')
    f.invalidate(); await f.open(source)
    assert.equal(f.form.test_steps[0].action, 'Example action')
    assert.deepEqual([...f.form.story_refs], ['STORY-1'])
    f.invalidate(); await f.open()
    assert.equal(f.form.id, null); assert.equal(f.form.version_no, null)
    assert.equal(f.form.project_product, 2); assert.equal(f.form.module, 3)
    assert.equal(f.form.title, '')
  } finally { f.close() }
})

test('failed save retains the draft and version; retry writes once and emits only after success', async () => {
  const writes = []; let fail = true
  const f = setup({ api: { putManualCase: async payload => { writes.push(payload); if (fail) throw Error('Rejected') } } })
  try {
    await f.open(record()); f.form.title = 'Changed'
    assert.equal(await f.saveCase(), false)
    assert.equal(f.visible.value, true); assert.equal(f.saveError.value, true)
    assert.equal(f.form.title, 'Changed'); assert.equal(f.form.version_no, 7)
    assert.equal(f.saving.value, false); assert.deepEqual(f.events, [])
    fail = false; await f.saveCase()
    assert.equal(f.visible.value, false); assert.equal(f.form.id, null)
    assert.equal(writes.length, 2); assert.equal(writes[1].version_no, 7)
    assert.deepEqual(f.events, [['saved']])
  } finally { f.close() }
})

test('invalid input keeps the editor open and makes no request', async () => {
  let calls = 0
  const f = setup({ api: { postManualCase: async () => { ++calls } } })
  try {
    await f.open(); assert.equal(await f.saveCase(), false)
    assert.equal(calls, 0); assert.equal(f.visible.value, true); assert.equal(f.saving.value, false)
  } finally { f.close() }
})

test('editor prefers the current grid relation IDs over stale display relation objects', async () => {
  const f = setup()
  try {
    await f.open(record({ project_product_id: 8, module_id: 9, owner_id: 10 }))
    assert.equal(f.form.project_product, 8); assert.equal(f.form.module, 9); assert.equal(f.form.owner, 10)
  } finally { f.close() }
})

test('pending write blocks duplicate submission, cancel and reopen across context invalidation', async () => {
  const pending = deferred(); let calls = 0
  const f = setup({ api: { putManualCase: async () => { ++calls; await pending.promise } } })
  try {
    await f.open(record()); const saving = f.saveCase()
    assert.equal(f.canCancel(), false); assert.equal(await f.saveCase(), false)
    f.props.contextKey = 'new-role'
    assert.equal(f.visible.value, false); assert.equal(f.saving.value, true)
    await f.open(record({ id: 22 })); assert.equal(f.visible.value, false)
    pending.resolve(); await saving
    assert.equal(calls, 1); assert.deepEqual(f.events, []); assert.equal(f.saving.value, false)
    await f.open(record({ id: 22 })); assert.equal(f.form.id, 22)
  } finally { f.close() }
})

test('late category responses do not overwrite another record or release its loading', async () => {
  const first = deferred(), second = deferred(); let calls = 0
  const f = setup({ api: { getFunctionalCaseCategoryOptions: () => ++calls === 1 ? first.promise : second.promise } })
  try {
    const old = f.open(record()); await flush()
    const fresh = f.open(record({ id: 22 })); await flush()
    first.resolve({ data: { category_level_1: ['Old'] } }); await old; await flush()
    assert.equal(f.form.id, 22); assert.equal(f.categoryLoading.value, true)
    assert.deepEqual([...f.categoryOptions.category_level_1], [])
    second.resolve({ data: { category_level_1: ['Current'] } }); await fresh; await flush()
    assert.equal(f.categoryLoading.value, false)
    assert.deepEqual([...f.categoryOptions.category_level_1], ['Current'])
  } finally { f.close() }
})

test('category failure supports retry without losing form edits', async () => {
  let fail = true
  const f = setup({ api: { getFunctionalCaseCategoryOptions: async () => { if (fail) throw Error('Offline'); return { data: { category_level_1: ['Ready'] } } } } })
  try {
    await f.open(record()); await flush(); f.form.title = 'Retained'
    assert.equal(f.categoryError.value, true); assert.equal(f.categoryLoading.value, false)
    fail = false; await f.loadCategoryOptions()
    assert.equal(f.form.title, 'Retained'); assert.equal(f.categoryError.value, false)
    assert.deepEqual([...f.categoryOptions.category_level_1], ['Ready'])
  } finally { f.close() }
})

test('KeepAlive deactivation invalidates reads, activation permits a fresh explicit open', async () => {
  const hooks = {}; const pending = deferred()
  const f = setup({
    modules: { vue: { ...vue, onDeactivated: fn => { hooks.stop = fn }, onActivated: fn => { hooks.start = fn }, onBeforeUnmount: fn => { hooks.unmount = fn } } },
    api: { getFunctionalCaseCategoryOptions: () => pending.promise },
  })
  try {
    const reading = f.open(record()); hooks.stop()
    pending.resolve({ data: { category_level_1: ['Old'] } }); await reading
    assert.equal(f.visible.value, false); assert.equal(f.form.id, null)
    assert.deepEqual([...f.categoryOptions.category_level_1], [])
    await f.open(record()); assert.equal(f.visible.value, false)
    hooks.start(); await f.open(record({ id: 22 })); assert.equal(f.form.id, 22)
    hooks.unmount(); assert.equal(f.visible.value, false)
  } finally { f.close() }
})

test('page and editor script/template/style compile with installed Vue', () => {
  for (const relative of ['index.vue', 'components/CaseEditor.vue', 'components/CaseHistoryDrawer.vue', 'components/CaseBindingDialog.vue', 'components/CasePlanDialog.vue']) {
    const filename = path.join(base, relative), source = readFileSync(filename, 'utf8')
    const { descriptor, errors } = parse(source, { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: relative })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: relative, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: relative, scoped: style.scoped }).errors, [])
  }
})
