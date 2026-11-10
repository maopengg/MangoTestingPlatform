import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/plan')
const caseRow = (fields = {}) => ({ id: 10, plan: 1, title: 'Example case', case_no: 'CASE-10', result: 0, defects: [], ...fields })
const plan = (id = 1, fields = {}) => ({ id, name: `Plan ${id}`, status: 0, scope_type: 2, scope_ref: 'Example scope',
  project_product: { id: 2, name: 'Example product' }, execution_stats: { total: 1, executed: 0, pass_rate: 0 },
  cases: [caseRow({ plan: id })], ...fields })
const settle = async () => { await flush(); await new Promise(resolve => setImmediate(resolve)); await flush() }
function setup(overrides = {}) {
  const route = vue.reactive({ path: '/functional-test/plan/details', fullPath: '/functional-test/plan/details?id=1', query: { id: '1' } })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'example-test-token', selected_environment: 1 })
  const hooks = { mount: [], stop: [], activate: [], unmount: [] }, calls = [], dialogs = [], notifications = [], navigation = []
  const api = {
    getFunctionalPlanDetail: async id => ({ data: plan(id) }), getUserName: async () => ({ data: [{ key: 4, title: 'Example owner' }] }),
    startFunctionalPlan: async id => ({ data: { id, status: 2 } }), finishFunctionalPlan: async id => ({ data: { id, status: 3 } }),
    removeFunctionalPlanCases: async () => ({ data: { count: 1 } }),
    batchFunctionalPlanResult: async body => ({ data: body.plan_case_ids.map(id => caseRow({ id, plan: body.plan_id, result: body.result })) }),
    putFunctionalPlanCase: async body => ({ data: caseRow(body) }), ...overrides.api,
  }
  const f = harness('details', 'loadAll,loadDetail,loadUsers,loadEnums,plan,planId,loading,readError,usersError,enumsError,usersLoading,users,gridEditable,canOperate,columns,selectedPlanCases,onSelectionChange,execution,savePlanCase,caseSaving,casePicker,defectRelation,openCasePicker,openBindDefect,openUnbindDefect,onRelatedChanged,createDefect,goBack,navigating,navigationError,selectedDefectOptions', {
    base, filename: path.join(base, 'details.vue'),
    api: Object.fromEntries(Object.entries(api).map(([name, fn]) => [name, (...args) => { calls.push([name, ...args]); return fn(...args) }])),
    modules: {
      vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.stop.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      'vue-router': { useRoute: () => route, useRouter: () => ({ push: async target => { navigation.push(target); return overrides.push?.(target) }, back: async () => { navigation.push('back'); return overrides.back?.() } }) },
      '@/store/modules/user': { default: () => user },
      '@/components/table/functional-case-grid': { readGridRecord: row => row },
      '@/store/modules/get-enum': { useEnum: () => ({ colors: {}, getEnum: overrides.getEnum || (async () => {}), functional_test_result: [{ key: 0, title: 'Unexecuted' }, { key: 1, title: 'Passed' }] }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(kind => [kind, message => notifications.push([kind, message])])), Modal: { warning(config) { const handle = { closed: false, close() { handle.closed = true } }; dialogs.push({ config, handle }); return handle } } },
    },
  })
  return { ...f, route, user, hooks, calls, dialogs, notifications, navigation, cleanup() { hooks.unmount.forEach(fn => fn()); f.close() } }
}
test('detail is independent of slow users and failing enums, with separate local retries', async () => {
  const pending = deferred(), f = setup({ api: { getUserName: () => pending.promise }, getEnum: async () => { throw Error('Offline') } })
  try {
    const load = f.loadAll(); await settle()
    assert.equal(f.plan.value.id, 1); assert.equal(f.loading.value, false); assert.equal(f.usersLoading.value, true); assert.equal(f.enumsError.value, true)
    assert.equal(f.columns.value.find(item => item.field === 'result').editable, false)
    pending.resolve({ data: [{ key: 4, title: 'Owner' }] }); await load
    assert.equal(f.users.value[0].title, 'Owner'); assert.equal(f.usersLoading.value, false)
  } finally { f.cleanup() }
})
test('failed details retain current data, end loading and allow retry; wrong scopes are rejected', async () => {
  let response = plan(), f = setup({ api: { getFunctionalPlanDetail: async () => { if (response instanceof Error) throw response; return { data: response } } } })
  try {
    await f.loadAll(); const original = f.plan.value
    for (const invalid of [Error('Offline'), plan(2), plan(1, { cases: [caseRow({ plan: 2 })] }), {}]) {
      response = invalid; assert.equal(await f.loadDetail(), false); assert.equal(f.plan.value, original); assert.equal(f.readError.value, true); assert.equal(f.loading.value, false)
    }
    response = plan(); assert.equal(await f.loadDetail(), true); assert.equal(f.readError.value, false)
  } finally { f.cleanup() }
})
test('latest read wins even when an older detail response arrives last', async () => {
  const first = deferred(), second = deferred(); let count = 0
  const f = setup({ api: { getFunctionalPlanDetail: () => (++count === 1 ? first : second).promise } })
  try {
    const a = f.loadDetail(), b = f.loadDetail(); second.resolve({ data: plan(1, { name: 'Latest' }) }); await b
    first.resolve({ data: plan(1, { name: 'Old' }) }); await a; assert.equal(f.plan.value.name, 'Latest')
  } finally { f.cleanup() }
})
test('invalid and other-route entries never request a plan', async () => {
  const f = setup()
  try {
    for (const value of ['', '0', '-1', '1.1', 'Infinity', ['1']]) { f.route.query.id = value; await f.loadAll(); assert.equal(f.planId.value, null) }
    f.route.query.id = '1'; f.route.path = '/other'; await f.loadAll(); assert.deepEqual(f.calls, [])
  } finally { f.cleanup() }
})
for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`${field} A-B-A invalidates old reads and selection`, async () => {
    const pending = deferred(), f = setup({ api: { getFunctionalPlanDetail: () => pending.promise } })
    try {
      const read = f.loadDetail(), original = f.user[field]
      f.user[field] = field === 'token' ? 'example-other-token' : 2; f.user[field] = original
      pending.resolve({ data: plan() }); await read
      assert.equal(f.plan.value, null); assert.deepEqual(f.selectedPlanCases.value, []); assert.equal(f.loading.value, false)
    } finally { f.cleanup() }
  })
}
test('mount/activate do not duplicate reads; changed IDs and KeepAlive restore load fresh data', async () => {
  const f = setup()
  try {
    f.hooks.mount.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await settle()
    assert.equal(f.calls.filter(([name]) => name === 'getFunctionalPlanDetail').length, 1)
    f.route.query.id = '2'; f.route.fullPath = '/functional-test/plan/details?id=2'; await settle(); assert.equal(f.plan.value.id, 2)
    f.hooks.stop.forEach(fn => fn()); assert.equal(f.plan.value, null)
    f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(f.plan.value.id, 2)
    f.hooks.unmount.forEach(fn => fn()); const before = f.calls.length; await f.loadAll(); assert.equal(f.calls.length, before)
  } finally { f.cleanup() }
})
test('selection accepts only current owned rows and supplies copied targets to relation windows', async () => {
  const f = setup(), opened = []
  try {
    await f.loadAll(); const own = f.plan.value.cases[0]
    f.onSelectionChange([own, caseRow({ id: 99 })]); assert.deepEqual(f.selectedPlanCases.value, [own])
    f.defectRelation.value = { open: (...args) => opened.push(args), isSaving: () => false, isOpen: () => false }
    f.openBindDefect(); assert.deepEqual(opened, [['bind', [10]]])
  } finally { f.cleanup() }
})
test('saving cells captures finite payload and prevents a concurrent plan execution', async () => {
  const pending = deferred(), f = setup({ api: { putFunctionalPlanCase: () => pending.promise } })
  try {
    await f.loadAll(); const row = f.plan.value.cases[0]
    const save = f.savePlanCase({ row, field: 'title', changes: { title: 'Edited' }, displayChanges: {}, oldValues: {} }); await settle()
    assert.equal(f.caseSaving.value, true); f.execution.openStart(); assert.equal(f.execution.startVisible.value, false)
    pending.resolve({ data: caseRow({ title: 'Edited' }) }); await save; assert.equal(row.title, 'Edited')
  } finally { f.cleanup() }
})
test('refresh requested during a cell write is deferred until the physical queue finishes', async () => {
  const pending = deferred(), f = setup({ api: { putFunctionalPlanCase: () => pending.promise } })
  try {
    await f.loadAll(); const row = f.plan.value.cases[0]
    const save = f.savePlanCase({ row, field: 'title', changes: { title: 'Edited' }, displayChanges: {}, oldValues: {} }); await settle()
    assert.equal(await f.loadDetail(), false); assert.equal(f.calls.filter(([name]) => name === 'getFunctionalPlanDetail').length, 1)
    pending.resolve({ data: caseRow({ title: 'Edited' }) }); await save; await settle()
    assert.equal(f.calls.filter(([name]) => name === 'getFunctionalPlanDetail').length, 2)
  } finally { f.cleanup() }
})
test('detail loading rejects cell writes rather than letting stale reads replace them', async () => {
  let hold = false; const pending = deferred(), f = setup({ api: { getFunctionalPlanDetail: () => hold ? pending.promise : Promise.resolve({ data: plan() }) } })
  try {
    await f.loadAll(); const row = f.plan.value.cases[0]; hold = true; const read = f.loadDetail()
    await f.savePlanCase({ row, field: 'title', changes: { title: 'Edited' }, displayChanges: {}, oldValues: {} })
    assert.equal(f.calls.some(([name]) => name === 'putFunctionalPlanCase'), false)
    pending.resolve({ data: plan() }); await read
  } finally { f.cleanup() }
})
test('window openness blocks grid edits; its post-write refresh waits for its physical lock', async () => {
  const f = setup(), open = vue.ref(true), writing = vue.ref(true)
  try {
    await f.loadAll(); f.casePicker.value = { open() {}, isOpen: () => open.value, isSaving: () => writing.value }
    assert.equal(f.gridEditable.value, false); f.onRelatedChanged(1)
    assert.equal(f.calls.filter(([name]) => name === 'getFunctionalPlanDetail').length, 1)
    open.value = false; writing.value = false; await settle()
    assert.equal(f.calls.filter(([name]) => name === 'getFunctionalPlanDetail').length, 2)
  } finally { f.cleanup() }
})
test('start dialog resets option, captures target, prevents duplicate writes and updates status before a failing refresh', async () => {
  const pending = deferred(); let failRead = false
  const f = setup({ api: { getFunctionalPlanDetail: async () => { if (failRead) throw Error('Offline'); return { data: plan(1, { requirement_version: { requirement_name: 'Requirement', version_no: 1 } }) } }, startFunctionalPlan: () => pending.promise } })
  try {
    await f.loadAll(); f.execution.openStart(); assert.equal(f.execution.startForm.update_requirement_status, true)
    f.execution.cancelStart(); f.execution.openStart(); f.execution.startForm.update_requirement_status = false
    const start = f.execution.start(); await f.execution.start(); assert.equal(f.execution.canCancel(), false)
    assert.deepEqual(f.calls.filter(([name]) => name === 'startFunctionalPlan'), [['startFunctionalPlan', 1, false]])
    failRead = true; pending.resolve({ data: { id: 1, status: 2 } }); await start; await settle()
    assert.equal(f.execution.startVisible.value, false); assert.equal(f.execution.error.value, false); assert.equal(f.plan.value.status, 2); assert.equal(f.readError.value, true)
  } finally { f.cleanup() }
})
test('failed start keeps the dialog and allows retry; wrong acknowledgements never close it', async () => {
  let data = null, f = setup({ api: { startFunctionalPlan: async () => ({ data }) } })
  try {
    await f.loadAll(); f.execution.openStart(); await f.execution.start()
    assert.equal(f.execution.error.value, true); assert.equal(f.execution.startVisible.value, true)
    data = { id: 99, status: 2 }; await f.execution.start(); assert.equal(f.execution.startVisible.value, true)
    data = { id: 1, status: 2 }; await f.execution.start(); assert.equal(f.execution.startVisible.value, false)
  } finally { f.cleanup() }
})
test('remove confirmation captures selected IDs, failure retains selection and confirm supports retry', async () => {
  let fail = true, f = setup({ api: { removeFunctionalPlanCases: async () => { if (fail) throw Error('Offline'); return { data: { count: 1 } } } } })
  try {
    await f.loadAll(); f.onSelectionChange(f.plan.value.cases); f.execution.remove(); f.onSelectionChange([]); f.execution.remove()
    assert.equal(f.dialogs.length, 1); assert.equal(await f.dialogs[0].config.onBeforeOk(), false)
    fail = false; assert.equal(await f.dialogs[0].config.onBeforeOk(), true)
    assert.deepEqual(f.calls.filter(([name]) => name === 'removeFunctionalPlanCases').map(([, body]) => body), [{ plan_id: 1, plan_case_ids: [10] }, { plan_id: 1, plan_case_ids: [10] }])
    assert.equal(f.dialogs[0].handle.closed, true)
  } finally { f.cleanup() }
})
test('finish confirmation includes outstanding defects and preserves confirmed read-only status when refresh fails', async () => {
  let failRead = false, f = setup({ api: { getFunctionalPlanDetail: async () => { if (failRead) throw Error('Offline'); return { data: plan(1, { status: 2, unlinked_failed_count: 1 }) } } } })
  try {
    await f.loadAll(); f.execution.finish(); assert.match(f.dialogs[0].config.content, /1 条/)
    failRead = true; assert.equal(await f.dialogs[0].config.onBeforeOk(), true); await settle()
    assert.equal(f.plan.value.status, 3); assert.equal(f.gridEditable.value, false); assert.equal(f.readError.value, true)
  } finally { f.cleanup() }
})
test('batch result captures selected cases, rejects duplicate and cross-scope results and preserves owned selection on failure', async () => {
  const pending = deferred(), f = setup({ api: { getFunctionalPlanDetail: async () => ({ data: plan(1, { status: 2 }) }), batchFunctionalPlanResult: () => pending.promise } })
  try {
    await f.loadAll(); f.onSelectionChange(f.plan.value.cases); const batch = f.execution.batch(2); await f.execution.batch(1)
    assert.equal(f.execution.batchResult.value, 2)
    assert.equal(f.calls.filter(([name]) => name === 'batchFunctionalPlanResult').length, 1)
    pending.resolve({ data: [caseRow({ plan: 2, result: 2 })] }); assert.equal(await batch, false)
    assert.equal(f.execution.error.value, true); assert.equal(f.selectedPlanCases.value.length, 1)
  } finally { f.cleanup() }
})
test('successful batch results remain visible when the follow-up detail read fails', async () => {
  let fail = false, f = setup({ api: { getFunctionalPlanDetail: async () => { if (fail) throw Error('Offline'); return { data: plan(1, { status: 2 }) } } } })
  try {
    await f.loadAll(); f.onSelectionChange(f.plan.value.cases); fail = true
    assert.equal(await f.execution.batch(2), true); await settle()
    assert.equal(f.plan.value.cases[0].result, 2); assert.equal(f.readError.value, true); assert.equal(f.execution.error.value, false)
    assert.equal(f.execution.batchResult.value, null); assert.deepEqual(f.selectedPlanCases.value, [])
  } finally { f.cleanup() }
})
for (const scope of ['deactivate', 'unmount', 'identity']) {
  test(`${scope} during execution discards late acknowledgements and keeps its physical lock until completion`, async () => {
    const pending = deferred(), f = setup({ api: { startFunctionalPlan: () => pending.promise } })
    try {
      f.hooks.mount.forEach(fn => fn()); await settle(); f.execution.openStart(); const starting = f.execution.start()
      if (scope === 'deactivate') { f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()) }
      else if (scope === 'unmount') f.hooks.unmount.forEach(fn => fn())
      else { f.user.roleId = 2; f.user.roleId = 1 }
      assert.equal(f.execution.busy.value, true); assert.equal(f.execution.startVisible.value, false)
      pending.reject(Error('Old failure')); await starting; await settle()
      assert.equal(f.execution.error.value, false); assert.equal(f.execution.busy.value, false); assert.deepEqual(f.notifications, [])
      assert.equal(f.plan.value === null, scope === 'unmount')
    } finally { f.cleanup() }
  })
}
test('context changes during execution suppress old success and recover a deferred new plan read', async () => {
  const pending = deferred(), f = setup({ api: { startFunctionalPlan: () => pending.promise } })
  try {
    f.hooks.mount.forEach(fn => fn()); await settle(); f.execution.openStart(); const starting = f.execution.start()
    f.route.query.id = '2'; f.route.fullPath = '/functional-test/plan/details?id=2'; await settle()
    assert.equal(f.plan.value, null); assert.equal(f.execution.busy.value, true); assert.equal(f.execution.startVisible.value, false)
    pending.resolve({ data: { id: 1, status: 2 } }); await starting; await settle()
    assert.equal(f.plan.value.id, 2); assert.deepEqual(f.notifications, [])
  } finally { f.cleanup() }
})
test('completed plans remain read-only for cells and execution while defect relationships remain available', async () => {
  const f = setup({ api: { getFunctionalPlanDetail: async () => ({ data: plan(1, { status: 3, cases: [caseRow({ result: 2 })] }) }) } }), opened = []
  try {
    await f.loadAll(); assert.equal(f.gridEditable.value, false); f.execution.openStart(); f.execution.finish(); await f.execution.batch(1)
    assert.equal(f.execution.startVisible.value, false); assert.equal(f.dialogs.length, 0)
    f.defectRelation.value = { open: (...args) => opened.push(args), isSaving: () => false, isOpen: () => false }
    f.onSelectionChange(f.plan.value.cases); f.openBindDefect(); assert.deepEqual(opened[0], ['bind', [10]])
  } finally { f.cleanup() }
})
test('defect navigation keeps original query protocol, deduplicates and supports failure retry', async () => {
  const pending = deferred(), f = setup({ api: { getFunctionalPlanDetail: async () => ({ data: plan(1, { cases: [caseRow({ result: 2 })] }) }) }, push: () => pending.promise })
  try {
    await f.loadAll(); f.onSelectionChange(f.plan.value.cases); const nav = f.createDefect(); await f.createDefect()
    assert.equal(f.navigation.length, 1); assert.deepEqual(f.navigation[0], { path: '/functional-test/defect/index', query: { plan_id: 1, plan_case_ids: '10', project_product: 2 } })
    pending.reject(Error('Chunk offline')); await nav; assert.equal(f.navigationError.value, true); assert.equal(f.navigating.value, null)
  } finally { f.cleanup() }
})
