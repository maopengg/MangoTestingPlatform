import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/iteration/details')
const subject = (values = {}) => ({
  id: 11, requirement_name: 'Example requirement', version_no: 2,
  development_owner: { id: 4, name: 'Example developer' }, priority: 0,
  planned_start_date: '2026-11-01', planned_submit_date: '2026-11-05', status: 3,
  ...values,
})
function setup(write) {
  const hooks = { stop: [], activate: [], unmount: [] }, writes = []
  const f = harness('IterationScheduleDialog', 'open,reset,save,form,visible,saving,saveError,canCancel,subjectLabel,ownerOptions', {
    base,
    props: { contextKey: 'A', iterationId: 1, users: [], priorityOptions: [], statusOptions: [] },
    api: { putManualSuite: async body => { writes.push(body); return write ? write(body) : { data: { id: body.id } } } },
    modules: { vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) } },
  })
  return { ...f, hooks, writes, cleanup: () => { hooks.unmount.forEach(fn => fn()); f.close() } }
}

test('schedule owns a fresh draft and immutable target/payload through submission', async () => {
  const pending = deferred(), f = setup(() => pending.promise)
  try {
    const row = subject({ suite_id: 21 }); f.open(row)
    row.development_owner.id = 99; row.suite_id = 22
    const saving = f.save(); f.form.priority = 2; f.form.planned_start_date = '2026-11-02'
    assert.deepEqual(f.writes, [{ id: 21, iteration_ref: 1, development_owner: 4, priority: 0, planned_start_date: '2026-11-01', planned_submit_date: '2026-11-05', status: 3 }])
    assert.equal(f.saving.value, true); assert.equal(f.canCancel(), false)
    assert.equal(f.exposed.isSaving(21), true)
    await f.save(); f.open(subject({ id: 99 })); assert.equal(f.writes.length, 1)
    pending.resolve({ data: { id: 21 } }); await saving
    assert.equal(f.visible.value, false); assert.equal(f.saving.value, false)
    assert.equal(f.exposed.isSaving(21), false)
    assert.deepEqual(f.events, [['saved', 21]])
  } finally { f.cleanup() }
})

test('cancel then reopen rebuilds the form, label and owner fallback without editing the source', () => {
  const f = setup()
  try {
    const row = subject(); f.open(row); f.form.development_owner = null; f.form.status = 7
    assert.equal(row.status, 3); assert.equal(row.development_owner.id, 4)
    f.reset(); assert.equal(f.form.development_owner, null); assert.equal(f.subjectLabel.value, '')
    f.open(subject({ id: 12, requirement_name: 'Second', development_owner: null, planned_start_date: null, planned_submit_date: null, priority: 1 }))
    assert.equal(f.form.development_owner, null); assert.equal(f.form.priority, 1)
    assert.equal(f.form.planned_start_date, null); assert.equal(f.subjectLabel.value, 'Second · V2')
    assert.deepEqual(f.ownerOptions.value, []); assert.equal(f.writes.length, 0)
  } finally { f.cleanup() }
})

test('selected owner fallback retains a readable label until asynchronous options arrive', async () => {
  const f = setup()
  try {
    f.open(subject()); assert.deepEqual(f.ownerOptions.value, [{ key: 4, title: 'Example developer' }])
    f.props.users = [{ key: 4, title: 'Fresh name' }]; await flush()
    assert.deepEqual(f.ownerOptions.value, [{ key: 4, title: 'Fresh name' }])
    assert.equal(f.form.development_owner, 4)
  } finally { f.cleanup() }
})

test('failed save retains input and allows retry; cancellation and close happen only after acknowledgement', async () => {
  let failing = true
  const f = setup(async body => { if (failing) throw Error('Offline'); return { data: { id: body.id } } })
  try {
    f.open(subject()); f.form.planned_submit_date = '2026-11-06'
    await f.save(); assert.equal(f.saveError.value, true); assert.equal(f.visible.value, true)
    assert.equal(f.form.planned_submit_date, '2026-11-06'); assert.equal(f.saving.value, false)
    assert.equal(f.canCancel(), true); assert.deepEqual(f.events, [])
    failing = false; await f.save(); assert.equal(f.visible.value, false)
    assert.deepEqual(f.events, [['saved', 11]]); assert.equal(f.writes.length, 2)
  } finally { f.cleanup() }
})

test('wrong record or missing acknowledgement does not close the current draft', async () => {
  for (const data of [null, [], {}, { id: 99 }]) {
    const f = setup(async () => ({ data }))
    try {
      f.open(subject()); await f.save()
      assert.equal(f.visible.value, true); assert.equal(f.saveError.value, true); assert.deepEqual(f.events, [])
    } finally { f.cleanup() }
  }
})

test('clearable values are explicitly sent as null; metadata and relation objects never enter writes', async () => {
  const f = setup()
  try {
    f.open(subject({ audit: 'Do not send', iteration_ref: 99 }))
    f.form.development_owner = undefined; f.form.planned_start_date = ''; f.form.planned_submit_date = undefined
    await f.save()
    assert.deepEqual(f.writes, [{ id: 11, iteration_ref: 1, development_owner: null, priority: 0, planned_start_date: null, planned_submit_date: null, status: 3 }])
  } finally { f.cleanup() }
})

for (const scope of ['context', 'iteration', 'deactivate', 'unmount']) {
  test(`schedule ${scope} invalidation suppresses late responses while preserving the physical lock`, async () => {
    const pending = deferred(), f = setup(() => pending.promise)
    try {
      f.open(subject()); const saving = f.save()
      if (scope === 'context') { f.props.contextKey = 'B'; f.props.contextKey = 'A' }
      if (scope === 'iteration') { f.props.iterationId = 2; f.props.iterationId = 1 }
      if (scope === 'deactivate') { f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()) }
      if (scope === 'unmount') f.hooks.unmount.forEach(fn => fn())
      f.open(subject({ id: 22 })); await f.save()
      assert.equal(f.visible.value, false); assert.equal(f.saving.value, true)
      assert.equal(f.exposed.isSaving(11), true); assert.equal(f.writes.length, 1)
      pending.resolve({ data: { id: 11 } }); await saving
      assert.equal(f.saveError.value, false); assert.equal(f.saving.value, false); assert.deepEqual(f.events, [])
      f.open(subject({ id: 22 })); assert.equal(f.visible.value, scope !== 'unmount')
    } finally { f.cleanup() }
  })
}

test('late failure from an inactive context does not mark the fresh editor as failed', async () => {
  const pending = deferred(), f = setup(() => pending.promise)
  try {
    f.open(subject()); const saving = f.save(); f.props.contextKey = 'B'
    pending.reject(Error('Old failure')); await saving
    assert.equal(f.saveError.value, false); assert.equal(f.visible.value, false)
    f.open(subject({ id: 22 })); assert.equal(f.visible.value, true); assert.equal(f.saveError.value, false)
  } finally { f.cleanup() }
})

test('invalid or absent targets cannot write', async () => {
  const f = setup()
  try {
    for (const id of [0, -1, NaN, Infinity, 1.5]) { f.open(subject({ id })); await f.save() }
    f.props.iterationId = 0; f.open(subject()); await f.save()
    assert.equal(f.visible.value, false); assert.deepEqual(f.writes, [])
  } finally { f.cleanup() }
})

test('parent retains the acknowledged saved state while region refreshes report their own failures', async () => {
  let refreshes = 0
  const saveState = vue.ref('idle')
  const onSaved = method('onScheduleSaved', {
    saveState,
    available: () => true,
    refreshBusiness: async () => { ++refreshes; return [false] },
  }, path.join(base, 'index.vue'))
  await onSaved()
  assert.equal(saveState.value, 'saved')
  assert.equal(refreshes, 1)
})

test('iteration detail and private schedule window compile scripts, templates and styles', () => {
  for (const file of ['index.vue', 'components/IterationScheduleDialog.vue']) {
    const filename = path.join(base, file), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: file, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: file, scoped: style.scoped, preprocessLang: style.lang }).errors, [])
  }
})
