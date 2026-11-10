import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { readFileSync } from 'node:fs'
import { compileScript, compileStyle, compileTemplate, parse } from '@vue/compiler-sfc'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/iteration')
const suite = (id = 11) => ({ id, requirement_name: 'Example requirement', requirement: { id: 7, name: 'Example requirement', requirement_key: 'REQ-7' }, version_no: 2, status: 3, priority: 0, owner: { id: 4, name: 'Example tester' }, development_owner: { id: 6, name: 'Example developer' }, planned_start_date: '2026-11-01', planned_submit_date: '2026-11-05', project_product: { id: 2, name: 'Example product', project: { id: 1, name: 'Example project' } }, module: { id: 3, name: 'Example module', full_path: 'Example / Module' }, iteration_ref: { id: 5 }, automation_coverage_percent: 50, case_count: 2 })
const cases = () => [1, 2].map(id => ({ id, case_no: `CASE-${id}`, title: `Example case ${id}`, priority: 0, owner: { id: 4, name: 'Example tester' } }))
const settle = async () => { await flush(); await new Promise(resolve => setImmediate(resolve)); await flush() }
function setup(overrides = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, selected_environment: 1, token: 'example-test-token' })
  const route = vue.reactive({ fullPath: '/functional-test/iteration/details?id=1' })
  const hooks = { stop: [], activate: [], unmount: [] }, requests = [], writes = [], dialogs = [], navigations = [], messages = []
  const api = {
    getManualSuite: async body => ({ data: [suite(body.id)] }),
    getFunctionalRequirementCases: async () => ({ data: cases() }),
    getRelatedFunctionalPlans: async () => ({ data: [{ id: 21, name: 'Example plan', status: 0 }] }),
    getRelatedFunctionalDefects: async () => ({ data: [{ id: 31, defect_no: 'DEF-31', title: 'Example defect', status: 0 }] }),
    getFunctionalContextResource: async () => ({ data: [{ id: 41, title: 'Example resource', context_key: 'requirement', update_time: '2026-11-07 10:00:00' }] }),
    unbindFunctionalRequirementCases: async () => ({ data: { unbound_count: 1 } }),
    ...overrides.api,
  }
  const wrappedApi = Object.fromEntries(Object.entries(api).map(([key, fn]) => [key, async (...args) => {
    (key === 'unbindFunctionalRequirementCases' ? writes : requests).push([key, ...args]); return fn(...args)
  }]))
  function confirm(config) { const handle = { close() { config.onClose?.() } }; dialogs.push({ config, handle }); return handle }
  const f = harness('RequirementOverviewDrawer', 'loadAll,regions,regionErrors,suite,cases,plans,defects,resources,selectedCaseKeys,selectCases,unlinkCases,unlinking,unlinkError,navigation,navigationError,blocked,changeVisible,editSchedule,openWorkspace,openDetail,createPlan,openPlan,activeTab', {
    base, props: { visible: true, suiteId: 11, contextKey: 'A', ...overrides.props }, api: wrappedApi,
    modules: {
      vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      'vue-router': { useRoute: () => route, useRouter: () => ({ push: async target => { navigations.push(target); return overrides.navigate?.(target) } }) },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ colors: {}, getEnum: overrides.getEnum ?? (async () => {}) }) },
      '@arco-design/web-vue': { Modal: { warning: confirm }, Message: Object.fromEntries(['success', 'error', 'warning'].map(key => [key, value => messages.push([key, value])])) },
    },
  })
  return { ...f, user, route, hooks, requests, writes, dialogs, navigations, messages, cleanup: () => { hooks.unmount.forEach(fn => fn()); f.close() } }
}

test('drawer regions load independently and remain usable with slow resources and failed enums', async () => {
  const pending = deferred(), f = setup({ api: { getFunctionalContextResource: () => pending.promise }, getEnum: async () => { throw Error('Enum failed') } })
  try {
    await settle(); assert.equal(f.suite.value.id, 11); assert.equal(f.cases.value.length, 2); assert.equal(f.plans.value.length, 1)
    assert.equal(f.regions.suite.loading.value, false); assert.equal(f.regions.resources.loading.value, true); assert.equal(f.regions.enums.error.value, true)
    pending.resolve({ data: [] }); await settle(); assert.equal(f.regions.resources.loading.value, false)
  } finally { f.cleanup() }
})

test('failed region preserves existing data and retry only reads that region', async () => {
  let fail = false
  const f = setup({ api: { getFunctionalContextResource: async () => { if (fail) throw Error('Offline'); return { data: [{ id: 41, title: 'Example resource' }] } } } })
  try {
    await settle(); const rows = f.resources.value; fail = true; await f.regions.resources.load()
    assert.equal(f.regions.resources.error.value, true); assert.equal(f.resources.value, rows); assert.equal(f.regions.resources.loading.value, false)
    const count = f.requests.length; fail = false; await f.regions.resources.load()
    assert.equal(f.requests.length, count + 1); assert.equal(f.regions.resources.error.value, false)
  } finally { f.cleanup() }
})

test('switching records resets tabs, selection and all data and ignores late old-record reads', async () => {
  const pending = deferred(), f = setup({ api: { getManualSuite: async body => body.id === 11 ? pending.promise : { data: [suite(body.id)] } } })
  try {
    await settle(); f.selectCases([1]); f.activeTab.value = 'cases'; f.props.suiteId = 12
    assert.equal(f.activeTab.value, 'overview'); assert.deepEqual(f.selectedCaseKeys.value, []); assert.equal(f.suite.value, null)
    await settle(); assert.equal(f.suite.value.id, 12)
    pending.resolve({ data: [suite(11)] }); await settle(); assert.equal(f.suite.value.id, 12)
  } finally { f.cleanup() }
})

test('latest read wins and wrong-record detail is an error, not a fallback empty record', async () => {
  const first = deferred(), f = setup({ api: { getManualSuite: async () => first.promise } })
  try {
    f.props.visible = false; f.props.visible = true
    first.resolve({ data: [suite(99)] }); await settle()
    assert.equal(f.suite.value, null); assert.equal(f.regions.suite.error.value, true)
    f.editSchedule(); await f.openWorkspace(); assert.deepEqual(f.navigations, [])
  } finally { f.cleanup() }
})

for (const key of ['userId', 'roleId', 'selected_environment', 'token', 'contextKey', 'route']) {
  test(`${key} change closes and invalidates pending reads, even after A to B to A`, async () => {
    const pending = deferred(), f = setup({ api: { getManualSuite: () => pending.promise } })
    try {
      await settle()
      if (key === 'contextKey') { f.props.contextKey = 'B'; f.props.contextKey = 'A' }
      else if (key === 'route') { f.route.fullPath = '/functional-test/plan/index'; f.route.fullPath = '/functional-test/iteration/details?id=1' }
      else { const previous = f.user[key]; f.user[key] = key === 'token' ? 'example-other-token' : 2; f.user[key] = previous }
      pending.resolve({ data: [suite()] }); await settle()
      assert.equal(f.blocked.value, true); assert.equal(f.suite.value, null); assert.equal(f.regions.suite.error.value, false)
      assert.ok(f.events.some(([event, value]) => event === 'update:visible' && value === false))
      f.editSchedule(); await f.openDetail(); assert.deepEqual(f.navigations, [])
    } finally { f.cleanup() }
  })
}

test('closing suppresses late failures and reopening starts a new clean session', async () => {
  const pending = deferred(); let first = true
  const f = setup({ api: { getManualSuite: async body => { if (first) { first = false; return pending.promise } return { data: [suite(body.id)] } } } })
  try {
    f.changeVisible(false); pending.reject(Error('Late')); await settle()
    assert.equal(f.regions.suite.error.value, false); assert.equal(f.suite.value, null)
    f.props.visible = false; f.props.visible = true; await settle(); assert.equal(f.suite.value.id, 11); assert.equal(f.blocked.value, false)
  } finally { f.cleanup() }
})

test('initial activation does not duplicate requests and deactivate/unmount suppress old results', async () => {
  const f = setup()
  try {
    await settle(); const before = f.requests.length; f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(f.requests.length, before)
    f.hooks.stop.forEach(fn => fn()); assert.equal(f.suite.value, null); assert.equal(f.blocked.value, true)
    f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(f.requests.length, before)
    f.props.visible = false; f.props.visible = true; await settle(); assert.equal(f.suite.value.id, 11)
    f.hooks.unmount.forEach(fn => fn()); const count = f.requests.length; await f.loadAll(); assert.equal(f.requests.length, count)
  } finally { f.cleanup() }
})

test('selection only accepts unique owned IDs and refresh prunes missing records', async () => {
  let rows = cases(), f = setup({ api: { getFunctionalRequirementCases: async () => ({ data: rows }) } })
  try {
    await settle(); f.selectCases([1, 1, 2, 999, '1']); assert.deepEqual(f.selectedCaseKeys.value, [1, 2])
    rows = [cases()[1]]; await f.regions.cases.load(); assert.deepEqual(f.selectedCaseKeys.value, [2])
  } finally { f.cleanup() }
})

test('unbind confirmation snapshots owned IDs and does not retarget when selection changes', async () => {
  const pending = deferred(), f = setup({ api: { unbindFunctionalRequirementCases: () => pending.promise } })
  try {
    await settle(); f.selectCases([1]); f.unlinkCases(); f.selectCases([2]); f.unlinkCases(); assert.equal(f.dialogs.length, 1)
    const writing = f.dialogs[0].config.onBeforeOk(); assert.deepEqual(f.writes, [['unbindFunctionalRequirementCases', 11, [1]]])
    f.selectCases([1, 2]); assert.deepEqual(f.selectedCaseKeys.value, [2])
    await f.dialogs[0].config.onBeforeOk(); assert.equal(f.writes.length, 1); assert.equal(f.dialogs[0].config.onBeforeCancel(), false)
    pending.resolve({ data: { unbound_count: 1 } }); assert.equal(await writing, true)
    assert.equal(f.unlinking.value, false); assert.deepEqual(f.selectedCaseKeys.value, [])
    assert.equal(f.events.filter(([event]) => event === 'changed').length, 1)
    assert.deepEqual(f.events.filter(([event]) => event === 'busy'), [['busy', true], ['busy', false]])
  } finally { f.cleanup() }
})

test('failed unbind retains selection and permits retry on the same confirmation', async () => {
  let fail = true, f = setup({ api: { unbindFunctionalRequirementCases: async () => { if (fail) throw Error('Offline'); return { data: { unbound_count: 0 } } } } })
  try {
    await settle(); f.selectCases([1]); f.unlinkCases()
    assert.equal(await f.dialogs[0].config.onBeforeOk(), false); assert.equal(f.unlinkError.value, true); assert.deepEqual(f.selectedCaseKeys.value, [1]); assert.equal(f.unlinking.value, false)
    fail = false; assert.equal(await f.dialogs[0].config.onBeforeOk(), true); assert.equal(f.unlinkError.value, false); assert.equal(f.writes.length, 2)
  } finally { f.cleanup() }
})

test('confirmed unbind remains successful when reload fails and only relationship-specific API is called', async () => {
  let failRead = false
  const f = setup({ api: {
    getFunctionalRequirementCases: async () => { if (failRead) throw Error('Refresh failed'); return { data: cases() } },
    unbindFunctionalRequirementCases: async () => { failRead = true; return { data: { unbound_count: 1 } } },
  } })
  try {
    await settle(); f.selectCases([1]); f.unlinkCases(); assert.equal(await f.dialogs[0].config.onBeforeOk(), true); await settle()
    assert.equal(f.unlinkError.value, false); assert.equal(f.regions.cases.error.value, true); assert.deepEqual(f.cases.value.map(row => row.id), [2])
    assert.deepEqual(f.writes, [['unbindFunctionalRequirementCases', 11, [1]]])
  } finally { f.cleanup() }
})

test('old confirmation and pending unbind become inert across a scope switch while the physical lock remains', async () => {
  const pending = deferred(), f = setup({ api: { unbindFunctionalRequirementCases: () => pending.promise } })
  try {
    await settle(); f.selectCases([1]); f.unlinkCases(); const writing = f.dialogs[0].config.onBeforeOk()
    f.user.roleId = 2; f.props.visible = false; f.props.visible = true; await settle()
    f.selectCases([2]); f.unlinkCases(); assert.equal(f.unlinking.value, true); assert.equal(f.dialogs.length, 1)
    assert.equal(await f.dialogs[0].config.onBeforeOk(), false)
    pending.resolve({ data: { unbound_count: 1 } }); assert.equal(await writing, false)
    assert.equal(f.events.filter(([event]) => event === 'changed').length, 0); assert.deepEqual(f.messages, []); assert.equal(f.unlinking.value, false)
  } finally { f.cleanup() }
})

test('navigation failure stays local, duplicate clicks are blocked, and retry uses the correct existing routes', async () => {
  const pending = deferred(); let first = true
  const f = setup({ navigate: async () => { if (first) { first = false; return pending.promise } } })
  try {
    await settle(); const navigation = f.openWorkspace(); await f.openDetail(); assert.equal(f.navigations.length, 1); assert.equal(f.navigation.value, 'workspace')
    pending.reject(Error('Chunk failed')); await navigation; assert.equal(f.navigationError.value, true); assert.equal(f.navigation.value, null); assert.equal(f.blocked.value, false)
    await f.openWorkspace(); assert.deepEqual(f.navigations, [{ path: '/functional-test/suite/details', query: { id: 11 } }, { path: '/functional-test/suite/details', query: { id: 11 } }]); assert.equal(f.blocked.value, true)
  } finally { f.cleanup() }
})

test('aborted navigation is retryable and late navigation failure cannot mark a new scope failed', async () => {
  const f = setup({ navigate: async () => ({ type: 4 }) })
  try { await settle(); await f.createPlan(); assert.equal(f.navigationError.value, true); assert.equal(f.blocked.value, false); assert.deepEqual(f.navigations, [{ path: '/functional-test/plan/index', query: { requirement_version: 11 } }]) }
  finally { f.cleanup() }
  const pending = deferred(), late = setup({ navigate: () => pending.promise })
  try { await settle(); const navigation = late.openDetail(); late.user.roleId = 2; pending.reject(Error('Late')); await navigation; assert.equal(late.navigationError.value, false) }
  finally { late.cleanup() }
})

test('foreign plans and closed or invalid records cannot navigate or cancel relationships', async () => {
  const f = setup()
  try {
    await settle(); await f.openPlan({ id: 999 }); assert.deepEqual(f.navigations, [])
    f.props.suiteId = 0; f.selectCases([1]); f.unlinkCases(); await f.openWorkspace(); assert.deepEqual(f.navigations, []); assert.deepEqual(f.writes, [])
  } finally { f.cleanup() }
})

test('edit handoff preserves the finite fields required by both actual parents and uses freshly loaded dates', async () => {
  const f = setup()
  try {
    await settle(); f.editSchedule(); const record = f.events.find(([event]) => event === 'edit-schedule')[1]
    assert.equal(record.module.full_path, 'Example / Module'); assert.equal(record.project_product.project.id, 1)
    const editorCalls = [], overviewVisible = vue.ref(true)
    const openSuite = method('openSuite', {
      usersActive: true, writeBlocked: vue.ref(false), caseVisible: vue.ref(false), overviewVisible, navigationCreateRef: vue.ref(null),
      suiteEditor: vue.ref({ open: (...args) => editorCalls.push(args) }),
    }, path.resolve('src/views/functional-test/suite/index.vue'))
    await openSuite(record)
    assert.equal(editorCalls[0][0], 'edit'); assert.equal(editorCalls[0][1], record)
    assert.equal(overviewVisible.value, false)
    const opened = [], openSchedule = method('openSchedule', {
      available: () => true, isBusy: () => false, suites: vue.ref([{ id: 11, planned_submit_date: 'Old' }]), boardColumns: vue.ref([]), scheduleDialog: vue.ref({ open: value => opened.push(value) }),
    }, path.join(base, 'details/index.vue'))
    openSchedule(record); assert.equal(opened[0], record); assert.equal(opened[0].planned_submit_date, '2026-11-05')
  } finally { f.cleanup() }
})

test('overview and both parent SFC scripts/templates/styles compile', () => {
  for (const filename of [path.join(base, 'components/RequirementOverviewDrawer.vue'), path.join(base, 'details/index.vue'), path.resolve('src/views/functional-test/suite/index.vue')]) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: filename, scoped: style.scoped, preprocessLang: style.lang }).errors, [])
  }
})
