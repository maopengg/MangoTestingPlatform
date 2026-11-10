import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/plan')
const row = (id = 10) => ({ id, case_no: `CASE-${id}`, title: `Example case ${id}`, priority: 0 })
function setup(overrides = {}) {
  const calls = [], messages = [], hooks = { stop: [], activate: [], unmount: [] }
  const f = harness('PlanCasePickerDrawer', 'open,reset,loadCases,save,selectRows,resetSearch,onVisibleChange,canCancel,visible,loading,saving,readError,saveError,rows,selectedKeys,filters,subject', {
    base, props: { contextKey: 'A', planId: 1, productId: 2, editable: true, priorityOptions: [] },
    api: {
      getManualCase: async query => { calls.push(['read', query]); return overrides.read ? overrides.read(query) : { data: [row(), row(11)] } },
      addFunctionalPlanCases: async body => { calls.push(['write', body]); return overrides.write ? overrides.write(body) : { data: { created_count: body.case_ids.length, ignored_count: 0 } } },
    }, modules: {
      vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      '@arco-design/web-vue': { Message: { success: text => messages.push(['success', text]), warning: text => messages.push(['warning', text]) } },
    },
  })
  return { ...f, calls, messages, hooks, cleanup() { hooks.unmount.forEach(fn => fn()); f.close() } }
}
test('opening reads the product-scoped published library with the existing 500-row protocol', async () => {
  const f = setup()
  try {
    f.open(); assert.equal(f.loading.value, true); await flush()
    assert.deepEqual(f.calls[0], ['read', { project_product: 2, status: 1, page: 1, pageSize: 500 }])
    assert.equal(f.rows.value.length, 2); assert.equal(f.loading.value, false); assert.equal(f.rows.value[0].priority, 0)
  } finally { f.cleanup() }
})
test('cancel and reopen reset filters, selection, errors and target', async () => {
  const f = setup()
  try {
    f.open(); await flush(); f.selectRows([10]); f.filters.title = 'Old'; f.filters.module = 9
    f.onVisibleChange(false); assert.equal(f.visible.value, false); assert.equal(f.subject.value, null)
    f.props.planId = 2; f.props.productId = 3; f.open(); await flush()
    assert.equal(f.filters.title, ''); assert.equal(f.filters.module, null); assert.deepEqual(f.selectedKeys.value, [])
    assert.equal(f.calls.at(-1)[1].project_product, 3); assert.equal(f.subject.value.planId, 2)
  } finally { f.cleanup() }
})
test('search captures its query and ignores late results from older searches', async () => {
  const a = deferred(), b = deferred(); let count = 0
  const f = setup({ read: () => ++count === 1 ? Promise.resolve({ data: [row()] }) : count === 2 ? a.promise : b.promise })
  try {
    f.open(); await flush(); f.filters.title = 'First'; f.filters.module = 9; const first = f.loadCases()
    f.filters.title = 'Second'; const second = f.loadCases()
    assert.equal(f.calls[1][1].title, 'First'); assert.equal(f.calls[2][1].title, 'Second')
    b.resolve({ data: [row(22)] }); await second
    a.resolve({ data: [row(20)] }); await first
    assert.equal(f.rows.value[0].id, 22); assert.equal(f.loading.value, false)
  } finally { f.cleanup() }
})
test('read failure retains current rows and selection, ends loading, and permits retry', async () => {
  let fail = false, f = setup({ read: async () => { if (fail) throw Error('Offline'); return { data: [row()] } } })
  try {
    f.open(); await flush(); f.selectRows([10]); fail = true; assert.equal(await f.loadCases(), false)
    assert.equal(f.rows.value.length, 1); assert.deepEqual(f.selectedKeys.value, [10]); assert.equal(f.readError.value, true); assert.equal(f.loading.value, false)
    fail = false; assert.equal(await f.loadCases(), true); assert.equal(f.readError.value, false)
  } finally { f.cleanup() }
})
test('malformed rows are read errors rather than apparent empty successful data', async () => {
  for (const data of [{}, [{ id: 0 }], [{ id: '10' }]]) {
    const f = setup({ read: async () => ({ data }) })
    try { f.open(); await flush(); assert.equal(f.readError.value, true); assert.deepEqual(f.rows.value, []); assert.equal(f.loading.value, false) }
    finally { f.cleanup() }
  }
})
test('selection is deduplicated and restricted to current rows; successful search prunes old keys', async () => {
  let data = [row(), row(11)], f = setup({ read: async () => ({ data }) })
  try {
    f.open(); await flush(); f.selectRows(['10', 10, 11, 99, 0, -1]); assert.deepEqual(f.selectedKeys.value, [10, 11])
    data = [row(11)]; await f.loadCases(); assert.deepEqual(f.selectedKeys.value, [11])
    f.filters.title = 'Change'; await f.resetSearch(); assert.equal(f.filters.title, ''); assert.deepEqual(f.selectedKeys.value, [])
  } finally { f.cleanup() }
})
test('joining captures plan and case IDs, prevents duplicate requests and cancellation, then closes on acknowledgement', async () => {
  const pending = deferred(), f = setup({ write: () => pending.promise })
  try {
    f.open(); await flush(); f.selectRows([10, 11]); const saving = f.save()
    f.selectedKeys.value = [99]; f.selectRows([11]); f.onVisibleChange(false); f.open(); await f.save()
    assert.equal(f.canCancel(), false); assert.equal(f.visible.value, true); assert.equal(f.exposed.isSaving(), true)
    assert.deepEqual(f.calls.filter(([key]) => key === 'write'), [['write', { plan_id: 1, case_ids: [10, 11] }]])
    pending.resolve({ data: { created_count: 2, ignored_count: 0 } }); assert.equal(await saving, true)
    assert.equal(f.visible.value, false); assert.equal(f.saving.value, false); assert.deepEqual(f.events, [['changed', 1]])
  } finally { f.cleanup() }
})
test('join failure retains selected rows, draft and retry capability', async () => {
  let fail = true, f = setup({ write: async () => { if (fail) throw Error('Offline'); return { data: { created_count: 1, ignored_count: 0 } } } })
  try {
    f.open(); await flush(); f.selectRows([10]); f.filters.title = 'Keep'
    assert.equal(await f.save(), false); assert.equal(f.saveError.value, true); assert.equal(f.saving.value, false)
    assert.deepEqual(f.selectedKeys.value, [10]); assert.equal(f.filters.title, 'Keep'); assert.deepEqual(f.events, [])
    fail = false; assert.equal(await f.save(), true); assert.deepEqual(f.events, [['changed', 1]])
  } finally { f.cleanup() }
})
test('valid idempotent joins accept zero created while invalid counts keep the drawer open', async () => {
  for (const data of [null, {}, { created_count: -1, ignored_count: 0 }, { created_count: 0, ignored_count: 1 }]) {
    const f = setup({ write: async () => ({ data }) })
    try {
      f.open(); await flush(); f.selectRows([10]); const result = await f.save()
      assert.equal(result, data?.ignored_count === 1); assert.equal(f.visible.value, data?.ignored_count !== 1)
    } finally { f.cleanup() }
  }
})
for (const scope of ['context', 'plan', 'product', 'editable', 'deactivate', 'unmount']) {
  test(`${scope} invalidates reads and pending writes without exposing late errors or releasing physical locks early`, async () => {
    const pending = deferred(), f = setup({ write: () => pending.promise })
    try {
      f.open(); await flush(); f.selectRows([10]); const saving = f.save()
      if (scope === 'context') { f.props.contextKey = 'B'; f.props.contextKey = 'A' }
      if (scope === 'plan') { f.props.planId = 2; f.props.planId = 1 }
      if (scope === 'product') { f.props.productId = 3; f.props.productId = 2 }
      if (scope === 'editable') { f.props.editable = false; f.props.editable = true }
      if (scope === 'deactivate') { f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()) }
      if (scope === 'unmount') f.hooks.unmount.forEach(fn => fn())
      assert.equal(f.visible.value, false); assert.equal(f.saving.value, true); f.open(); assert.equal(f.visible.value, false)
      pending.reject(Error('Late failure')); await saving
      assert.equal(f.saveError.value, false); assert.equal(f.saving.value, false); assert.deepEqual(f.events, [])
    } finally { f.cleanup() }
  })
}
test('closing invalidates in-flight reads, including A-B-A reopen', async () => {
  const old = deferred(); let count = 0
  const f = setup({ read: () => ++count === 1 ? old.promise : Promise.resolve({ data: [row(22)] }) })
  try {
    f.open(); f.onVisibleChange(false); f.open(); await flush()
    old.resolve({ data: [row(10)] }); await flush()
    assert.equal(f.rows.value[0].id, 22); assert.equal(f.loading.value, false)
  } finally { f.cleanup() }
})
test('invalid targets and completed plans never read or write', async () => {
  const f = setup()
  try {
    f.props.planId = 0; f.open(); f.props.planId = 1; f.props.productId = null; f.open()
    f.props.productId = 2; f.props.editable = false; f.open(); await f.save(); assert.deepEqual(f.calls, [])
  } finally { f.cleanup() }
})
test('drawer and integrated parent compile scripts, templates and scoped styles', async () => {
  for (const file of ['components/PlanCasePickerDrawer.vue', 'details.vue']) {
    const filename = path.join(base, file), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, []); const script = compileScript(descriptor, { id: file })
    assert.deepEqual(compileTemplate({ id: file, source: descriptor.template.content, filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ id: file, filename, source: style.content, scoped: true, preprocessLang: style.lang })).errors, [])
  }
})
