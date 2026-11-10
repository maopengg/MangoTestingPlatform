import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/case-library')
const selection = () => [{ id: 11, productId: 2, ownerId: 3 }, { id: 12, productId: 2, ownerId: 4 }]
const bindingSubject = () => ({ id: 11, bindings: [
  { automation_type: 0, automation_case_id: 101 }, { automation_type: 1, automation_case_id: 102 },
] })
function binding(overrides = {}) {
  return harness('CaseBindingDialog', 'open, form, subject, visible, saving, saveError, save, reset, canCancel, loadBindingId', {
    base, props: { contextKey: 'context-1' }, ...overrides,
  })
}
function plan(overrides = {}) {
  return harness('CasePlanDialog', 'openCreate, openJoin, form, joinForm, mode, visible, saving, saveError, save, reset, canCancel, caseIds, createdPlanId, planOptions, planLoading, planError, loadPlans, requirementOptions, requirementLoading, requirementError, loadRequirements, iterationOptions, iterationLoading, iterationError, loadIterations, onProductChange, onScopeChange', {
    base, props: { contextKey: 'context-1', users: [], defaults: { projectProduct: 9, module: null } }, ...overrides,
  })
}
function fill(f) { Object.assign(f.form, { name: 'Example plan', owner: 3, requirement_version: 7 }) }

test('binding snapshots relations, switches type and resets unsaved input on reopen', () => {
  const f = binding()
  try {
    const source = bindingSubject(); f.open(source)
    assert.equal(f.form.automation_case_id, 101)
    source.bindings[1].automation_case_id = 999
    f.form.automation_type = 1; f.loadBindingId()
    assert.equal(f.form.automation_case_id, 102)
    f.form.automation_case_id = 555; f.reset(); f.open(bindingSubject())
    assert.equal(f.form.automation_type, 0); assert.equal(f.form.automation_case_id, 101)
    f.open({ id: 22, bindings: [] }); assert.equal(f.form.automation_case_id, null)
  } finally { f.close() }
})

test('binding failure retains input and retry emits success only after acknowledged write', async () => {
  let fail = true; const writes = []
  const f = binding({ api: { postManualAutomationBind: async value => { writes.push(value); if (fail) throw Error('Rejected') } } })
  try {
    f.open(bindingSubject()); f.form.automation_case_id = 777
    await f.save(); assert.equal(f.visible.value, true); assert.equal(f.saveError.value, true)
    assert.equal(f.form.automation_case_id, 777); assert.equal(f.saving.value, false)
    assert.deepEqual(f.events, [])
    fail = false; await f.save()
    assert.equal(f.visible.value, false); assert.deepEqual(f.events, [['saved']])
    assert.deepEqual(writes[1], { case_id: 11, automation_type: 0, automation_case_id: 777 })
  } finally { f.close() }
})

test('binding rejects missing ID and blocks duplicate/cancel/open while saving', async () => {
  const pending = deferred(); let calls = 0
  const f = binding({ api: { postManualAutomationBind: async () => { ++calls; await pending.promise } } })
  try {
    f.open({ id: 11, bindings: [] }); await f.save(); assert.equal(calls, 0)
    f.form.automation_case_id = 22; const saving = f.save()
    assert.equal(f.canCancel(), false); await f.save(); f.open({ id: 33 })
    assert.equal(f.subject.value.id, 11); assert.equal(calls, 1)
    f.props.contextKey = 'other-role'
    assert.equal(f.visible.value, false); assert.equal(f.saving.value, true)
    f.open({ id: 33 }); assert.equal(f.visible.value, false)
    pending.resolve(); await saving
    assert.equal(f.saving.value, false); assert.deepEqual(f.events, [])
    f.open({ id: 33 }); assert.equal(f.subject.value.id, 33)
  } finally { f.close() }
})

test('plan payload whitelists fields, resolves cascades and clears unrelated scope references', () => {
  const f = plan()
  try {
    const { createLibraryPlanForm, libraryPlanPayload } = f.load('plan-form.ts')
    const source = { ...createLibraryPlanForm(), name: 'Example', project_product: [1, 2], scope_type: 0, requirement_version: 7, iteration: 8, update_time: 'forbidden' }
    const payload = libraryPlanPayload(source)
    assert.equal(payload.project_product, 2); assert.equal(payload.scope_type, 0)
    assert.equal(payload.requirement_version, 7); assert.equal(payload.iteration, null)
    assert.equal('id' in payload, false); assert.equal('update_time' in payload, false)
    source.scope_type = 1
    assert.equal(libraryPlanPayload(source).requirement_version, null)
    assert.equal(libraryPlanPayload(source).iteration, 8)
    source.scope_type = 2
    assert.equal(libraryPlanPayload(source).iteration, null)
    assert.equal(libraryPlanPayload(source).requirement_version, null)
  } finally { f.close() }
})

test('join plan opens immediately with local loading and fixes the originally selected IDs', async () => {
  const reading = deferred(), writes = []
  const f = plan({ api: { getFunctionalPlans: () => reading.promise, addFunctionalPlanCases: async value => writes.push(value) } })
  try {
    const source = selection(), opening = f.openJoin(source)
    assert.equal(f.visible.value, true); assert.equal(f.planLoading.value, true)
    source[0].id = 99; source.push({ id: 100, productId: 2, ownerId: 3 })
    reading.resolve({ data: [{ id: 55, name: 'Example plan' }] }); await opening
    assert.equal(f.planLoading.value, false); assert.deepEqual([...f.caseIds.value], [11, 12])
    f.joinForm.plan_id = 55; await f.save()
    assert.deepEqual(writes, [{ plan_id: 55, case_ids: [11, 12] }])
    assert.equal(f.visible.value, false)
  } finally { f.close() }
})

test('join plan option failure can retry, and write failure keeps the selected plan', async () => {
  let failRead = true, failWrite = true
  const f = plan({ api: {
    getFunctionalPlans: async () => { if (failRead) throw Error('Offline'); return { data: [{ id: 55, name: 'Example' }] } },
    addFunctionalPlanCases: async () => { if (failWrite) throw Error('Rejected') },
  } })
  try {
    await f.openJoin(selection()); assert.equal(f.planError.value, true); assert.equal(f.planLoading.value, false)
    failRead = false; await f.loadPlans(); assert.equal(f.planError.value, false)
    f.joinForm.plan_id = 55; await f.save()
    assert.equal(f.visible.value, true); assert.equal(f.saveError.value, true); assert.equal(f.joinForm.plan_id, 55)
    failWrite = false; await f.save(); assert.equal(f.visible.value, false)
  } finally { f.close() }
})

test('incompatible products are rejected and create without selected cases uses navigation defaults', async () => {
  const f = plan()
  try {
    await f.openJoin([]); assert.equal(f.visible.value, false)
    const mixed = [{ id: 1, productId: 2, ownerId: 3 }, { id: 2, productId: 4, ownerId: 3 }]
    await f.openJoin(mixed); assert.equal(f.visible.value, false)
    await f.openCreate(mixed); assert.equal(f.visible.value, false)
    await f.openCreate([])
    assert.equal(f.mode.value, 'create'); assert.equal(f.form.project_product, 9)
    assert.equal(f.form.owner, null); assert.deepEqual([...f.caseIds.value], [])
    f.reset(); await f.openCreate([{ id: 1, productId: 2, ownerId: 3 }, { id: 2, productId: '2', ownerId: 4 }])
    assert.equal(f.form.project_product, 2); assert.equal(f.form.owner, 3)
  } finally { f.close() }
})

test('requirement and iteration choices load independently and only failed region needs retry', async () => {
  const slow = deferred(); let requirementsFail = true
  const f = plan({ api: {
    getFunctionalRequirements: async () => { if (requirementsFail) throw Error('Offline'); return { data: [{ id: 7, name: 'Example requirement', version_no: 0 }] } },
    getFunctionalIterations: () => slow.promise,
  } })
  try {
    const opening = f.openCreate(selection()); await flush()
    assert.equal(f.visible.value, true); assert.equal(f.requirementError.value, true)
    assert.equal(f.requirementLoading.value, false); assert.equal(f.iterationLoading.value, true)
    requirementsFail = false; await f.loadRequirements()
    assert.equal(f.requirementError.value, false); assert.equal(f.iterationLoading.value, true)
    assert.equal(f.requirementOptions.value[0].label, 'Example requirement · V0')
    slow.resolve({ data: [{ id: 8, name: 'Example sprint', iteration_no: 'S1' }] }); await opening
    assert.equal(f.iterationLoading.value, false)
    assert.equal(f.iterationOptions.value[0].label, 'S1 Example sprint')
  } finally { f.close() }
})

test('product change clears dependent choices and old responses cannot stop new loading', async () => {
  const first = deferred(), second = deferred(); let requests = 0
  const f = plan({ api: { getFunctionalRequirements: () => ++requests === 1 ? first.promise : second.promise } })
  try {
    const opening = f.openCreate(selection())
    f.form.requirement_version = 7; f.form.iteration = 8; f.form.project_product = 4
    const changing = f.onProductChange()
    assert.equal(f.form.requirement_version, null); assert.equal(f.form.iteration, null)
    first.resolve({ data: [{ id: 7, name: 'Old', version_no: 1 }] }); await opening
    assert.equal(f.requirementLoading.value, true); assert.deepEqual([...f.requirementOptions.value], [])
    second.resolve({ data: [{ id: 9, name: 'Current', version_no: 2 }] }); await changing
    assert.equal(f.requirementLoading.value, false); assert.equal(f.requirementOptions.value[0].value, 9)
    f.form.scope_type = 1; f.form.requirement_version = 9; f.form.scope_ref = 'old'; f.onScopeChange()
    assert.equal(f.form.requirement_version, null); assert.equal(f.form.scope_ref, '')
  } finally { f.close() }
})

test('acknowledged creation is retained after association failure; retry does not create another plan', async () => {
  let createCount = 0, addCount = 0; const payloads = []
  const f = plan({ api: {
    postFunctionalPlan: async payload => { ++createCount; payloads.push(payload); return { data: { id: 55 } } },
    addFunctionalPlanCases: async payload => { ++addCount; payloads.push(payload); if (addCount === 1) throw Error('Rejected') },
  } })
  try {
    await f.openCreate(selection()); fill(f); await f.save()
    assert.equal(f.visible.value, true); assert.equal(f.createdPlanId.value, 55)
    assert.equal(f.saveError.value, true); assert.equal(f.saving.value, false)
    assert.equal(f.form.name, 'Example plan'); await f.save()
    assert.equal(createCount, 1); assert.equal(addCount, 2); assert.equal(f.visible.value, false)
    assert.deepEqual(payloads[1], { plan_id: 55, case_ids: [11, 12] })
    assert.deepEqual(payloads[2], payloads[1])
  } finally { f.close() }
})

test('create failure retains the form and permits retry, without association before successful creation', async () => {
  let fail = true, creates = 0, adds = 0
  const f = plan({ api: {
    postFunctionalPlan: async () => { ++creates; if (fail) throw Error('Rejected'); return { data: { id: 55 } } },
    addFunctionalPlanCases: async () => { ++adds },
  } })
  try {
    await f.openCreate(selection()); fill(f); await f.save()
    assert.equal(f.visible.value, true); assert.equal(f.createdPlanId.value, null)
    assert.equal(f.form.name, 'Example plan'); assert.equal(adds, 0)
    fail = false; await f.save(); assert.equal(creates, 2); assert.equal(adds, 1)
  } finally { f.close() }
})

test('plan create validates required scope, preserves zero type, and allows a plan with no cases', async () => {
  const writes = []; let adds = 0
  const f = plan({ api: { postFunctionalPlan: async value => { writes.push(value); return { data: { id: 55 } } }, addFunctionalPlanCases: async () => { ++adds } } })
  try {
    await f.openCreate([]); await f.save(); assert.equal(writes.length, 0)
    fill(f); f.form.requirement_version = null; await f.save(); assert.equal(writes.length, 0)
    f.form.requirement_version = 7; await f.save()
    assert.equal(writes[0].scope_type, 0); assert.equal(writes[0].project_product, 9)
    assert.equal(adds, 0); assert.equal(f.visible.value, false)
  } finally { f.close() }
})

test('context change during creation blocks subsequent association and keeps physical write lock', async () => {
  const pending = deferred(); let adds = 0, creates = 0
  const f = plan({ api: { postFunctionalPlan: async () => { ++creates; return pending.promise }, addFunctionalPlanCases: async () => { ++adds } } })
  try {
    await f.openCreate(selection()); fill(f); const saving = f.save()
    assert.equal(f.canCancel(), false); await f.save(); assert.equal(creates, 1)
    f.props.contextKey = 'new-environment'
    await f.openCreate([]); assert.equal(f.visible.value, false); assert.equal(f.saving.value, true)
    pending.resolve({ data: { id: 55 } }); await saving
    assert.equal(adds, 0); assert.equal(f.createdPlanId.value, null); assert.equal(f.saving.value, false)
    await f.openCreate([]); assert.equal(f.visible.value, true)
  } finally { f.close() }
})

for (const name of ['binding', 'plan']) {
  test(`${name} KeepAlive stop clears the window and ignores a pending write`, async () => {
    const hooks = {}, pending = deferred()
    const options = { modules: { vue: { ...vue, onDeactivated: fn => { hooks.stop = fn }, onActivated: fn => { hooks.start = fn }, onBeforeUnmount: fn => { hooks.unmount = fn } } },
      api: name === 'binding' ? { postManualAutomationBind: () => pending.promise } : { addFunctionalPlanCases: () => pending.promise },
    }
    const f = name === 'binding' ? binding(options) : plan(options)
    try {
      if (name === 'binding') f.open(bindingSubject())
      else { await f.openJoin(selection()); f.joinForm.plan_id = 55 }
      const saving = f.save(); hooks.stop()
      assert.equal(f.visible.value, false); assert.equal(f.saving.value, true)
      pending.resolve({ data: {} }); await saving
      assert.equal(f.saving.value, false); assert.equal(f.saveError.value, false)
      hooks.start()
      if (name === 'binding') f.open(bindingSubject())
      else await f.openJoin(selection())
      assert.equal(f.visible.value, true); hooks.unmount(); assert.equal(f.visible.value, false)
      assert.deepEqual(f.events, [])
    } finally { f.close() }
  })
}

test('closing pending plan reads cannot reopen the window or publish old options', async () => {
  const pending = deferred()
  const f = plan({ api: { getFunctionalPlans: () => pending.promise } })
  try {
    const opening = f.openJoin(selection()); f.reset()
    pending.resolve({ data: [{ id: 55, name: 'Old' }] }); await opening
    assert.equal(f.visible.value, false); assert.equal(f.mode.value, null)
    assert.deepEqual([...f.planOptions.value], []); assert.equal(f.planLoading.value, false)
    assert.equal(f.planError.value, false)
  } finally { f.close() }
})
