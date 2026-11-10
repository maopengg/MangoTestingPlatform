import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { compileScript, compileStyle, compileTemplate, parse } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/defect')
const subject = (values = {}) => ({ id: 11, defect_no: 'DEF-11', status: 2, assignee: { id: 4 }, resolution: 0, resolution_note: 'Note', environment: 'Example environment', ...values })
function setup(kind, overrides = {}) {
  const hooks = { stop: [], activate: [], unmount: [] }, writes = [], navigations = [], messages = []
  const f = harness(kind === 'transition' ? 'DefectTransitionDialog' : 'DefectRetestDialog',
    'open,reset,save,form,visible,saving,saveError,canCancel' + (kind === 'retest' ? ',createdPlanId,navigationError' : ',transitionOptions'), {
      base, props: { contextKey: 'A', users: [{ key: 4, title: 'Example user' }] },
      api: {
        transitionFunctionalDefect: async body => { writes.push(body); return overrides.write ? overrides.write(body) : { data: { id: body.id, status: body.status } } },
        createFunctionalDefectRetestPlan: async body => { writes.push(body); return overrides.write ? overrides.write(body) : { data: { id: 99 } } },
      },
      modules: {
        vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
        'vue-router': { useRouter: () => ({ push: async target => { navigations.push(target); return overrides.navigate?.(target) } }) },
        '@/store/modules/get-enum': { useEnum: () => ({ functional_test_defect_status: [0, 1, 2, 3, 4, 5].map(key => ({ key, title: `Status ${key}` })), functional_test_defect_resolution: [{ key: 0, title: 'Fixed' }] }) },
        '@arco-design/web-vue': { Message: Object.fromEntries(['warning', 'success'].map(key => [key, value => messages.push([key, value])])) },
      },
    })
  return { ...f, hooks, writes, navigations, messages, cleanup: () => { hooks.unmount.forEach(fn => fn()); f.close() } }
}

test('transition captures subject and sends only whitelisted fields including zero resolution', async () => {
  const pending = deferred(), f = setup('transition', { write: () => pending.promise })
  try {
    const row = subject(); f.open(row, 3); row.id = 999; row.assignee.id = 8
    const saving = f.save(); f.form.resolution_note = 'Later'
    assert.deepEqual(f.writes, [{ id: 11, status: 3, assignee: 4, resolution: 0, resolution_note: 'Note' }])
    assert.equal(f.saving.value, true); assert.equal(f.canCancel(), false)
    await f.save(); assert.equal(f.writes.length, 1)
    pending.resolve({ data: { id: 11, status: 3 } }); await saving
    assert.equal(f.visible.value, false); assert.equal(f.saving.value, false)
    assert.deepEqual(f.events, [['saved', { id: 11, status: 3 }]])
  } finally { f.cleanup() }
})

test('transition validates the existing state machine and required fields without writing', async () => {
  const f = setup('transition')
  try {
    f.open(subject({ status: 0 }), 3); await f.save()
    f.open(subject({ status: 1, assignee: null }), 2); await f.save()
    f.open(subject({ resolution: null }), 3); await f.save()
    assert.equal(f.writes.length, 0); assert.equal(f.visible.value, true)
    assert.equal(f.messages.length, 3)
  } finally { f.cleanup() }
})

test('transition failure preserves input and retry closes only after success', async () => {
  let failing = true
  const f = setup('transition', { write: async body => { if (failing) throw Error('Offline'); return { data: { id: body.id, status: body.status } } } })
  try {
    f.open(subject(), 3); f.form.resolution_note = 'Preserve'
    await f.save(); assert.equal(f.saveError.value, true); assert.equal(f.visible.value, true)
    assert.equal(f.form.resolution_note, 'Preserve'); assert.equal(f.saving.value, false)
    failing = false; await f.save(); assert.equal(f.visible.value, false); assert.equal(f.events.length, 1)
  } finally { f.cleanup() }
})

test('wrong-record transition acknowledgement is not applied as a successful update', async () => {
  const f = setup('transition', { write: async () => ({ data: { id: 999, status: 3 } }) })
  try {
    f.open(subject(), 3); await f.save()
    assert.equal(f.saveError.value, true); assert.equal(f.visible.value, true); assert.deepEqual(f.events, [])
  } finally { f.cleanup() }
})

test('cancel and reopen rebuild each window draft without retaining previous values', async () => {
  for (const kind of ['transition', 'retest']) {
    const f = setup(kind)
    try {
      f.open(subject(), 3); f.form[kind === 'transition' ? 'resolution_note' : 'name'] = 'Unsaved'
      f.reset(); f.open(subject({ id: 22, defect_no: 'DEF-22', resolution_note: 'Second' }), 3)
      assert.equal(f.form[kind === 'transition' ? 'resolution_note' : 'name'], kind === 'transition' ? 'Second' : 'DEF-22 缺陷验证')
      assert.equal(f.saveError.value, false); assert.equal(f.writes.length, 0)
    } finally { f.cleanup() }
  }
})

for (const kind of ['transition', 'retest']) {
  test(`${kind} ignores a late response across context A to B to A and keeps the physical lock`, async () => {
    const pending = deferred(), f = setup(kind, { write: () => pending.promise })
    try {
      f.open(subject(), 3); const saving = f.save()
      f.props.contextKey = 'B'; f.props.contextKey = 'A'
      f.open(subject({ id: 22 }), 3); await f.save()
      assert.equal(f.visible.value, false); assert.equal(f.saving.value, true); assert.equal(f.writes.length, 1)
      assert.equal(f.exposed.isSaving(11), true); assert.equal(f.exposed.isSaving(22), false)
      pending.resolve({ data: { id: kind === 'transition' ? 11 : 99 } }); await saving
      assert.deepEqual(f.events, []); assert.deepEqual(f.navigations, []); assert.equal(f.saving.value, false)
      assert.equal(f.exposed.isSaving(11), false)
      f.open(subject({ id: 22 }), 3); assert.equal(f.visible.value, true)
    } finally { f.cleanup() }
  })

  test(`${kind} deactivation and unmount suppress old failures and activation permits a fresh draft`, async () => {
    const pending = deferred(), f = setup(kind, { write: () => pending.promise })
    try {
      f.open(subject(), 3); const saving = f.save()
      f.hooks.stop.forEach(fn => fn()); pending.reject(Error('Late failure')); await saving
      assert.equal(f.saveError.value, false); assert.equal(f.visible.value, false)
      f.hooks.activate.forEach(fn => fn()); f.open(subject({ id: 22 }), 3); assert.equal(f.visible.value, true)
      f.hooks.unmount.forEach(fn => fn()); f.open(subject()); assert.equal(f.visible.value, false)
    } finally { f.cleanup() }
  })
}

test('retest navigation retry reuses the created plan instead of creating it again', async () => {
  let failed = true
  const f = setup('retest', { navigate: async () => { if (failed) throw Error('Chunk failed') } })
  try {
    const row = subject(); f.open(row); row.id = 999; row.assignee.id = 8
    await f.save()
    assert.deepEqual(f.writes, [{ id: 11, name: 'DEF-11 缺陷验证', owner: 4, environment: 'Example environment', build_version: '' }])
    assert.equal(f.createdPlanId.value, 99); assert.equal(f.navigationError.value, true); assert.equal(f.saveError.value, false)
    failed = false; await f.save(); assert.equal(f.writes.length, 1); assert.equal(f.navigations.length, 2)
    assert.equal(f.visible.value, false)
  } finally { f.cleanup() }
})

test('retest aborted navigation retains the confirmed plan and failure permits creation retry', async () => {
  let failing = true
  const f = setup('retest', { write: async () => { if (failing) throw Error('Rejected'); return { data: { id: 99 } } }, navigate: async () => ({ type: 4 }) })
  try {
    f.open(subject()); f.form.name = 'Preserved'; await f.save()
    assert.equal(f.saveError.value, true); assert.equal(f.form.name, 'Preserved'); assert.equal(f.createdPlanId.value, null)
    failing = false; await f.save(); assert.equal(f.navigationError.value, true); assert.equal(f.createdPlanId.value, 99)
    await f.save(); assert.equal(f.writes.length, 2); assert.equal(f.navigations.length, 2)
  } finally { f.cleanup() }
})

test('a late navigation failure after closing the scope does not reopen or mark a new window failed', async () => {
  const pending = deferred(), f = setup('retest', { navigate: () => pending.promise })
  try {
    f.open(subject()); const saving = f.save(); await flush()
    assert.equal(f.createdPlanId.value, 99)
    f.props.contextKey = 'New'; pending.reject(Error('Late navigation failure')); await saving
    assert.equal(f.navigationError.value, false); assert.equal(f.createdPlanId.value, null); assert.equal(f.visible.value, false)
  } finally { f.cleanup() }
})

test('defect page and both private windows compile scripts, templates and styles', () => {
  for (const file of ['index.vue', 'components/DefectTransitionDialog.vue', 'components/DefectRetestDialog.vue', 'components/DefectEditorDrawer.vue']) {
    const filename = path.join(base, file), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, []); compileScript(descriptor, { id: file })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: file }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: file, scoped: style.scoped, preprocessLang: style.lang }).errors, [])
  }
})

