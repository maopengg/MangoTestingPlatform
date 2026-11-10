import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/plan')
const row = (fields = {}) => ({ id: 1, name: 'Example plan', status: 0, scope_type: 0,
  project_product: { id: 2, name: 'Example product', project: { id: 3, name: 'Example project' } },
  owner: { id: 4, name: 'Example owner' }, requirement_version: { id: 5, requirement_name: 'Example requirement', version_no: 2 },
  iteration: null, environment: '', build_version: '', remark: '', planned_start_time: null, planned_end_time: null,
  execution_stats: { executed: 0, total: 0, passed: 0, failed: 0, blocked: 0, skipped: 0, progress: 0, pass_rate: 0 }, ...fields })
const settle = async () => { await flush(); await new Promise(resolve => setImmediate(resolve)); await flush() }
function setup(overrides = {}, editor = false) {
  const hooks = { mount: [], stop: [], activate: [], unmount: [] }, calls = [], dialogs = [], notifications = []
  const route = vue.reactive({ path: '/functional-test/plan/index', fullPath: '/functional-test/plan/index', query: {} })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'example-test-token', selected_environment: 1 })
  const api = {
    getFunctionalPlans: async () => ({ data: [row()], totalSize: 42 }), getUserName: async () => ({ data: [{ key: 4, title: 'Owner' }] }),
    getFunctionalRequirements: async () => ({ data: [{ id: 5, name: 'Example requirement', version_no: 2 }] }),
    getFunctionalIterations: async () => ({ data: [{ id: 6, name: 'Example sprint', iteration_no: 'SPR-6' }] }),
    postFunctionalPlan: async () => ({ data: { id: 2 } }), putFunctionalPlan: async body => ({ data: { id: body.id } }), deleteFunctionalPlan: async () => ({}), ...overrides.api,
  }
  const f = harness(editor ? 'PlanEditor' : 'index', editor
    ? 'open,reset,save,form,visible,saving,saveError,recordId,requirements,iterations,requirementOptions,iterationOptions,ownerOptions,loadOptions,onScopeTypeChange,canCancel'
    : 'loadAll,loadPlans,loadUsers,loadEnums,rows,loading,readError,usersError,enumsError,usersLoading,filters,appliedQuery,pagination,onNavigationFilterChange,search,reset,editorRef,navigationCreateRef,openEditor,openRouteCreate,onSaved,removePlan,deletingIds,isBusy,goDetail,navigatingId,navigationError,contextKey', {
      base, props: { contextKey: 'A', users: [], scopeOptions: [{ key: 0, title: 'Requirement' }] },
      api: Object.fromEntries(Object.entries(api).map(([name, fn]) => [name, (...args) => { calls.push([name, ...args]); return fn(...args) }])),
      modules: {
        vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.stop.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
        'vue-router': { useRoute: () => route, useRouter: () => ({ push: overrides.push || (async () => {}) }) },
        '@/store/modules/user': { default: () => user },
        '@/store/modules/get-enum': { useEnum: () => ({ colors: {}, getEnum: overrides.getEnum || (async () => {}), functional_test_plan_scope_type: [{ key: 0, title: 'Requirement' }], functional_test_plan_status: [{ key: 0, title: 'Draft' }] }) },
        '@/hooks/table': { usePagination: callback => vue.reactive({ page: 1, pageSize: 20, pageCount: 0, onChange: callback, setTotalSize(total) { this.pageCount = total } }) },
        '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(kind => [kind, text => notifications.push([kind, text])])), Modal: { warning(config) { const handle = { closed: false, close() { handle.closed = true } }; dialogs.push({ config, handle }); return handle } } },
      },
    })
  return { ...f, hooks, calls, route, user, dialogs, notifications, cleanup() { hooks.unmount.forEach(fn => fn()); f.close() } }
}

test('list and route creation are independent of slow users and failed enums', async () => {
  const pending = deferred(), f = setup({ api: { getUserName: () => pending.promise }, getEnum: async () => { throw Error('Offline') } }), opened = []
  try {
    f.editorRef.value = { open: (...args) => opened.push(args), isSaving: () => false }
    f.route.query = { create: '1', project_product: '2', requirement_version: '5' }; f.route.fullPath += '?create=1&project_product=2&requirement_version=5'
    f.hooks.mount.forEach(fn => fn()); await settle()
    assert.equal(f.rows.value.length, 1); assert.equal(f.loading.value, false); assert.equal(f.pagination.pageCount, 42)
    assert.equal(f.usersLoading.value, true); assert.equal(f.enumsError.value, true)
    assert.deepEqual(opened, [[null, { productId: 2, requirementId: 5 }]])
    pending.resolve({ data: [] }); await settle()
  } finally { f.cleanup() }
})
test('multiple filters preserve zero, snapshots drive pagination, reset keeps product navigation', async () => {
  const f = setup()
  try {
    f.filters.name = 'Release'; f.filters.scope_type = [0, 2]; f.filters.status = [0, 1]
    await f.onNavigationFilterChange({ projectProduct: '2' })
    assert.deepEqual(f.calls.at(-1)[1], { project_product: 2, name: 'Release', scope_type__in: '0,2', status__in: '0,1', page: 1, pageSize: 20 })
    f.filters.name = 'Unsubmitted'; f.pagination.page = 2; await f.pagination.onChange(); assert.equal(f.calls.at(-1)[1].name, 'Release')
    await f.reset(); assert.deepEqual(f.calls.at(-1)[1], { project_product: 2, page: 1, pageSize: 20 })
  } finally { f.cleanup() }
})
test('latest list response wins; old page totals never overwrite the current page', async () => {
  const a = deferred(), b = deferred(); let count = 0
  const f = setup({ api: { getFunctionalPlans: () => (++count === 1 ? a : b).promise } })
  try {
    const first = f.loadPlans(), second = f.search(); b.resolve({ data: [row({ id: 2 })], totalSize: 2 }); await second
    a.resolve({ data: [row()], totalSize: 99 }); await first
    assert.equal(f.rows.value[0].id, 2); assert.equal(f.pagination.pageCount, 2)
  } finally { f.cleanup() }
})
test('bad or failed list responses keep current rows and can retry; total zero is preserved', async () => {
  let data = { data: [row()], totalSize: 0 }, f = setup({ api: { getFunctionalPlans: async () => { if (data instanceof Error) throw data; return data } } })
  try {
    await f.loadPlans(); assert.equal(f.pagination.pageCount, 0)
    for (const value of [Error('Offline'), { data: {}, totalSize: 1 }, { data: [], totalSize: -1 }]) {
      data = value; assert.equal(await f.loadPlans(), false); assert.equal(f.rows.value.length, 1); assert.equal(f.loading.value, false); assert.equal(f.readError.value, true)
    }
    data = { data: [], totalSize: 0 }; assert.equal(await f.loadPlans(), true); assert.deepEqual(f.rows.value, [])
  } finally { f.cleanup() }
})
for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`${field} A-B-A invalidates rows, filters and old responses`, async () => {
    const pending = deferred(), f = setup({ api: { getFunctionalPlans: () => pending.promise } })
    try {
      f.filters.name = 'Old'; const read = f.loadPlans(), original = f.user[field]
      f.user[field] = field === 'token' ? 'example-other-token' : 2; f.user[field] = original
      pending.resolve({ data: [row()], totalSize: 99 }); await read
      assert.deepEqual(f.rows.value, []); assert.equal(f.pagination.pageCount, 0); assert.equal(f.filters.name, '')
    } finally { f.cleanup() }
  })
}
test('mount and activation read once; inactive failures are ignored and activation restores', async () => {
  const pending = deferred(); let count = 0
  const f = setup({ api: { getFunctionalPlans: () => ++count === 1 ? pending.promise : Promise.resolve({ data: [row()], totalSize: 1 }) } })
  try {
    f.hooks.mount.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); assert.equal(count, 1)
    f.hooks.stop.forEach(fn => fn()); pending.reject(Error('Late')); await settle(); assert.equal(f.readError.value, false)
    f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(count, 2); assert.equal(f.rows.value.length, 1)
    f.hooks.unmount.forEach(fn => fn()); await f.loadAll(); assert.equal(count, 2)
  } finally { f.cleanup() }
})
test('route prefill opens once, rejects array IDs, and waits for an earlier physical save', async () => {
  const f = setup(), pending = vue.ref(true), opened = []
  try {
    f.editorRef.value = { open: (...args) => opened.push(args), isSaving: () => pending.value }
    f.route.query = { create: '1', project_product: ['2', '3'], requirement_version: '5' }; f.route.fullPath += '?create=1'
    f.hooks.mount.forEach(fn => fn()); await settle(); assert.equal(opened.length, 0)
    pending.value = false; await settle(); assert.deepEqual(opened, [[null, { productId: null, requirementId: 5 }]])
    f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(opened.length, 1)
  } finally { f.cleanup() }
})
test('obsolete route prefill is ignored and normal creation uses captured navigation defaults', async () => {
  const f = setup(), opened = []
  try {
    f.editorRef.value = { open: (...args) => opened.push(args), isSaving: () => false }
    f.route.query = { create: '1', project_product: '2' }; const opening = f.openRouteCreate()
    f.route.query = {}; f.route.fullPath += '?other=1'; await opening; assert.equal(opened.length, 0)
    f.navigationCreateRef.value = { getCreateDefaults: () => ({ projectProduct: '2', module: null }) }
    f.openEditor(); assert.deepEqual(opened, [[null, { productId: 2 }]])
  } finally { f.cleanup() }
})
test('delete snapshot deduplicates, keeps retry on failure, and backs off an emptied page', async () => {
  let fail = true, f = setup({ api: { deleteFunctionalPlan: async () => { if (fail) throw Error('Offline') } } })
  try {
    await f.loadPlans(); f.pagination.page = 2; const record = f.rows.value[0]
    f.removePlan(record); f.removePlan(record); record.id = 99
    assert.equal(f.dialogs.length, 1); assert.equal(await f.dialogs[0].config.onBeforeOk(), false)
    record.id = 1; fail = false; assert.equal(await f.dialogs[0].config.onBeforeOk(), true)
    assert.deepEqual(f.calls.filter(([name]) => name === 'deleteFunctionalPlan').map(([, id]) => id), [1, 1]); assert.equal(f.pagination.page, 1)
  } finally { f.cleanup() }
})
test('delete physical lock survives context reset; old success never notifies the new identity', async () => {
  const pending = deferred(), f = setup({ api: { deleteFunctionalPlan: () => pending.promise } })
  try {
    await f.loadPlans(); f.removePlan(f.rows.value[0]); const deleting = f.dialogs[0].config.onBeforeOk()
    assert.equal(f.dialogs[0].config.onBeforeCancel(), false); assert.equal(await f.dialogs[0].config.onBeforeOk(), false)
    f.user.roleId = 2; assert.equal(f.dialogs[0].handle.closed, true); assert.equal(f.deletingIds.has(1), true)
    pending.resolve({}); assert.equal(await deleting, false); assert.deepEqual(f.notifications, []); assert.equal(f.deletingIds.size, 0)
  } finally { f.cleanup() }
})
test('delete success is separate from a failed subsequent read', async () => {
  let failed = false, f = setup({ api: { getFunctionalPlans: async () => { if (failed) throw Error('Offline'); return { data: [row()], totalSize: 1 } } } })
  try {
    await f.loadPlans(); f.removePlan(f.rows.value[0]); failed = true
    assert.equal(await f.dialogs[0].config.onBeforeOk(), true); await settle()
    assert.equal(f.readError.value, true); assert.deepEqual(f.rows.value, []); assert.equal(f.notifications[0][0], 'success')
  } finally { f.cleanup() }
})
test('detail navigation checks ownership, deduplicates, preserves route and can retry failures', async () => {
  const pending = deferred(), calls = [], f = setup({ push: target => { calls.push(target); return pending.promise } })
  try {
    await f.loadPlans(); await f.goDetail(row({ id: 99 })); assert.equal(calls.length, 0)
    const navigation = f.goDetail(f.rows.value[0]); await f.goDetail(f.rows.value[0]); assert.deepEqual(calls, [{ path: '/functional-test/plan/details', query: { id: 1 } }])
    pending.reject(Error('Chunk offline')); await navigation; assert.equal(f.navigationError.value, true); assert.equal(f.navigatingId.value, null)
  } finally { f.cleanup() }
})

test('editor opens immediately, owns its draft, preserves fallback labels and resets on cancel/reopen', async () => {
  const slow = deferred(), f = setup({ api: { getFunctionalRequirements: () => slow.promise } }, true)
  try {
    const original = row(); f.open(original); assert.equal(f.visible.value, true); assert.equal(f.requirements.loading, true)
    f.form.name = 'Changed'; assert.equal(original.name, 'Example plan'); assert.equal(f.form.requirement_version, 5)
    assert.equal(f.requirementOptions.value[0].label, 'Example requirement · V2'); assert.equal(f.ownerOptions.value[0].title, 'Example owner')
    f.reset(); f.open(null, { productId: 3 }); assert.equal(f.form.name, ''); assert.equal(f.form.requirement_version, null)
    slow.resolve({ data: [] }); await settle(); assert.equal(f.requirementOptions.value.length, 0)
  } finally { f.cleanup() }
})
test('product A-B-A option races cannot restore old associations or overwrite current options', async () => {
  const old = deferred(), latest = deferred(); let count = 0
  const f = setup({ api: { getFunctionalRequirements: () => ++count === 1 ? old.promise : count === 3 ? latest.promise : Promise.resolve({ data: [] }) } }, true)
  try {
    f.open(row()); f.form.project_product = 3; f.form.project_product = 2
    assert.equal(f.form.requirement_version, null); assert.equal(f.form.iteration, null)
    latest.resolve({ data: [{ id: 8, name: 'Latest', version_no: 3 }] }); await settle()
    old.resolve({ data: [{ id: 5, name: 'Old', version_no: 2 }] }); await settle()
    assert.equal(f.requirementOptions.value[0].value, 8); assert.equal(f.requirements.loading, false)
  } finally { f.cleanup() }
})
test('option errors are independent, retain a retry, and clearing product stops obsolete results', async () => {
  let fail = true, f = setup({ api: { getFunctionalRequirements: async () => { if (fail) throw Error('Offline'); return { data: [{ id: 5, name: 'Requirement', version_no: 2 }] } } } }, true)
  try {
    f.open(row()); await settle(); assert.equal(f.requirements.error, true); assert.equal(f.iterations.options.length, 1); assert.equal(f.iterations.error, false)
    fail = false; await f.loadOptions('requirement'); assert.equal(f.requirements.error, false)
    f.form.project_product = null; await settle(); assert.deepEqual(f.requirements.options, []); assert.equal(f.requirements.loading, false); assert.equal(f.form.requirement_version, null)
  } finally { f.cleanup() }
})
test('scope changes clear irrelevant associations and payload sends only the applicable scope', async () => {
  const f = setup({}, true)
  try {
    f.open(row()); await settle(); f.form.scope_type = 1; f.form.scope_ref = 'Old'; f.onScopeTypeChange()
    assert.equal(f.form.requirement_version, null); assert.equal(f.form.scope_ref, '')
    f.form.iteration = 6; await f.save()
    const body = f.calls.find(([name]) => name === 'putFunctionalPlan')[1]
    assert.equal(body.iteration, 6); assert.equal(body.requirement_version, null); assert.equal('status' in body, false)
  } finally { f.cleanup() }
})
test('save freezes target and whitelist, converts cascade IDs and preserves explicit cleared dates', async () => {
  const pending = deferred(), f = setup({ api: { putFunctionalPlan: () => pending.promise } }, true)
  try {
    const original = row({ extra: 'metadata' }); f.open(original); await settle(); f.form.project_product = [3, '2']
    f.form.planned_start_time = ''; const save = f.save(); original.id = 99; f.form.name = 'Later'; await f.save(); f.open(null)
    const writes = f.calls.filter(([name]) => name === 'putFunctionalPlan'); assert.equal(writes.length, 1)
    assert.equal(writes[0][1].id, 1); assert.equal(writes[0][1].name, 'Example plan'); assert.equal(writes[0][1].project_product, 2)
    assert.equal(writes[0][1].planned_start_time, null); assert.equal(writes[0][1].planned_end_time, null)
    for (const key of ['status', 'extra', 'execution_stats', 'case_count', 'owner_name', 'update_time']) assert.equal(key in writes[0][1], false)
    assert.equal(f.canCancel(), false); assert.equal(f.exposed.isSaving(1), true)
    pending.resolve({ data: { id: 1 } }); await save; assert.equal(f.visible.value, false); assert.deepEqual(f.events, [['saved', 1]])
  } finally { f.cleanup() }
})
test('failed or unconfirmed saves keep the draft and permit retry', async () => {
  let response = Error('Offline'), f = setup({ api: { putFunctionalPlan: async () => { if (response instanceof Error) throw response; return response } } }, true)
  try {
    f.open(row()); await settle(); f.form.remark = 'Keep'; await f.save(); assert.equal(f.saveError.value, true); assert.equal(f.form.remark, 'Keep')
    response = { data: { id: 99 } }; await f.save(); assert.equal(f.visible.value, true); assert.deepEqual(f.events, [])
    response = { data: { id: 1 } }; await f.save(); assert.equal(f.visible.value, false); assert.equal(f.saving.value, false)
  } finally { f.cleanup() }
})
test('create validates required scope and delete conflicts before POST', async () => {
  const f = setup({}, true)
  try {
    f.open(null, { productId: 2, requirementId: 5 }); await settle(); await f.save(); assert.equal(f.calls.some(([name]) => name === 'postFunctionalPlan'), false)
    f.form.name = 'Create'; f.form.owner = 4; await f.save(); assert.equal(f.calls.find(([name]) => name === 'postFunctionalPlan')[1].id, undefined)
    f.open(row()); await settle(); f.props.busyIds = [1]; await f.save(); assert.equal(f.calls.some(([name]) => name === 'putFunctionalPlan'), false)
  } finally { f.cleanup() }
})
for (const scope of ['context', 'deactivate', 'unmount']) {
  test(`editor ${scope} discards late results but preserves the physical save lock`, async () => {
    const pending = deferred(), f = setup({ api: { putFunctionalPlan: () => pending.promise } }, true)
    try {
      f.open(row()); await settle(); const saving = f.save()
      if (scope === 'context') { f.props.contextKey = 'B'; f.props.contextKey = 'A' }
      else f.hooks[scope === 'deactivate' ? 'stop' : 'unmount'].forEach(fn => fn())
      f.open(null); assert.equal(f.visible.value, false); assert.equal(f.saving.value, true)
      pending.reject(Error('Late')); await saving; assert.equal(f.saveError.value, false); assert.equal(f.saving.value, false); assert.deepEqual(f.events, [])
    } finally { f.cleanup() }
  })
}
test('list and editor compile scripts, templates and scoped styles', async () => {
  for (const file of ['index.vue', 'components/PlanEditor.vue']) {
    const filename = path.join(base, file), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, []); const script = compileScript(descriptor, { id: file })
    assert.deepEqual(compileTemplate({ id: file, source: descriptor.template.content, filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ id: file, filename, source: style.content, scoped: true, preprocessLang: style.lang })).errors, [])
  }
})
