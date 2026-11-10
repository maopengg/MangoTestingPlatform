import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/defect')
const linked = { id: 1, case: 7, plan_case: null, case_no: 'CASE-7', case_title: 'Example', plan_id: null }
const record = (extra = {}) => ({ id: 11, defect_no: 'DEF-11', title: 'Example defect', status: 2, actual_result: 'Failure', project_product: { id: 2 }, module: { id: 3 }, requirement_version: 4,
  severity: 0, priority: 0, source_type: 0, defect_type: 0, resolution: 0, assignee: { id: 5 }, reporter: { id: 6, name: 'Reporter' },
  reproduce_steps: [{ sort: 8, action: 'Do', expected: 'Pass', actual: 'Failure' }], attachment_file_ids: [9], relations: [linked], ...extra })
const caseRow = (id = 7) => ({ id, case_no: `CASE-${id}`, title: `Case ${id}`, module_id: 3, precondition: 'Prepare', test_steps: [{ action: 'Act', expected: 'Pass' }], expected_result: 'Pass', actual_result: 'Observed' })
const seed = (extra = {}) => ({ projectProduct: 2, requirementVersion: 4, planId: null, caseIds: [7], planCaseIds: [], ...extra })
function fixture(api = {}) {
  const hooks = { stop: [], activate: [], unmount: [] }, writes = [], uploads = [], messages = []
  const f = harness('DefectEditorDrawer', 'open,openById,openFromRoute,loadDetail,loadCases,loadPlans,loadPlanCases,onFormProductChange,changePlan,save,reset,form,metadata,visible,saving,saveError,detailLoading,detailError,caseLoading,caseError,plansLoading,plansError,planCaseLoading,planCaseError,caseOptions,planOptions,planCaseOptions,libraryCaseRows,planCaseRows,attachmentFileList,onAttachmentChange,canCancel', {
    base, props: { contextKey: 'A', users: [] },
    api: {
      getManualCase: async () => ({ data: [caseRow()] }), getFunctionalPlans: async () => ({ data: [{ id: 8, name: 'Plan', environment: 'Example environment' }] }),
      getFunctionalPlanCases: async () => ({ data: [caseRow(10)] }), getFunctionalDefectDetail: async id => ({ data: record({ id }) }),
      postUserFile: async body => { uploads.push(body); return { data: { id: 20 + uploads.length } } },
      postFunctionalDefect: async body => { writes.push(body); return { data: { ...body, id: 11 } } },
      putFunctionalDefect: async body => { writes.push(body); return { data: { ...body } } }, ...api,
    }, modules: {
      vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['warning', 'success'].map(kind => [kind, value => messages.push([kind, value])])) },
    },
  })
  return { ...f, hooks, writes, uploads, messages, cleanup: () => { hooks.unmount.forEach(fn => fn()); f.close() } }
}
const file = name => ({ uid: name, name, file: new File(['Example'], name) })
function ready(f) { f.form.title = 'New defect'; f.form.actual_result = 'Failure'; f.form.project_product = 2 }

test('record mapping isolates steps, IDs and metadata, and payload excludes display/audit fields', async () => {
  const f = fixture()
  try {
    const source = record(); await f.open(source)
    f.form.reproduce_steps[0].action = 'Draft'; f.form.attachment_file_ids.push(20)
    assert.equal(source.reproduce_steps[0].action, 'Do'); assert.deepEqual(source.attachment_file_ids, [9])
    assert.equal(f.metadata.value.reporter_name, 'Reporter'); assert.equal(f.metadata.value.resolution, 0)
    await f.save(); const payload = f.writes[0]
    assert.equal(payload.project_product, 2); assert.equal(payload.severity, 0); assert.equal(payload.requirement_version, 4)
    assert.deepEqual(payload.reproduce_steps, [{ sort: 1, action: 'Draft', expected: 'Pass', actual: 'Failure' }])
    for (const field of ['reporter', 'relations', 'defect_no', 'status', 'resolution', 'create_time', 'source_plan_id']) assert.equal(field in payload, false)
    assert.equal(f.events[0][0], 'saved'); assert.equal(f.visible.value, false)
  } finally { f.cleanup() }
})

test('cancel/reopen discards all nested drafts and navigation defaults use real selection IDs', async () => {
  const f = fixture()
  try {
    await f.open(record()); f.form.title = 'Unsaved'; f.onAttachmentChange([file('old.txt')]); f.reset()
    await f.open(undefined, { projectProduct: 0, module: 0 })
    assert.equal(f.form.title, ''); assert.deepEqual(f.form.reproduce_steps, []); assert.deepEqual(f.form.case_ids, [])
    assert.equal(f.form.project_product, 0); assert.equal(f.form.module, 0); assert.equal(f.form.requirement_version, null)
    assert.deepEqual(f.attachmentFileList.value, [])
  } finally { f.cleanup() }
})

test('case and plan choices load independently, keep selected fallback labels and retry failed requests', async () => {
  const cases = deferred(), plans = deferred(); let calls = 0
  const f = fixture({ getManualCase: () => ++calls === 1 ? cases.promise : Promise.resolve({ data: [caseRow()] }), getFunctionalPlans: () => plans.promise })
  try {
    const opening = f.open(record({ relations: [linked, { id: 2, case: null, plan_case: 10, plan_id: 8, plan_name: 'Saved plan', case_no: 'CASE-10', case_title: 'Saved case' }] }))
    assert.equal(f.visible.value, true); assert.equal(f.caseLoading.value, true); assert.equal(f.plansLoading.value, true)
    assert.equal(f.caseOptions.value[0].label, 'CASE-7 Example')
    cases.reject(Error('Offline')); await flush()
    assert.equal(f.caseError.value, true); assert.equal(f.caseLoading.value, false); assert.equal(f.plansLoading.value, true)
    plans.resolve({ data: [] }); await opening
    assert.equal(f.planOptions.value[0].label, 'Saved plan'); assert.deepEqual(f.form.plan_case_ids, [10])
    await f.loadCases(); assert.equal(f.caseError.value, false); assert.equal(calls, 2)
  } finally { f.cleanup() }
})

test('product A to B to A ignores old choices and old finally cannot release fresh loading', async () => {
  const old = deferred(), fresh = deferred(); let calls = 0
  const f = fixture({ getManualCase: () => ++calls === 1 ? old.promise : fresh.promise })
  try {
    const opening = f.open(record()); f.form.project_product = 4; const b = f.onFormProductChange()
    f.form.project_product = 2; const a = f.onFormProductChange()
    assert.equal(f.form.module, null); assert.equal(f.form.requirement_version, null); assert.deepEqual(f.form.case_ids, [])
    old.resolve({ data: [caseRow(99)] }); await opening
    assert.equal(f.caseLoading.value, true); assert.deepEqual(f.libraryCaseRows.value, [])
    fresh.resolve({ data: [caseRow(7)] }); await Promise.all([a, b])
    assert.equal(f.caseLoading.value, false); assert.equal(f.libraryCaseRows.value[0].id, 7)
  } finally { f.cleanup() }
})

test('changing source plan rejects late rows and retry preserves newly selected plan case IDs', async () => {
  const old = deferred(), fresh = deferred(); let calls = 0
  const f = fixture({ getFunctionalPlanCases: () => ++calls === 1 ? old.promise : fresh.promise })
  try {
    await f.open(record()); f.form.source_plan_id = 8; const first = f.changePlan()
    f.form.plan_case_ids = [10]; f.form.source_plan_id = 9; const second = f.changePlan()
    assert.deepEqual(f.form.plan_case_ids, []); old.resolve({ data: [caseRow(99)] }); await first
    assert.equal(f.planCaseLoading.value, true); assert.deepEqual(f.planCaseRows.value, [])
    fresh.resolve({ data: [caseRow(12)] }); await second; f.form.plan_case_ids = [12]
    await f.loadPlanCases(false); assert.deepEqual(f.form.plan_case_ids, [12])
  } finally { f.cleanup() }
})

test('route seed fills plan snapshot and environment while preserving user-edited and intentionally cleared fields', async () => {
  const rows = deferred(), plans = deferred()
  const f = fixture({ getFunctionalPlanCases: () => rows.promise, getFunctionalPlans: () => plans.promise })
  try {
    const input = seed({ planId: 8, planCaseIds: [10], caseIds: [] }), opening = f.openFromRoute(input)
    input.planCaseIds.push(99); f.form.title = 'Typed'; f.form.title = ''; f.form.actual_result = 'Custom'
    rows.resolve({ data: [caseRow(10)] }); plans.resolve({ data: [{ id: 8, name: 'Plan', environment: 'Environment' }] }); await opening
    assert.equal(f.form.title, ''); assert.equal(f.form.actual_result, 'Custom'); assert.equal(f.form.environment, 'Environment')
    assert.deepEqual(f.form.plan_case_ids, [10]); assert.equal(f.form.precondition, 'Prepare'); assert.equal(f.form.reproduce_steps[0].action, 'Act')
    assert.equal(f.form.source_type, 0); assert.equal(f.form.requirement_version, 4)
  } finally { f.cleanup() }
})

test('detail loading has failure/retry feedback and an obsolete detail never replaces a reopened draft', async () => {
  const old = deferred(); let calls = 0
  const f = fixture({ getFunctionalDefectDetail: async () => { if (++calls === 1) throw Error('Offline'); if (calls === 2) return old.promise; return { data: record() } } })
  try {
    await f.openById(11); assert.equal(f.detailError.value, true); assert.equal(f.detailLoading.value, false)
    await f.save(); assert.equal(f.writes.length, 0)
    const retry = f.loadDetail(); assert.equal(f.detailLoading.value, true)
    await f.open(); f.form.title = 'New draft'; old.resolve({ data: record({ title: 'Stale detail' }) }); await retry
    assert.equal(f.form.title, 'New draft'); assert.equal(f.form.id, null)
    await f.openById(11); assert.equal(f.detailError.value, false); assert.equal(f.form.id, 11)
  } finally { f.cleanup() }
})

test('partial attachment failure waits for the whole batch and retries only failed files', async () => {
  const slow = deferred(), uploads = []; let fails = true
  const f = fixture({ postUserFile: async body => { const name = body.get('test_file').name; uploads.push(name); if (name === 'failed.txt' && fails) throw Error('Rejected'); return name === 'slow.txt' ? slow.promise : { data: { id: 22 } } } })
  try {
    await f.open(); ready(f); f.onAttachmentChange([file('failed.txt'), file('slow.txt')]); const saving = f.save(); await flush()
    assert.equal(f.saving.value, true); assert.equal(f.canCancel(), false); assert.equal(f.writes.length, 0)
    await f.save(); assert.equal(uploads.length, 2)
    slow.resolve({ data: { id: 21 } }); await saving
    assert.equal(f.saveError.value, true); assert.deepEqual(f.form.attachment_file_ids, [21]); assert.equal(f.attachmentFileList.value.length, 1)
    assert.equal(f.attachmentFileList.value[0].uid, 'failed.txt'); assert.equal(f.writes.length, 0)
    fails = false; await f.save()
    assert.deepEqual(uploads, ['failed.txt', 'slow.txt', 'failed.txt']); assert.deepEqual(f.writes[0].attachment_file_ids, [21, 22])
  } finally { f.cleanup() }
})

test('save snapshots editable fields before uploading and success cannot be repeated while in flight', async () => {
  const pending = deferred(), f = fixture({ postUserFile: () => pending.promise })
  try {
    await f.open(record()); f.onAttachmentChange([file('example.txt')]); const saving = f.save()
    f.form.title = 'Later'; f.form.reproduce_steps[0].action = 'Later'; f.form.case_ids.push(99)
    pending.resolve({ data: { id: 20 } }); await saving
    assert.equal(f.writes[0].title, 'Example defect'); assert.equal(f.writes[0].reproduce_steps[0].action, 'Do'); assert.deepEqual(f.writes[0].case_ids, [7])
    assert.deepEqual(f.writes[0].attachment_file_ids, [9, 20]); assert.equal(f.visible.value, false)
  } finally { f.cleanup() }
})

test('a failed defect write preserves successful uploads and retry does not upload them again', async () => {
  let fail = true; const writes = []
  const f = fixture({ postFunctionalDefect: async body => { writes.push(body); if (fail) throw Error('Rejected'); return { data: { id: 11 } } } })
  try {
    await f.open(); ready(f); f.onAttachmentChange([file('example.txt')]); await f.save()
    assert.equal(f.saveError.value, true); assert.equal(f.visible.value, true); assert.equal(f.form.title, 'New defect')
    assert.equal(f.uploads.length, 1); assert.deepEqual(f.form.attachment_file_ids, [21]); assert.deepEqual(f.attachmentFileList.value, [])
    fail = false; await f.save(); assert.equal(f.uploads.length, 1); assert.equal(writes.length, 2); assert.equal(f.events.length, 1)
  } finally { f.cleanup() }
})

test('context invalidation during upload prevents submitting a defect or mutating a new draft', async () => {
  const pending = deferred(), f = fixture({ postUserFile: () => pending.promise })
  try {
    await f.open(); ready(f); f.onAttachmentChange([file('example.txt')]); const saving = f.save()
    f.props.contextKey = 'B'; f.props.contextKey = 'A'; await f.open(record())
    assert.equal(f.visible.value, false); assert.equal(f.saving.value, true)
    pending.resolve({ data: { id: 20 } }); await saving
    assert.equal(f.writes.length, 0); assert.deepEqual(f.form.attachment_file_ids, []); assert.deepEqual(f.events, [])
    await f.open(); assert.equal(f.visible.value, true)
  } finally { f.cleanup() }
})

test('deactivation suppresses a late save and activation/unmount reset drafts without releasing a physical lock early', async () => {
  const pending = deferred(), f = fixture({ putFunctionalDefect: () => pending.promise })
  try {
    await f.open(record()); const saving = f.save(); await flush()
    f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await f.open()
    assert.equal(f.visible.value, false); assert.equal(f.saving.value, true)
    assert.equal(f.exposed.isSaving(11), true)
    pending.reject(Error('Late rejection')); await saving
    assert.equal(f.saveError.value, false); assert.deepEqual(f.events, [])
    assert.equal(f.exposed.isSaving(11), false)
    await f.open(); assert.equal(f.visible.value, true)
    f.hooks.unmount.forEach(fn => fn()); assert.equal(f.visible.value, false)
  } finally { f.cleanup() }
})

test('malformed upload and mismatched save acknowledgements retain retryable input', async () => {
  const f = fixture({ postUserFile: async () => ({ data: {} }), putFunctionalDefect: async () => ({ data: { id: 999 } }) })
  try {
    await f.open(record()); f.onAttachmentChange([file('example.txt')]); await f.save()
    assert.equal(f.saveError.value, true); assert.equal(f.attachmentFileList.value.length, 1)
    f.onAttachmentChange([]); await f.save(); assert.equal(f.saveError.value, true); assert.equal(f.visible.value, true); assert.deepEqual(f.events, [])
  } finally { f.cleanup() }
})

test('form helpers normalize real product leaves, preserve zero values and reject incomplete route seeds', () => {
  const f = fixture()
  try {
    const { createDefectForm, defectPayload, defectRouteSeed } = f.load('form.ts')
    const first = createDefectForm(), second = createDefectForm(); first.reproduce_steps.push({ sort: 1, action: 'A', expected: '', actual: '' })
    assert.deepEqual(second.reproduce_steps, [])
    first.project_product = [1, 2]; first.assignee = 0; first.source_type = 0
    const payload = defectPayload(first); assert.equal(payload.project_product, 2); assert.equal(payload.assignee, 0); assert.equal('id' in payload, false)
    assert.equal(defectRouteSeed({ project_product: 2 }), null)
    assert.deepEqual(defectRouteSeed({ project_product: '2', plan_id: '8', plan_case_ids: '10,10,12' }), { projectProduct: 2, planId: 8, requirementVersion: null, planCaseIds: [10, 12], caseIds: [] })
  } finally { f.cleanup() }
})
