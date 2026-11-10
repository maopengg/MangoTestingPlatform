import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/iteration/details')
const suite = (fields = {}) => ({ id: 11, requirement_name: 'Example requirement', version_no: 2, status: 3, update_time: '2026-11-07 10:00:00', development_owner: { id: 4, name: 'Example developer' }, owner: null, ...fields })
const detail = (id = 1) => ({ id, name: `Iteration ${id}`, status: 1, owner: null, start_date: '2026-11-01', end_date: '2026-11-15' })
const gantt = (id = 1) => ({ iteration: detail(id), today: '2026-11-07', summary: { requirement_count: 1 }, groups: [{ owner_id: 4, owner_name: 'Example developer', items: [{ id: 'requirement-11', suite_id: 11, requirement_name: 'Example requirement', status: 3 }] }] })
function setup(overrides = {}) {
  const route = vue.reactive({ path: '/functional-test/iteration/details', fullPath: '/functional-test/iteration/details?id=1', query: { id: '1' } })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'example-test-token', selected_environment: 1 })
  const hooks = { mount: [], stop: [], activate: [], unmount: [] }, requests = [], writes = [], dialogs = [], messages = []
  const api = {
    getFunctionalIterationDetail: async id => ({ data: detail(id) }),
    getManualSuite: async () => ({ data: [suite()] }),
    getFunctionalIterationGantt: async body => ({ data: gantt(body.iteration_id) }),
    getFunctionalIterationBoard: async id => ({ data: { iteration_id: id, columns: [{ status: 3, title: 'Developing', items: [suite()] }, { status: 4, title: 'Pending', items: [] }, { status: 6, title: 'Completed', items: [] }] } }),
    getRelatedFunctionalPlans: async () => ({ data: [{ id: 21, name: 'Example plan', owner: null }] }),
    getRelatedFunctionalDefects: async () => ({ data: [{ id: 31, defect_no: 'DEF-31', title: 'Example defect', assignee: null }] }),
    getFunctionalIterationCases: async () => ({ data: [], totalSize: 0 }),
    getUserName: async () => ({ data: [{ key: 4, title: 'Example developer' }] }),
    transitionManualSuiteStatus: async body => ({ data: { suite: suite({ id: body.id, status: body.status }), warnings: [] } }),
    confirmManualSuiteSubmit: async id => ({ data: suite({ id, status: 4 }) }),
    ...overrides.api,
  }
  const wrappedApi = Object.fromEntries(Object.entries(api).map(([key, fn]) => [key, async body => {
    (key === 'transitionManualSuiteStatus' || key === 'confirmManualSuiteSubmit' ? writes : requests).push([key, body])
    return fn(body)
  }]))
  function confirm(config) { const handle = { close() { config.onClose?.() } }; dialogs.push({ config, handle }); return handle }
  const enums = { colors: {}, getEnum: overrides.getEnum ?? (async () => {}) }
  const f = harness('index', 'loadAll,regions,regionErrors,iteration,suites,boardColumns,ganttData,iterationId,iterationCaseTotal,iterationCaseColumns,userOptions,gridContextKey,scheduleDialog,openGanttSchedule,openSchedule,moveRequirement,cancelRequirement,confirmSubmit,mutations,saveState,overviewVisible,openOverview,onScheduleSaved,isBusy', {
    base, api: wrappedApi,
    modules: {
      vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.stop.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      'vue-router': { useRoute: () => route, useRouter: () => ({ push: async () => {}, back() {} }) },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => enums },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error'].map(key => [key, value => messages.push([key, value])])), Modal: { confirm, warning: confirm } },
    },
  })
  return { ...f, route, user, hooks, requests, writes, dialogs, messages, cleanup: () => { hooks.unmount.forEach(fn => fn()); f.close() } }
}
const settle = async () => { await flush(); await new Promise(resolve => setImmediate(resolve)); await flush() }

test('independent regions display successes without waiting for a slow region or failed enums/users', async () => {
  const slow = deferred(), f = setup({ api: { getFunctionalIterationGantt: () => slow.promise, getUserName: async () => { throw Error('Offline') } }, getEnum: async () => { throw Error('Enum failed') } })
  try {
    const loading = f.loadAll(); await settle()
    assert.equal(f.iteration.value.id, 1); assert.equal(f.suites.value.length, 1); assert.equal(f.boardColumns.value[0].items.length, 1)
    assert.equal(f.regions.detail.loading.value, false); assert.equal(f.regions.gantt.loading.value, true)
    assert.equal(f.regions.users.error.value, true); assert.equal(f.regions.enums.error.value, true)
    slow.resolve({ data: gantt() }); await loading
    assert.equal(f.ganttData.value.groups.length, 1); assert.equal(f.regions.gantt.loading.value, false)
  } finally { f.cleanup() }
})

test('region read failure retains current data, closes loading and has an independent retry', async () => {
  let fail = false, f = setup({ api: { getRelatedFunctionalPlans: async () => { if (fail) throw Error('Offline'); return { data: [{ id: 21, name: 'Example plan' }] } } } })
  try {
    await f.loadAll(); const rows = f.regions.plans.data.value; fail = true
    assert.equal(await f.regions.plans.load(), false); assert.equal(f.regions.plans.error.value, true)
    assert.equal(f.regions.plans.data.value, rows); assert.equal(f.regions.plans.loading.value, false)
    const before = f.requests.length; fail = false; await f.regions.plans.load()
    assert.equal(f.requests.length, before + 1); assert.equal(f.regions.plans.error.value, false)
  } finally { f.cleanup() }
})

test('latest region request wins even when older response arrives last', async () => {
  const first = deferred(), second = deferred(); let count = 0
  const f = setup({ api: { getFunctionalIterationDetail: () => (++count === 1 ? first : second).promise } })
  try {
    const a = f.regions.detail.load(), b = f.regions.detail.load()
    second.resolve({ data: { ...detail(), name: 'Latest' } }); await b
    first.resolve({ data: { ...detail(), name: 'Old' } }); await a
    assert.equal(f.iteration.value.name, 'Latest'); assert.equal(f.regions.detail.loading.value, false)
  } finally { f.cleanup() }
})

for (const field of ['userId', 'roleId', 'selected_environment', 'token']) {
  test(`identity change in ${field} clears rows and ignores A to B to A responses`, async () => {
    const pending = deferred(), f = setup({ api: { getManualSuite: () => pending.promise } })
    try {
      const reading = f.loadAll(); await settle(); assert.equal(f.iteration.value.id, 1)
      const previous = f.user[field]; f.user[field] = field === 'token' ? 'example-other-token' : 2; f.user[field] = previous
      assert.equal(f.iteration.value, null); assert.deepEqual(f.boardColumns.value, [])
      pending.resolve({ data: [suite()] }); await reading
      assert.deepEqual(f.suites.value, []); assert.equal(f.regions.suites.loading.value, false)
    } finally { f.cleanup() }
  })
}

test('mount, deactivate and reactivate refresh once, suppress stale failures, and stop after unmount', async () => {
  const pending = deferred(); let first = true
  const f = setup({ api: { getManualSuite: async () => { if (first) { first = false; return pending.promise } return { data: [suite()] } } } })
  try {
    f.hooks.mount.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await settle()
    assert.equal(f.requests.filter(([key]) => key === 'getManualSuite').length, 1)
    f.hooks.stop.forEach(fn => fn()); pending.reject(Error('Late')); await settle()
    assert.equal(f.regions.suites.error.value, false); assert.deepEqual(f.suites.value, [])
    f.hooks.activate.forEach(fn => fn()); await settle()
    assert.equal(f.suites.value.length, 1)
    f.hooks.unmount.forEach(fn => fn()); const before = f.requests.length; await f.loadAll()
    assert.equal(f.requests.length, before)
  } finally { f.cleanup() }
})

test('invalid route IDs or a different route never initiate business requests', async () => {
  const f = setup()
  try {
    for (const id of ['', '0', '-1', '1.5', 'Infinity', ['1', '2']]) { f.route.query.id = id; await f.loadAll(); assert.equal(f.iterationId.value, null) }
    f.route.query.id = '1'; f.route.path = '/functional-test/plan/details'; await f.loadAll()
    assert.deepEqual(f.requests, [])
  } finally { f.cleanup() }
})

test('route switch after mount loads the new iteration and clears old opened windows', async () => {
  const f = setup()
  try {
    f.hooks.mount.forEach(fn => fn()); await settle()
    f.openOverview(f.suites.value[0]); assert.equal(f.overviewVisible.value, true)
    f.route.query.id = '2'; f.route.fullPath = '/functional-test/iteration/details?id=2'; await settle()
    assert.equal(f.overviewVisible.value, false); assert.equal(f.iteration.value.id, 2)
  } finally { f.cleanup() }
})

test('invalid or wrong-scope responses are region errors rather than successful empty data', async () => {
  const f = setup({ api: { getFunctionalIterationDetail: async () => ({ data: detail(2) }), getFunctionalIterationBoard: async () => ({ data: { iteration_id: 2, columns: [] } }), getManualSuite: async () => ({ data: {} }) } })
  try {
    await f.loadAll(); assert.equal(f.regions.detail.error.value, true); assert.equal(f.regions.board.error.value, true); assert.equal(f.regions.suites.error.value, true)
    assert.equal(f.regions.gantt.error.value, false); assert.equal(f.iterationCaseTotal.value, 0)
  } finally { f.cleanup() }
})

test('gantt string item identity opens the numeric suite_id and rejects stale items', async () => {
  const opened = [], f = setup()
  try {
    await f.loadAll(); f.scheduleDialog.value = { open: row => opened.push(row.id), isSaving: () => false }
    const item = f.ganttData.value.groups[0].items[0]
    f.openGanttSchedule(item); assert.deepEqual(opened, [11])
    f.openGanttSchedule({ ...item }); assert.equal(opened.length, 1)
  } finally { f.cleanup() }
})

test('transition does not mutate its source optimistically and duplicate/status/submit requests are locked', async () => {
  const pending = deferred(), f = setup({ api: { transitionManualSuiteStatus: () => pending.promise } })
  try {
    await f.loadAll(); const row = f.boardColumns.value[0].items[0]
    const writing = f.moveRequirement({ item: row, status: 4 })
    assert.equal(row.status, 3); assert.equal(f.isBusy(11), true)
    await f.moveRequirement({ item: row, status: 4 }); await f.confirmSubmit(row)
    assert.equal(f.writes.length, 1)
    pending.resolve({ data: { suite: suite({ status: 4 }), warnings: [] } }); await writing
    assert.equal(row.status, 3); assert.equal(f.isBusy(11), false); assert.equal(f.saveState.value, 'saved')
  } finally { f.cleanup() }
})

test('failed write preserves rows, restores button state and allows a fresh retry', async () => {
  let fail = true
  const f = setup({ api: { transitionManualSuiteStatus: async () => { if (fail) throw Error('Offline'); return { data: { suite: suite({ status: 4 }), warnings: [] } } } } })
  try {
    await f.loadAll(); const row = f.boardColumns.value[0].items[0]
    assert.equal(await f.moveRequirement({ item: row, status: 4 }), false)
    assert.equal(row.status, 3); assert.equal(f.saveState.value, 'failed'); assert.equal(f.isBusy(11), false)
    fail = false; assert.equal(await f.moveRequirement({ item: row, status: 4 }), true)
    assert.equal(f.writes.length, 2); assert.equal(f.saveState.value, 'saved')
  } finally { f.cleanup() }
})

test('successful transition remains saved when refresh fails; warnings are retained', async () => {
  let readingFails = false
  const f = setup({ api: {
    getManualSuite: async () => { if (readingFails) throw Error('Refresh failed'); return { data: [suite()] } },
    transitionManualSuiteStatus: async () => { readingFails = true; return { data: { suite: suite({ status: 4 }), warnings: ['Example warning'] } } },
  } })
  try {
    await f.loadAll(); await f.moveRequirement({ item: f.suites.value[0], status: 4 }); await settle()
    assert.equal(f.saveState.value, 'saved'); assert.equal(f.regions.suites.error.value, true)
    assert.equal(f.suites.value[0].status, 4); assert.equal(f.writes.length, 1)
    assert.ok(f.messages.some(([kind, text]) => kind === 'warning' && text === 'Example warning'))
  } finally { f.cleanup() }
})

test('confirmation captures update_time and becomes inert after a scope switch', async () => {
  const f = setup()
  try {
    await f.loadAll(); const row = f.suites.value[0]
    f.moveRequirement({ item: row, status: 6 }); row.update_time = 'Changed after confirmation opened'
    await f.dialogs[0].config.onBeforeOk()
    assert.equal(f.writes[0][1].expected_update_time, '2026-11-07 10:00:00')
    f.dialogs[0].handle.close(); await settle()
    f.cancelRequirement(f.suites.value[0]); const dialog = f.dialogs[1]
    f.user.roleId = 2; assert.equal(await dialog.config.onBeforeOk(), false); assert.equal(f.writes.length, 1)
  } finally { f.cleanup() }
})

test('old-context write acknowledgements cannot apply, notify, or release the physical lock early', async () => {
  const pending = deferred(), f = setup({ api: { transitionManualSuiteStatus: () => pending.promise } })
  try {
    await f.loadAll(); const writing = f.moveRequirement({ item: f.suites.value[0], status: 4 })
    f.user.roleId = 2; f.user.roleId = 1; await f.loadAll()
    assert.equal(f.isBusy(11), true)
    await f.moveRequirement({ item: f.suites.value[0], status: 4 }); assert.equal(f.writes.length, 1)
    pending.resolve({ data: { suite: suite({ status: 4 }), warnings: [] } }); await writing
    assert.equal(f.suites.value[0].status, 3); assert.deepEqual(f.messages, []); assert.equal(f.isBusy(11), false)
  } finally { f.cleanup() }
})

test('wrong-record acknowledgement fails locally; schedule saving blocks other writes for the same record', async () => {
  const f = setup({ api: { confirmManualSuiteSubmit: async () => ({ data: suite({ id: 99, status: 4 }) }) } })
  try {
    await f.loadAll(); const row = f.suites.value[0]
    f.scheduleDialog.value = { open() {}, isSaving: id => id === 11 }
    await f.confirmSubmit(row); assert.equal(f.writes.length, 0)
    f.scheduleDialog.value = null; assert.equal(await f.confirmSubmit(row), false)
    assert.equal(f.saveState.value, 'failed'); assert.equal(row.status, 3)
  } finally { f.cleanup() }
})

test('a previous scope physical write does not leave a completed new-scope write labelled saving', async () => {
  const pending = deferred(), f = setup({ api: {
    getManualSuite: async () => ({ data: [suite(), suite({ id: 12 })] }),
    transitionManualSuiteStatus: async body => body.id === 11 ? pending.promise : { data: { suite: suite({ id: 12, status: 4 }), warnings: [] } },
  } })
  try {
    await f.loadAll(); const oldWrite = f.moveRequirement({ item: f.suites.value[0], status: 4 })
    f.user.roleId = 2; await f.loadAll()
    await f.moveRequirement({ item: f.suites.value[1], status: 4 })
    assert.equal(f.isBusy(11), true); assert.equal(f.isBusy(12), false); assert.equal(f.saveState.value, 'saved')
    pending.resolve({ data: { suite: suite({ status: 4 }), warnings: [] } }); await oldWrite
    assert.equal(f.saveState.value, 'saved')
  } finally { f.cleanup() }
})
