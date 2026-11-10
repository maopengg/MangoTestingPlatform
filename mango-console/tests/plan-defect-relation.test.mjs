import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/plan')
function setup(overrides = {}) {
  const calls = [], hooks = { stop: [], activate: [], unmount: [] }
  const f = harness('PlanDefectRelationDialog', 'open,reset,loadOptions,save,form,mode,subject,visible,loading,saving,readError,saveError,options,canCancel', {
    base, props: { contextKey: 'A', planId: 1, productId: 2 },
    api: {
      getFunctionalDefectOptions: async query => { calls.push(['read', query]); return overrides.read ? overrides.read(query) : { data: [{ id: 3, defect_no: 'DEF-3', title: 'Example defect' }] } },
      bindFunctionalDefectCases: async body => { calls.push(['bind', body]); return overrides.write ? overrides.write(body) : { data: { created_count: 1 } } },
      unbindFunctionalDefectCases: async body => { calls.push(['unbind', body]); return overrides.write ? overrides.write(body) : { data: { deleted_count: 1 } } },
    }, modules: { vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) } },
  })
  return { ...f, calls, hooks, cleanup() { hooks.unmount.forEach(fn => fn()); f.close() } }
}
test('bind captures case targets and loads scoped options, never reading later parent selection', async () => {
  const f = setup(), selected = [10, 11, 10]
  try {
    f.open('bind', selected); selected.splice(0, 3, 99); await flush(); f.form.defectId = 3; await f.save()
    assert.deepEqual(f.calls, [['read', { project_product: 2 }], ['bind', { id: 3, plan_case_ids: [10, 11] }]])
    assert.equal(f.visible.value, false); assert.deepEqual(f.events, [['changed', 1]])
  } finally { f.cleanup() }
})
test('unbind owns copied choices and uses the unbind API without loading unrelated options', async () => {
  const f = setup(), choices = [{ value: 3, label: 'Existing defect' }]
  try {
    f.open('unbind', [10], choices); choices[0].value = 99; choices[0].label = 'Changed'
    assert.equal(f.options.value[0].label, 'Existing defect'); await f.save()
    assert.deepEqual(f.calls, [['unbind', { id: 3, plan_case_ids: [10] }]])
  } finally { f.cleanup() }
})
test('cancel and reopening reset selected defect, options, mode and errors', async () => {
  const f = setup()
  try {
    f.open('unbind', [10], [{ value: 3, label: 'Old' }]); f.reset(); f.open('bind', [11]); await flush()
    assert.equal(f.form.defectId, null); assert.equal(f.mode.value, 'bind'); assert.deepEqual(f.subject.value.caseIds, [11])
    assert.equal(f.saveError.value, false); assert.equal(f.readError.value, false)
  } finally { f.cleanup() }
})
test('option failure has a local retry and does not allow unknown defect IDs', async () => {
  let fail = true, f = setup({ read: async () => { if (fail) throw Error('Offline'); return { data: [{ id: 3, defect_no: 'DEF-3', title: 'Example' }] } } })
  try {
    f.open('bind', [10]); await flush(); assert.equal(f.readError.value, true); assert.equal(f.loading.value, false)
    f.form.defectId = 999; await f.save(); assert.equal(f.calls.filter(([kind]) => kind === 'bind').length, 0)
    fail = false; await f.loadOptions(); assert.equal(f.readError.value, false); assert.equal(f.form.defectId, null)
    f.form.defectId = 3; await f.save(); assert.equal(f.calls.at(-1)[0], 'bind')
  } finally { f.cleanup() }
})
test('out-of-order and closed-window option results never replace current options', async () => {
  const old = deferred(), current = deferred(); let count = 0
  const f = setup({ read: () => ++count === 1 ? old.promise : current.promise })
  try {
    f.open('bind', [10]); f.reset(); f.open('bind', [11])
    current.resolve({ data: [{ id: 4, defect_no: 'DEF-4', title: 'Current' }] }); await flush()
    old.reject(Error('Old')); await flush()
    assert.equal(f.options.value[0].value, 4); assert.equal(f.readError.value, false); assert.equal(f.loading.value, false)
  } finally { f.cleanup() }
})
test('physical write prevents duplicate confirmations, closing and reopening, then releases after failure', async () => {
  const pending = deferred(), f = setup({ write: () => pending.promise })
  try {
    f.open('unbind', [10], [{ value: 3, label: 'Defect' }]); const saving = f.save()
    await f.save(); f.open('bind', [11]); assert.equal(f.mode.value, 'unbind'); assert.equal(f.canCancel(), false)
    assert.equal(f.calls.length, 1); assert.equal(f.saving.value, true)
    pending.reject(Error('Offline')); await saving
    assert.equal(f.visible.value, true); assert.equal(f.form.defectId, 3); assert.equal(f.saveError.value, true); assert.equal(f.saving.value, false)
  } finally { f.cleanup() }
})
test('invalid write acknowledgements preserve draft, while zero-change idempotent requests close', async () => {
  for (const data of [null, {}, { deleted_count: -1 }, { deleted_count: 0 }]) {
    const f = setup({ write: async () => ({ data }) })
    try {
      f.open('unbind', [10], [{ value: 3, label: 'Defect' }]); await f.save()
      assert.equal(f.visible.value, data?.deleted_count !== 0); assert.equal(f.events.length, data?.deleted_count === 0 ? 1 : 0)
    } finally { f.cleanup() }
  }
})
for (const scope of ['context', 'plan', 'product', 'deactivate', 'unmount']) {
  test(`${scope} resets the window and ignores late write notifications without releasing its physical lock early`, async () => {
    const pending = deferred(), f = setup({ write: () => pending.promise })
    try {
      f.open('unbind', [10], [{ value: 3, label: 'Defect' }]); const saving = f.save()
      if (scope === 'context') { f.props.contextKey = 'B'; f.props.contextKey = 'A' }
      if (scope === 'plan') { f.props.planId = 2; f.props.planId = 1 }
      if (scope === 'product') { f.props.productId = 3; f.props.productId = 2 }
      if (scope === 'deactivate') { f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()) }
      if (scope === 'unmount') f.hooks.unmount.forEach(fn => fn())
      assert.equal(f.visible.value, false); assert.equal(f.saving.value, true); f.open('bind', [11]); assert.equal(f.visible.value, false)
      pending.resolve({ data: { deleted_count: 1 } }); await saving
      assert.deepEqual(f.events, []); assert.equal(f.saving.value, false); assert.equal(f.saveError.value, false)
    } finally { f.cleanup() }
  })
}
test('dialog compiles script, template and scoped styling', async () => {
  const filename = path.join(base, 'components/PlanDefectRelationDialog.vue')
  const { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
  assert.deepEqual(errors, []); const script = compileScript(descriptor, { id: filename })
  assert.deepEqual(compileTemplate({ id: filename, filename, source: descriptor.template.content, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ id: filename, filename, source: style.content, scoped: true })).errors, [])
})
