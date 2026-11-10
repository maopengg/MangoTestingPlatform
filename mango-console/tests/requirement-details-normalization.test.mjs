import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/requirement/details')
const requirement = fields => ({ id: 10, name: 'Example requirement', requirement_key: 'REQ-10', owner: 4, issue_type: 0, requirement_category: 0, ...fields })
const suite = fields => ({ id: 1, requirement_name: 'Example version', requirement: requirement(), status: 1, version_no: 1,
  update_time: '2026-11-01 10:00:00', project_product: { id: 2, name: 'Example product' },
  owner: { id: 4, name: 'QA owner' }, development_owner: { id: 5, name: 'Developer' }, delivery_team: { id: 6, name: 'Example team' }, iteration_ref: { id: 7, name: 'Example sprint' },
  description: '', test_required: true, automation_recommended: false, effect_test_required: false,
  planned_start_date: null, planned_submit_date: null, planned_release_date: null, customer_deadline_date: null, committed_release_date: null, customer_ref: '', ...fields })
const mutation = body => ({ ...suite(), owner: 4, development_owner: 5, delivery_team: 6, iteration_ref: 7, requirement: 10, ...body, update_time: '2026-11-01 10:01:00' })
const caseRow = (id = 3) => ({ id, case_no: 'CASE-' + id, title: 'Example case', priority: 0, owner: { name: 'Example owner' } })
const plan = (id = 8) => ({ id, name: 'Example plan', status: 0, owner: { name: 'Example owner' }, execution_stats: { progress: 0, pass_rate: 0 } })
const settle = async () => { await flush(); await new Promise(resolve => setImmediate(resolve)); await flush() }
function setup(overrides = {}) {
  const hooks = { mount: [], stop: [], activate: [], unmount: [] }, calls = [], notices = [], navigations = []
  const route = vue.reactive({ path: '/functional-test/requirement/details', fullPath: '/functional-test/requirement/details?id=1', query: { id: '1' } })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'example-token', selected_environment: 1 })
  const api = {
    getManualSuite: async query => ({ data: [suite({ id: query.id })] }), getFunctionalRequirementCases: async () => ({ data: [caseRow()] }),
    getRelatedFunctionalPlans: async () => ({ data: [plan()] }), getRelatedFunctionalDefects: async () => ({ data: [{ id: 9, defect_no: 'DEF-9', title: 'Example defect', status: 0, severity: 0, assignee: null }] }),
    getFunctionalContextResource: async () => ({ data: [{ id: 11, title: 'Example document', content: 'Example text', update_time: '2026-11-01 10:00:00' }] }),
    getUserName: async () => ({ data: [{ key: 4, title: 'Loaded owner' }] }), getUserDepartment: async () => ({ data: [{ id: 6, name: 'Loaded team' }] }),
    getFunctionalIterations: async () => ({ data: [{ id: 7, iteration_no: 'SPR-7', name: 'Loaded sprint' }] }),
    putManualSuite: async body => ({ data: mutation(body) }), putFunctionalRequirement: async body => ({ data: requirement(body) }),
    transitionManualSuiteStatus: async body => ({ data: { suite: suite({ id: body.id, status: body.status, update_time: '2026-11-01 10:02:00' }), warnings: [] } }),
    unbindFunctionalRequirementCases: async () => ({ data: { unbound_count: 1 } }), ...overrides.api,
  }
  const f = harness('index', 'suiteId,contextKey,suite,form,requirementForm,cases,plans,defects,resources,loading,errors,users,departments,iterations,userOptions,departmentOptions,iterationOptions,loadAll,loadSuite,loadCases,loadPlans,loadDefects,loadResources,loadUsers,loadDepartments,loadIterations,loadEnums,saver,saveSuiteField,changeStatus,retryTransition,transitioning,transitionError,requestedStatus,selectedCaseIds,selectCases,openCasePicker,casePickerRef,tasksRef,onCasesBound,unbindCases,unbindingIds,unbindError,physicalBusy,controlsBlocked,operationBlocked,hasUnsaved,navigate,openCaseWorkspace,createPlan,createDefect,openPlan,openCase,navigating,navigationError,loaded,applySuite', {
    base, api: Object.fromEntries(Object.entries(api).map(([key, fn]) => [key, (...args) => { calls.push([key, ...args]); return fn(...args) }])),
    modules: {
      vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      'vue-router': { useRoute: () => route, useRouter: () => ({ back() {}, push: async target => { navigations.push(target); return overrides.push?.(target) } }) },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ colors: {}, case_level: [], functional_test_plan_status: [], functional_test_defect_status: [], functional_test_defect_severity: [], getEnum: overrides.getEnum || (async () => {}) }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error'].map(kind => [kind, text => notices.push([kind, text])])) },
    },
  })
  return { ...f, route, user, calls, hooks, notices, navigations, cleanup() { hooks.unmount.forEach(fn => fn()); f.close() } }
}
test('all regions load independently of failed users and plans and slow resources', async () => {
  const slow = deferred(), f = setup({ api: { getUserName: async () => { throw Error('Offline') }, getRelatedFunctionalPlans: async () => { throw Error('Offline') }, getFunctionalContextResource: () => slow.promise } })
  try {
    f.hooks.mount.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await settle()
    assert.equal(f.loaded.value, true); assert.equal(f.loading.suite, false); assert.equal(f.cases.value.length, 1); assert.equal(f.errors.users, true); assert.equal(f.errors.plans, true); assert.equal(f.loading.resources, true)
    assert.equal(f.form.owner, 4); assert.equal(f.requirementForm.owner, 4); assert.equal(f.requirementForm.issue_type, 0)
    assert.equal(f.userOptions.value.find(x => x.key === 5).title, 'Developer'); assert.equal(f.calls.filter(([kind]) => kind === 'getManualSuite').length, 1)
    slow.resolve({ data: [] }); await settle(); assert.equal(f.loading.resources, false)
  } finally { f.cleanup() }
})
test('empty and wrong-owner suite responses leave a local error and can retry', async () => {
  let data = [], f = setup({ api: { getManualSuite: async () => ({ data }) } })
  try {
    await f.loadSuite(); assert.equal(f.errors.suite, true); assert.equal(f.suite.value, null)
    data = [suite({ id: 2 })]; await f.loadSuite(); assert.equal(f.errors.suite, true)
    data = [suite()]; await f.loadSuite(); assert.equal(f.errors.suite, false); assert.equal(f.suite.value.id, 1)
  } finally { f.cleanup() }
})
test('region failures retain current data and retry without waiting for another region', async () => {
  let fail = false, f = setup({ api: { getRelatedFunctionalPlans: async () => { if (fail) throw Error('Offline'); return { data: [plan()] } } } })
  try { await f.loadPlans(); fail = true; await f.loadPlans(); assert.equal(f.plans.value.length, 1); assert.equal(f.errors.plans, true); fail = false; await f.loadPlans(); assert.equal(f.errors.plans, false) } finally { f.cleanup() }
})
test('a later read wins and a draft edited during the read is retained', async () => {
  const a = deferred(), b = deferred(); let count = 0
  const f = setup({ api: { getManualSuite: () => ++count === 1 ? Promise.resolve({ data: [suite()] }) : count === 2 ? a.promise : b.promise } })
  try {
    await f.loadSuite(); const first = f.loadSuite(), second = f.loadSuite(); f.form.description = 'Draft'
    b.resolve({ data: [suite({ requirement_name: 'Newer' })] }); await second; a.resolve({ data: [suite({ requirement_name: 'Older' })] }); await first
    assert.equal(f.suite.value.form.requirement_name, 'Newer'); assert.equal(f.form.description, 'Draft'); assert.equal(f.form.requirement_name, 'Newer')
  } finally { f.cleanup() }
})
for (const value of [undefined, '', '0', '-1', '1.5', ['1'], '9007199254740992']) {
  test(`invalid route ID ${JSON.stringify(value)} prevents reads and writes`, async () => {
    const f = setup()
    try { f.route.query.id = value; await f.loadAll(); await f.changeStatus(2); f.openCasePicker(); await f.createPlan(); assert.equal(f.suiteId.value, null); assert.deepEqual(f.calls, []); assert.deepEqual(f.navigations, []) } finally { f.cleanup() }
  })
}
for (const key of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`${key} A-B-A clears detail and options and rejects an old response`, async () => {
    const pending = deferred(), f = setup({ api: { getManualSuite: () => pending.promise } })
    try { const read = f.loadSuite(), old = f.user[key]; f.user[key] = key === 'token' ? 'example-new-token' : 2; f.user[key] = old; pending.resolve({ data: [suite()] }); await read; assert.equal(f.suite.value, null); assert.deepEqual(f.users.value, []); assert.equal(f.form.requirement_name, '') } finally { f.cleanup() }
  })
}
test('route ID changes load the actual new ID; cache activation reloads once and inactive reads are ignored', async () => {
  const f = setup()
  try {
    f.hooks.mount.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(f.calls.filter(([kind]) => kind === 'getManualSuite').length, 1)
    f.route.query.id = '2'; f.route.fullPath = '/functional-test/requirement/details?id=2'; await settle(); assert.equal(f.suite.value.id, 2)
    f.hooks.stop.forEach(fn => fn()); const count = f.calls.length; await f.loadAll(); assert.equal(f.calls.length, count); assert.equal(f.suite.value, null)
    f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(f.suite.value.id, 2)
    f.hooks.unmount.forEach(fn => fn()); await f.loadAll(); assert.equal(f.suite.value, null)
  } finally { f.cleanup() }
})
test('suite save is whitelisted and correctly parses mutation responses with scalar relation IDs', async () => {
  const f = setup()
  try {
    await f.loadSuite(); f.form.development_owner = null; await f.saveSuiteField('development_owner')
    assert.deepEqual(f.calls.find(([kind]) => kind === 'putManualSuite'), ['putManualSuite', { id: 1, development_owner: null }]); assert.equal(f.suite.value.form.development_owner, null)
    f.form.planned_start_date = ''; await f.saveSuiteField('planned_start_date'); assert.equal(f.calls.at(-1)[1].planned_start_date, null); assert.equal(f.form.planned_start_date, null)
    assert.equal(f.suite.value.update_time, '2026-11-01 10:01:00')
    const before = f.calls.length; await f.saveSuiteField('owner'); await f.saveSuiteField('update_time'); assert.equal(f.calls.length, before)
  } finally { f.cleanup() }
})
test('requirement save uses the nested requirement ID and scalar PM with zero enum values', async () => {
  const f = setup()
  try {
    await f.loadSuite(); f.requirementForm.owner = 5; await f.saver.saveRequirement()
    assert.deepEqual(f.calls.find(([kind]) => kind === 'putFunctionalRequirement'), ['putFunctionalRequirement', { id: 10, owner: 5, issue_type: 0, requirement_category: 0 }])
    assert.equal(f.suite.value.requirement.form.owner, 5); assert.equal(f.hasUnsaved.value, false)
  } finally { f.cleanup() }
})
test('save requests serialize, skip duplicate pending values and preserve later edits', async () => {
  const first = deferred(), second = deferred(); let count = 0
  const f = setup({ api: { putManualSuite: () => ++count === 1 ? first.promise : second.promise } })
  try {
    await f.loadSuite(); f.form.description = 'First'; const save = f.saveSuiteField('description'); await flush()
    f.form.description = 'Latest'; f.saveSuiteField('description'); assert.equal(count, 1)
    first.resolve({ data: mutation({ description: 'First' }) }); await settle(); assert.equal(f.form.description, 'Latest'); assert.equal(count, 2)
    second.resolve({ data: mutation({ description: 'Latest' }) }); await save; assert.equal(f.suite.value.form.description, 'Latest'); assert.equal(f.hasUnsaved.value, false)
  } finally { f.cleanup() }
})
test('failed saves preserve drafts and retry only failed fields with their latest values', async () => {
  let fail = true, f = setup({ api: { putManualSuite: async body => { if (fail) throw Error('Offline'); return { data: mutation(body) } } } })
  try {
    await f.loadSuite(); f.form.description = 'Failed'; await f.saveSuiteField('description'); assert.equal(f.saver.failed.has('description'), true); assert.equal(f.saver.writing.value, false); assert.equal(f.form.description, 'Failed')
    f.form.description = 'Retry'; fail = false; await f.saver.retry(); assert.deepEqual(f.calls.at(-1), ['putManualSuite', { id: 1, description: 'Retry' }]); assert.equal(f.saver.failed.size, 0)
  } finally { f.cleanup() }
})
test('duplicate blur events during the same save do not make a second request', async () => {
  const pending = deferred(), f = setup({ api: { putManualSuite: () => pending.promise } })
  try {
    await f.loadSuite(); f.form.description = 'One value'; const first = f.saveSuiteField('description'); await flush(); const second = f.saveSuiteField('description')
    pending.resolve({ data: mutation({ description: 'One value' }) }); await Promise.all([first, second]); assert.equal(f.calls.filter(([kind]) => kind === 'putManualSuite').length, 1)
  } finally { f.cleanup() }
})
test('a synchronous request setup failure releases the save lock and permits retry', async () => {
  let fail = true, f = setup({ api: { putManualSuite: body => { if (fail) throw Error('Setup failed'); return Promise.resolve({ data: mutation(body) }) } } })
  try {
    await f.loadSuite(); f.form.description = 'Draft'; await f.saveSuiteField('description'); assert.equal(f.saver.writing.value, false); assert.equal(f.saver.failed.has('description'), true)
    fail = false; await f.saver.retry(); assert.equal(f.suite.value.form.description, 'Draft'); assert.equal(f.saver.failed.size, 0)
  } finally { f.cleanup() }
})
test('a changed underlying requirement resets its private draft instead of applying the previous requirement owner', async () => {
  const f = setup()
  try {
    await f.loadSuite(); f.requirementForm.owner = 99
    f.applySuite(f.load('presentation.ts').parseRequirementVersion(suite({ requirement: requirement({ id: 12, owner: 5 }) }), 1))
    assert.equal(f.requirementForm.owner, 5); assert.equal(f.suite.value.requirement.id, 12)
  } finally { f.cleanup() }
})
test('unconfirmed writes cannot change the confirmed record and recover through retry', async () => {
  let data = { id: 9, description: 'Changed', update_time: 'later' }, f = setup({ api: { putManualSuite: async () => ({ data }) } })
  try {
    await f.loadSuite(); f.form.description = 'Changed'; await f.saveSuiteField('description'); assert.equal(f.suite.value.form.description, ''); assert.equal(f.saver.failed.has('description'), true)
    data = mutation({ description: 'Changed' }); await f.saver.retry(); assert.equal(f.suite.value.form.description, 'Changed')
  } finally { f.cleanup() }
})
test('switches change their displayed state only after a confirmed response', async () => {
  const pending = deferred(), f = setup({ api: { putManualSuite: () => pending.promise } })
  try {
    await f.loadSuite(); const save = f.saver.toggleFlag('test_required'); await flush(); assert.equal(f.form.test_required, true)
    pending.resolve({ data: mutation({ test_required: false }) }); await save; assert.equal(f.form.test_required, false); assert.equal(f.suite.value.form.test_required, false)
  } finally { f.cleanup() }
})
test('a read started before saving cannot restore the previous confirmed value', async () => {
  const old = deferred(); let count = 0
  const f = setup({ api: { getManualSuite: () => ++count === 1 ? Promise.resolve({ data: [suite()] }) : old.promise } })
  try {
    await f.loadSuite(); const read = f.loadSuite(); f.loading.suite = false; f.form.description = 'Saved'; await f.saveSuiteField('description')
    old.resolve({ data: [suite()] }); await read; assert.equal(f.suite.value.form.description, 'Saved')
  } finally { f.cleanup() }
})
test('transition captures status and optimistic timestamp, prevents duplicates and can retry', async () => {
  let fail = true, f = setup({ api: { transitionManualSuiteStatus: async body => { if (fail) throw Error('Offline'); return { data: { suite: suite({ status: body.status }) } } } } })
  try {
    await f.loadSuite(); assert.equal(await f.changeStatus(2), false); assert.equal(f.transitionError.value, true); assert.equal(f.suite.value.status, 1); assert.equal(f.transitioning.value, false)
    fail = false; assert.equal(await f.retryTransition(), true); assert.deepEqual(f.calls.filter(([kind]) => kind === 'transitionManualSuiteStatus').at(-1), ['transitionManualSuiteStatus', { id: 1, status: 2, expected_update_time: '2026-11-01 10:00:00' }]); assert.equal(f.suite.value.status, 2)
  } finally { f.cleanup() }
})
test('unbound iteration, pending drafts and child writes prevent a conflicting transition', async () => {
  const f = setup({ api: { getManualSuite: async () => ({ data: [suite({ iteration_ref: null })] }) } })
  try {
    await f.loadSuite(); await f.changeStatus(2); assert.equal(f.notices[0][0], 'warning')
    f.applySuite(f.load('presentation.ts').parseRequirementVersion(suite(), 1)); f.form.description = 'Uncommitted'; await f.changeStatus(2)
    f.form.description = ''; const pending = vue.ref(true); f.tasksRef.value = { isSaving: () => pending.value }; await f.changeStatus(2)
    assert.equal(f.calls.filter(([kind]) => kind === 'transitionManualSuiteStatus').length, 0)
  } finally { f.cleanup() }
})
test('physical save lock suppresses late writes after context change and restores the current page once settled', async () => {
  const pending = deferred(), f = setup({ api: { putManualSuite: () => pending.promise } })
  try {
    f.hooks.mount.forEach(fn => fn()); await settle(); f.form.description = 'Old'; const save = f.saveSuiteField('description'); await flush()
    f.user.roleId = 2; assert.equal(f.suite.value, null); assert.equal(f.saver.writing.value, true); await settle(); assert.equal(f.suite.value, null)
    pending.resolve({ data: mutation({ description: 'Old' }) }); await save; await settle(); assert.equal(f.suite.value.form.description, ''); assert.equal(f.form.description, ''); assert.equal(f.saver.failed.size, 0)
  } finally { f.cleanup() }
})
test('deactivation suppresses late transition failure and activation resumes after the physical lock', async () => {
  const pending = deferred(), f = setup({ api: { transitionManualSuiteStatus: () => pending.promise } })
  try {
    f.hooks.mount.forEach(fn => fn()); await settle(); const write = f.changeStatus(2); f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await settle()
    assert.equal(f.transitioning.value, true); assert.equal(f.suite.value, null); pending.reject(Error('Offline')); await write; await settle()
    assert.equal(f.transitionError.value, false); assert.equal(f.suite.value.status, 1); assert.deepEqual(f.notices, [])
  } finally { f.cleanup() }
})
test('case unbinding validates targets, is duplicate-safe, and keeps the successful outcome when rereading fails', async () => {
  const pending = deferred(); let failRead = false
  const f = setup({ api: { unbindFunctionalRequirementCases: () => pending.promise, getFunctionalRequirementCases: async () => { if (failRead) throw Error('Offline'); return { data: [caseRow()] } } } })
  try {
    await f.loadSuite(); await f.loadCases(); f.selectCases([3, 3, 999]); assert.deepEqual(f.selectedCaseIds.value, [3])
    const write = f.unbindCases([3, 3, 999]); await f.unbindCases([3]); assert.deepEqual(f.unbindingIds.value, [3])
    failRead = true; pending.resolve({ data: { unbound_count: 0 } }); assert.equal(await write, true); await settle()
    assert.equal(f.calls.filter(([kind]) => kind === 'unbindFunctionalRequirementCases').length, 1); assert.equal(f.unbindError.value, false); assert.equal(f.errors.cases, true); assert.deepEqual(f.cases.value, []); assert.deepEqual(f.selectedCaseIds.value, [])
  } finally { f.cleanup() }
})
test('case unbinding failure retains the relation and selection and can retry', async () => {
  let fail = true, f = setup({ api: { unbindFunctionalRequirementCases: async () => { if (fail) throw Error('Offline'); return { data: { unbound_count: 1 } } } } })
  try {
    await f.loadSuite(); await f.loadCases(); f.selectCases([3]); assert.equal(await f.unbindCases([3]), false); assert.equal(f.unbindError.value, true); assert.equal(f.cases.value.length, 1); assert.deepEqual(f.selectedCaseIds.value, [3])
    fail = false; assert.equal(await f.unbindCases([3]), true); assert.equal(f.unbindError.value, false)
  } finally { f.cleanup() }
})
test('late unbind acknowledgements from an old context do not remove current relations or show notifications', async () => {
  const pending = deferred(), f = setup({ api: { unbindFunctionalRequirementCases: () => pending.promise } })
  try {
    await f.loadSuite(); await f.loadCases(); const write = f.unbindCases([3]); f.user.roleId = 2
    pending.resolve({ data: { unbound_count: 1 } }); await write; assert.equal(f.suite.value, null); assert.deepEqual(f.notices, []); assert.deepEqual(f.unbindingIds.value, [])
  } finally { f.cleanup() }
})
test('picker change refreshes after its physical write lock and does not replace unsaved form inputs', async () => {
  const f = setup(), pending = vue.ref(true)
  try {
    await f.loadSuite(); f.form.description = 'Uncommitted'
    f.casePickerRef.value = { isSaving: () => pending.value, isOpen: () => false, open() {} }; f.onCasesBound(1); await settle()
    const count = f.calls.length; pending.value = false; await settle(); assert.ok(f.calls.length > count); assert.equal(f.form.description, 'Uncommitted')
  } finally { f.cleanup() }
})
test('navigation keeps registered paths, supplies create defaults and ignores non-owned row objects', async () => {
  const f = setup()
  try {
    await f.loadAll(); await f.createPlan(); assert.deepEqual(f.navigations.at(-1), { path: '/functional-test/plan/index', query: { requirement_version: 1, project_product: 2, create: 1 } })
    await f.openCase(f.cases.value[0]); assert.deepEqual(f.navigations.at(-1), { path: '/functional-test/case/details', query: { id: 3 } })
    const count = f.navigations.length; await f.openPlan({ ...f.plans.value[0] }); assert.equal(f.navigations.length, count)
    await f.createDefect(); assert.equal(f.navigations.at(-1).path, '/functional-test/defect/index')
  } finally { f.cleanup() }
})
test('navigation exposes a local loading state and failure retry', async () => {
  const pending = deferred(); let fail = true, f = setup({ push: () => fail ? pending.promise : undefined })
  try {
    await f.loadSuite(); const first = f.openCaseWorkspace(); await f.createPlan(); assert.equal(f.navigating.value, 'workspace'); assert.equal(f.navigations.length, 1)
    pending.reject(Error('Offline')); await first; assert.equal(f.navigationError.value, true); assert.equal(f.navigating.value, null)
    fail = false; await f.openCaseWorkspace(); assert.equal(f.navigationError.value, false)
  } finally { f.cleanup() }
})
test('main page compiles with typed scripts, actual template bindings and scoped styles', async () => {
  const filename = path.join(base, 'index.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'requirement42details' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'requirement42details', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: 'requirement42details', scoped: style.scoped, preprocessLang: style.lang })).errors, [])
})
