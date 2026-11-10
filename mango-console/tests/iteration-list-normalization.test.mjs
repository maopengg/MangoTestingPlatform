import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/iteration')
const row = (values = {}) => ({ id: 1, iteration_no: 'SPR-1', name: 'Example sprint', owner: { id: 4, name: 'Example owner' },
  project_product: { id: 10, name: 'Example product', project: { id: 2, name: 'Example project' } },
  status: 0, start_date: '2026-11-01', end_date: '2026-11-15', remark: '', ...values })
const settle = async () => { await flush(); await new Promise(resolve => setImmediate(resolve)); await flush() }
function setup(overrides = {}, editor = false) {
  const hooks = { mount: [], stop: [], activate: [], unmount: [] }, calls = [], dialogs = [], messages = []
  const route = vue.reactive({ path: '/functional-test/iteration/index', fullPath: '/functional-test/iteration/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'example-test-token', selected_environment: 1 })
  const api = {
    getFunctionalIterations: async () => ({ data: [row()], totalSize: 41 }),
    getUserName: async () => ({ data: [{ key: 4, title: 'Example owner' }] }),
    postFunctionalIteration: async () => ({ data: { id: 2 } }),
    putFunctionalIteration: async body => ({ data: { id: body.id } }),
    deleteFunctionalIteration: async () => ({ code: 200 }), ...overrides.api,
  }
  const wrapped = Object.fromEntries(Object.entries(api).map(([key, fn]) => [key, body => { calls.push([key, body]); return fn(body) }]))
  const f = harness(editor ? 'IterationEditor' : 'index', editor
    ? 'open,reset,save,form,visible,saving,saveError,recordId,ownerOptions,canCancel'
    : 'loadAll,loadRows,rows,loading,rowsRegion,usersRegion,enumsRegion,userOptions,statusOptions,filters,appliedQuery,pagination,search,reset,onNavigationFilterChange,navigationCreateRef,editorRef,openEditor,onSaved,removeRow,deletingIds,isBusy,goDetail,navigatingId,navigationError,contextKey', {
      base, api: wrapped, props: { contextKey: 'A', users: [], statusOptions: [] },
      modules: {
        vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
        'vue-router': { useRoute: () => route, useRouter: () => ({ push: overrides.push || (async () => {}) }) },
        '@/store/modules/user': { default: () => user },
        '@/store/modules/get-enum': { useEnum: () => ({ colors: {}, functional_test_iteration_status: [{ key: 0, title: 'Not started' }], getEnum: overrides.getEnum || (async () => {}) }) },
        '@/hooks/table': { usePagination: (callback) => vue.reactive({ page: 1, pageSize: 20, pageCount: 0, onChange: callback, setTotalSize(total) { this.pageCount = total } }) },
        '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(key => [key, text => messages.push([key, text])])), Modal: { warning(config) { const handle = { closed: false, close() { handle.closed = true } }; dialogs.push({ config, handle }); return handle } } },
      },
    })
  return { ...f, hooks, route, user, calls, dialogs, messages, cleanup() { hooks.unmount.forEach(fn => fn()); f.close() } }
}

test('list, user and enum reads are independent, including failed or slow options', async () => {
  const slow = deferred(), f = setup({ api: { getUserName: () => slow.promise }, getEnum: async () => { throw Error('Offline') } })
  try {
    const loading = f.loadAll(); await settle()
    assert.equal(f.rows.value.length, 1); assert.equal(f.pagination.pageCount, 41); assert.equal(f.loading.value, false)
    assert.equal(f.usersRegion.loading.value, true); assert.equal(f.enumsRegion.error.value, true)
    slow.resolve({ data: [{ key: 4, title: 'Owner' }] }); await loading
    assert.equal(f.userOptions.value[0].title, 'Owner')
  } finally { f.cleanup() }
})
test('search serializes multi-selection, preserves zero status and pagination uses the applied query', async () => {
  const f = setup()
  try {
    f.filters.name = 'Sprint'; f.filters.status = [0, 1]; f.filters.owner = [4, 5]
    await f.onNavigationFilterChange({ projectProduct: '10' })
    assert.deepEqual(f.calls.at(-1)[1], { name: 'Sprint', project_product: 10, status__in: '0,1', owner__in: '4,5', page: 1, pageSize: 20 })
    f.filters.name = 'Unsubmitted'; f.pagination.page = 2; f.pagination.pageSize = 50; await f.pagination.onChange()
    assert.equal(f.calls.at(-1)[1].name, 'Sprint'); assert.equal(f.calls.at(-1)[1].page, 2)
    await f.reset(); assert.deepEqual(f.calls.at(-1)[1], { project_product: 10, page: 1, pageSize: 50 })
  } finally { f.cleanup() }
})
test('out-of-order search responses cannot overwrite current rows or page totals', async () => {
  const a = deferred(), b = deferred(); let count = 0
  const f = setup({ api: { getFunctionalIterations: () => (++count === 1 ? a : b).promise } })
  try {
    const first = f.loadRows(), second = f.search()
    b.resolve({ data: [row({ id: 2 })], totalSize: 2 }); await second
    a.resolve({ data: [row()], totalSize: 99 }); await first
    assert.equal(f.rows.value[0].id, 2); assert.equal(f.pagination.pageCount, 2)
  } finally { f.cleanup() }
})
test('failed and malformed lists retain current data, clear loading, and allow retry', async () => {
  let response = { data: [row()], totalSize: 0 }, f = setup({ api: { getFunctionalIterations: async () => {
    if (response instanceof Error) throw response; return response
  } } })
  try {
    await f.loadRows(); assert.equal(f.pagination.pageCount, 0)
    for (const failure of [Error('Offline'), { data: {}, totalSize: 1 }, { data: [], totalSize: -1 }]) {
      response = failure; assert.equal(await f.loadRows(), false); assert.equal(f.rows.value.length, 1)
      assert.equal(f.loading.value, false); assert.equal(f.rowsRegion.error.value, true)
    }
    response = { data: [], totalSize: 0 }; assert.equal(await f.loadRows(), true); assert.deepEqual(f.rows.value, [])
  } finally { f.cleanup() }
})
for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`list invalidates stale responses after ${field} A-B-A changes`, async () => {
    const pending = deferred(), f = setup({ api: { getFunctionalIterations: () => pending.promise } })
    try {
      const read = f.loadRows(), previous = f.user[field]
      f.user[field] = field === 'token' ? 'example-other-token' : 2; f.user[field] = previous
      pending.resolve({ data: [row()], totalSize: 80 }); await read
      assert.deepEqual(f.rows.value, []); assert.equal(f.pagination.pageCount, 0); assert.equal(f.loading.value, false)
    } finally { f.cleanup() }
  })
}
test('KeepAlive mounts once, discards inactive responses, reloads on activation and stops on unmount', async () => {
  const pending = deferred(); let count = 0
  const f = setup({ api: { getFunctionalIterations: () => ++count === 1 ? pending.promise : Promise.resolve({ data: [row()], totalSize: 1 }) } })
  try {
    f.hooks.mount.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); assert.equal(count, 1)
    f.hooks.stop.forEach(fn => fn()); pending.reject(Error('Late')); await settle()
    assert.equal(f.rowsRegion.error.value, false); assert.deepEqual(f.rows.value, [])
    f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(count, 2); assert.equal(f.rows.value.length, 1)
    f.hooks.unmount.forEach(fn => fn()); await f.loadAll(); assert.equal(count, 2)
  } finally { f.cleanup() }
})
test('editor opens only owned rows and captures navigation product for creation', async () => {
  const f = setup(), opened = []
  try {
    await f.loadRows(); f.editorRef.value = { open: (...args) => opened.push(args), isSaving: () => false }
    f.navigationCreateRef.value = { getCreateDefaults: () => ({ projectProduct: '10', module: null }) }
    f.openEditor(); assert.deepEqual(opened[0], [null, 10])
    f.openEditor(f.rows.value[0]); assert.equal(opened.length, 2)
    f.openEditor(row({ id: 99 })); assert.equal(opened.length, 2)
  } finally { f.cleanup() }
})
test('delete confirmation deduplicates, preserves retry on failure, and handles the last page', async () => {
  let fail = true, f = setup({ api: { deleteFunctionalIteration: async () => { if (fail) throw Error('Offline') } } })
  try {
    await f.loadRows(); f.pagination.page = 3
    f.removeRow(f.rows.value[0]); f.removeRow(f.rows.value[0]); assert.equal(f.dialogs.length, 1)
    assert.equal(await f.dialogs[0].config.onBeforeOk(), false); assert.equal(f.rows.value.length, 1); assert.equal(f.deletingIds.size, 0)
    fail = false; assert.equal(await f.dialogs[0].config.onBeforeOk(), true)
    assert.equal(f.pagination.page, 2); assert.equal(f.calls.filter(([key]) => key === 'deleteFunctionalIteration').length, 2)
  } finally { f.cleanup() }
})
test('delete keeps its physical lock during context changes and suppresses old success', async () => {
  const pending = deferred(), f = setup({ api: { deleteFunctionalIteration: () => pending.promise } })
  try {
    await f.loadRows(); f.removeRow(f.rows.value[0]); const removing = f.dialogs[0].config.onBeforeOk()
    assert.equal(f.deletingIds.has(1), true); assert.equal(await f.dialogs[0].config.onBeforeOk(), false)
    f.user.roleId = 2; assert.equal(f.dialogs[0].handle.closed, true)
    pending.resolve({}); assert.equal(await removing, false); assert.deepEqual(f.messages, []); assert.equal(f.deletingIds.size, 0)
  } finally { f.cleanup() }
})
test('delete success is not changed into failure when the subsequent list refresh fails', async () => {
  let failRead = false, f = setup({ api: { getFunctionalIterations: async () => { if (failRead) throw Error('Offline'); return { data: [row()], totalSize: 1 } } } })
  try {
    await f.loadRows(); f.removeRow(f.rows.value[0]); failRead = true
    assert.equal(await f.dialogs[0].config.onBeforeOk(), true); await settle()
    assert.equal(f.rowsRegion.error.value, true); assert.equal(f.messages[0][0], 'success'); assert.equal(f.messages.length, 2); assert.equal(f.messages[1][0], 'error')
  } finally { f.cleanup() }
})
test('detail navigation has physical deduplication, failure feedback and retry', async () => {
  const pending = deferred(); let calls = 0
  const f = setup({ push: () => { ++calls; return pending.promise } })
  try {
    await f.loadRows(); const nav = f.goDetail(f.rows.value[0]); await f.goDetail(f.rows.value[0]); assert.equal(calls, 1)
    pending.reject(Error('Chunk offline')); await nav
    assert.equal(f.navigationError.value, true); assert.equal(f.navigatingId.value, null)
    await f.goDetail(f.rows.value[0]); assert.equal(calls, 2)
  } finally { f.cleanup() }
})
test('editor cancel, reopen, owner fallback and new form do not mutate source or retain metadata', () => {
  const f = setup({}, true)
  try {
    const source = row({ extra: 'metadata' }); f.open(source); f.form.name = 'Edited'
    assert.equal(source.name, 'Example sprint'); assert.deepEqual(f.ownerOptions.value, [{ key: 4, title: 'Example owner' }])
    f.reset(); f.open(null, 10); assert.equal(f.form.name, ''); assert.equal(f.form.project_product, 10); assert.equal(f.form.owner, null)
    assert.equal('extra' in f.form, false); assert.deepEqual(f.ownerOptions.value, [])
  } finally { f.cleanup() }
})
test('editor sends a captured field whitelist with real product ID, status zero and immutable target', async () => {
  const pending = deferred(), f = setup({ api: { putFunctionalIteration: () => pending.promise } }, true)
  try {
    const source = row({ extra: 'metadata' }); f.open(source); f.form.project_product = [2, '10']
    const saving = f.save(); source.id = 99; f.form.name = 'Later edit'; await f.save(); f.open(null, 20)
    assert.equal(f.calls.length, 1); assert.equal(f.canCancel(), false); assert.equal(f.exposed.isSaving(1), true)
    assert.deepEqual(f.calls[0][1], { id: 1, iteration_no: 'SPR-1', name: 'Example sprint', project_product: 10, owner: 4, start_date: '2026-11-01', end_date: '2026-11-15', status: 0, remark: '' })
    pending.resolve({ data: { id: 1 } }); await saving
    assert.equal(f.visible.value, false); assert.deepEqual(f.events, [['saved', 1]])
  } finally { f.cleanup() }
})
test('editor failed writes retain draft and retry; wrong acknowledgement never closes it', async () => {
  let response = Error('Offline'), f = setup({ api: { putFunctionalIteration: async () => { if (response instanceof Error) throw response; return response } } }, true)
  try {
    f.open(row()); f.form.remark = 'Keep input'; await f.save()
    assert.equal(f.saveError.value, true); assert.equal(f.form.remark, 'Keep input'); assert.equal(f.saving.value, false)
    response = { data: { id: 99 } }; await f.save(); assert.equal(f.visible.value, true); assert.deepEqual(f.events, [])
    response = { data: { id: 1 } }; await f.save(); assert.equal(f.visible.value, false)
  } finally { f.cleanup() }
})
test('open editor cannot save while the same Sprint is being deleted', async () => {
  const f = setup({}, true)
  try {
    f.open(row()); f.props.busyIds = [1]; await f.save()
    assert.equal(f.calls.length, 0); assert.equal(f.visible.value, true)
    f.props.busyIds = []; await f.save(); assert.equal(f.calls.length, 1)
  } finally { f.cleanup() }
})
test('new editor uses POST, validates required values and accepts only the confirmed record', async () => {
  const f = setup({}, true)
  try {
    f.open(null, 10); await f.save(); assert.equal(f.calls.length, 0)
    Object.assign(f.form, row(), { project_product: 10, owner: 4 }); delete f.form.id
    await f.save(); assert.equal(f.calls[0][0], 'postFunctionalIteration'); assert.equal('id' in f.calls[0][1], false)
    assert.deepEqual(f.events, [['saved', 2]])
  } finally { f.cleanup() }
})
for (const event of ['context', 'deactivate', 'unmount']) {
  test(`editor ${event} clears draft and ignores late responses without releasing pending writes early`, async () => {
    const pending = deferred(), f = setup({ api: { putFunctionalIteration: () => pending.promise } }, true)
    try {
      f.open(row()); const save = f.save()
      if (event === 'context') { f.props.contextKey = 'B'; f.props.contextKey = 'A' }
      else f.hooks[event === 'deactivate' ? 'stop' : 'unmount'].forEach(fn => fn())
      f.open(row({ id: 2 })); assert.equal(f.visible.value, false); assert.equal(f.saving.value, true)
      pending.reject(Error('Late')); await save
      assert.equal(f.saveError.value, false); assert.equal(f.saving.value, false); assert.deepEqual(f.events, [])
    } finally { f.cleanup() }
  })
}
test('page and editor compile their scripts, templates and scoped styles', async () => {
  for (const file of ['index.vue', 'components/IterationEditor.vue']) {
    const filename = path.join(base, file), source = readFileSync(filename, 'utf8'), { descriptor, errors } = parse(source)
    assert.deepEqual(errors, []); const script = compileScript(descriptor, { id: file })
    assert.deepEqual(compileTemplate({ id: file, source: descriptor.template.content, filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ id: file, filename, source: style.content, scoped: true, preprocessLang: style.lang })).errors, [])
  }
})
