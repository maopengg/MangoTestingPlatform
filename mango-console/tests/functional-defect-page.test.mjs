import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/defect')
const paginationModule = {}
new Function('exports', 'require', ts.transpileModule(readFileSync('src/hooks/table.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText)(paginationModule, id => { assert.equal(id, 'vue'); return vue })
const stats = (n = 1) => ({ open_count: n, my_pending_count: n, serious_count: n, resolved_pending_count: n })
const row = (extra = {}) => ({ id: 11, defect_no: 'DEF-11', title: 'Example defect', status: 2, priority: 1, severity: 2, source_type: 0, defect_type: 0,
  project_product: { id: 2, name: 'Product', project: { id: 1, name: 'Project' } }, module: { id: 3, name: 'Leaf', full_path: 'Parent/Child/Leaf' },
  assignee: { id: 4, name: 'Owner' }, reporter: { id: 5, name: 'Reporter' }, reproduce_steps: [], attachment_file_ids: [], relations: [], ...extra })
function fixture(api = {}, options = {}) {
  const originalStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  const stored = new Map(options.saved === undefined ? [] : [['mango-functional-defect-columns', options.saved]])
  const storage = { fail: options.storageFailure ?? false }
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: {
    getItem: key => { if (storage.fail) throw Error('Storage unavailable'); return stored.get(key) ?? null },
    setItem: (key, value) => { if (storage.fail) throw Error('Storage unavailable'); stored.set(key, value) },
  } })
  const hooks = { mount: [], activate: [], stop: [], unmount: [] }, reads = [], statsReads = [], planReads = [], writes = [], deletes = [], confirmations = []
  const route = vue.reactive({ fullPath: '/functional-test/defect/index', query: {} }), user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 1 })
  const enums = Object.fromEntries(['functional_test_defect_source', 'functional_test_defect_type', 'functional_test_defect_severity', 'functional_test_defect_priority', 'functional_test_defect_status'].map(key => [key, [0, 1, 2, 3, 4, 5].map(key => ({ key, title: `Option ${key}` }))]))
  enums.colors = []; enums.getEnum = options.getEnum ?? (async () => {})
  const f = harness('index', 'rows,stats,filters,appliedFilters,pagination,loading,listError,statsLoading,statsError,usersLoading,usersError,enumsLoading,enumsError,searchPlansLoading,searchPlansError,userOptions,searchPlanOptions,loadRows,refreshStats,refreshAll,loadUsers,loadEnums,loadSearchPlans,search,reset,onNavigationFilterChange,onEditorSaved,onTransitionSaved,quickUpdate,quickStatus,removeRow,rowBusy,mutationError,configuredColumns,columnStorageError,setColumnVisible,moveColumn,resetColumns,saveColumns,editorDrawer,transitionDialog,retestDialog,openEditor,openCurrentRoute', {
    base, api: {
      getFunctionalDefects: async query => { reads.push(query); return api.getFunctionalDefects ? api.getFunctionalDefects(query) : { data: [row()], totalSize: 45 } },
      getFunctionalDefectStats: async query => { statsReads.push(query); return api.getFunctionalDefectStats ? api.getFunctionalDefectStats(query) : { data: stats() } },
      getUserName: api.getUserName ?? (async () => ({ data: [{ key: 4, title: 'Owner' }] })),
      getFunctionalPlans: async query => { planReads.push(query); return api.getFunctionalPlans ? api.getFunctionalPlans(query) : { data: [{ id: 8, name: 'Plan' }] } },
      putFunctionalDefect: async body => { writes.push(body); return api.putFunctionalDefect ? api.putFunctionalDefect(body) : { data: row(body) } },
      transitionFunctionalDefect: async body => { writes.push(body); return api.transitionFunctionalDefect ? api.transitionFunctionalDefect(body) : { data: row(body) } },
      deleteFunctionalDefect: async id => { deletes.push(id); return api.deleteFunctionalDefect?.(id) },
    }, modules: {
      vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.stop.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      'vue-router': { useRoute: () => route }, '@/hooks/table': paginationModule,
      '@/store/modules/user': { default: () => user }, '@/store/modules/get-enum': { useEnum: () => enums },
      '@arco-design/web-vue': { Modal: { warning: config => { const dialog = { config, closed: false, close() { this.closed = true; config.onClose?.() } }; confirmations.push(dialog); return dialog } } },
    },
  })
  return { ...f, hooks, reads, statsReads, planReads, writes, deletes, confirmations, route, user, storage, stored,
    mount: async () => { hooks.mount.forEach(fn => fn()); await flush() },
    cleanup: () => { hooks.unmount.forEach(fn => fn()); f.close(); if (originalStorage) Object.defineProperty(globalThis, 'localStorage', originalStorage); else delete globalThis.localStorage },
  }
}

test('list and statistics finish independently, preserving rows when stats fail and allowing stats retry', async () => {
  const slow = deferred(); let fail = true
  const f = fixture({ getFunctionalDefectStats: () => fail ? slow.promise : Promise.resolve({ data: stats(9) }) })
  try {
    const reading = f.refreshAll(); await flush()
    assert.equal(f.loading.value, false); assert.equal(f.rows.value[0].id, 11); assert.equal(f.pagination.pageCount, 45)
    assert.equal(f.statsLoading.value, true); slow.reject(Error('Offline')); await reading
    assert.equal(f.statsError.value, true); assert.equal(f.listError.value, false); assert.equal(f.rows.value.length, 1)
    fail = false; await f.refreshStats(); assert.equal(f.stats.value.open_count, 9); assert.equal(f.statsError.value, false)
  } finally { f.cleanup() }
})

test('list failure is retryable and cannot prevent successful statistics', async () => {
  let fail = false
  const f = fixture({ getFunctionalDefects: async () => { if (fail) throw Error('Offline'); return { data: [row()], totalSize: 45 } } })
  try {
    await f.refreshAll(); fail = true; await f.refreshAll()
    assert.equal(f.listError.value, true); assert.equal(f.loading.value, false); assert.equal(f.rows.value.length, 1)
    assert.equal(f.stats.value.open_count, 1); assert.equal(f.statsError.value, false)
    fail = false; await f.loadRows(); assert.equal(f.listError.value, false)
  } finally { f.cleanup() }
})

test('search captures applied filters, real product IDs, dates and zero values for subsequent pagination', async () => {
  const f = fixture()
  try {
    Object.assign(f.filters, { project_product: [1, 2], module: 3, status: 0, severity: 0, keyword: '', create_range: ['2026-01-01', '2026-01-02'] })
    await f.search(); const query = f.reads[0]
    assert.deepEqual(query, { project_product: 2, module: 3, status: 0, severity: 0, create_time_start: '2026-01-01', create_time_end: '2026-01-02', page: 1, pageSize: 20 })
    f.filters.status = 5; f.filters.create_range[0] = 'Changed'; f.pagination.page = 2; await f.pagination.onChange()
    assert.equal(f.reads.at(-1).status, 0); assert.equal(f.reads.at(-1).create_time_start, '2026-01-01'); assert.equal(f.reads.at(-1).page, 2)
    await f.reset(); assert.equal(f.reads.at(-1).project_product, 2); assert.equal(f.reads.at(-1).module, 3); assert.equal('status' in f.reads.at(-1), false)
  } finally { f.cleanup() }
})

test('A to B to A search drops an old response and does not release the current loading', async () => {
  const first = deferred(), latest = deferred(); let calls = 0
  const f = fixture({ getFunctionalDefects: () => ++calls === 1 ? first.promise : latest.promise })
  try {
    f.filters.keyword = 'A'; const one = f.search(); f.filters.keyword = 'B'; const two = f.search(); f.filters.keyword = 'A'; const three = f.search()
    first.resolve({ data: [row({ id: 99 })], totalSize: 1 }); await one
    assert.equal(f.loading.value, true); assert.deepEqual(f.rows.value, [])
    latest.resolve({ data: [row({ id: 22 })], totalSize: 8 }); await Promise.all([two, three])
    assert.equal(f.rows.value[0].id, 22); assert.equal(f.pagination.pageCount, 8); assert.equal(f.loading.value, false)
  } finally { f.cleanup() }
})

test('navigation statistics and source plan requests cannot overwrite a newer product scope', async () => {
  const oldStats = deferred(), newStats = deferred(), oldPlans = deferred(), newPlans = deferred(); let s = 0, p = 0
  const f = fixture({ getFunctionalDefectStats: () => ++s === 1 ? oldStats.promise : newStats.promise, getFunctionalPlans: () => ++p === 1 ? oldPlans.promise : newPlans.promise })
  try {
    const old = f.onNavigationFilterChange({ projectProduct: 2, module: 3 }); await flush()
    const fresh = f.onNavigationFilterChange({ projectProduct: 4, module: null }); await flush()
    oldStats.resolve({ data: stats(99) }); oldPlans.resolve({ data: [{ id: 99, name: 'Old plan' }] }); await old
    assert.equal(f.statsLoading.value, true); assert.equal(f.searchPlansLoading.value, true); assert.deepEqual(f.searchPlanOptions.value, [])
    newStats.resolve({ data: stats(2) }); newPlans.resolve({ data: [{ id: 8, name: 'New plan' }] }); await fresh; await flush()
    assert.equal(f.stats.value.open_count, 2); assert.equal(f.searchPlanOptions.value[0].label, 'New plan')
    assert.deepEqual(f.statsReads.at(-1), { project_product: 4 }); assert.equal(f.planReads.at(-1).project_product, 4)
  } finally { f.cleanup() }
})

test('identity changes clear previous assets/options and reject late results including A to B to A', async () => {
  const old = deferred(), fresh = deferred(); let calls = 0
  const f = fixture({ getFunctionalDefects: () => ++calls === 1 ? old.promise : fresh.promise })
  try {
    await f.mount(); f.filters.keyword = 'Old'; f.user.roleId = 2; f.user.roleId = 1
    assert.deepEqual(f.rows.value, []); assert.equal(f.pagination.pageCount, 0); assert.equal(f.filters.keyword, '')
    old.resolve({ data: [row({ id: 99 })], totalSize: 1 }); await flush()
    assert.equal(f.loading.value, true); assert.deepEqual(f.rows.value, [])
    fresh.resolve({ data: [row({ id: 22 })], totalSize: 4 }); await flush()
    assert.equal(f.rows.value[0].id, 22); assert.equal(f.pagination.pageCount, 4)
  } finally { f.cleanup() }
})

test('route detail opening waits for updated child props and only opens the latest route', async () => {
  const f = fixture(), opened = []
  try {
    f.editorDrawer.value = { openById: async id => opened.push(id), open: async () => {}, openFromRoute: async () => {} }
    f.route.query = { defect_id: '11' }; f.hooks.mount.forEach(fn => fn())
    f.route.query = { defect_id: '22' }; f.route.fullPath = '/functional-test/defect/index?defect_id=22'; await flush()
    assert.deepEqual(opened, [22]); await f.openCurrentRoute(); assert.deepEqual(opened, [22])
    f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await flush(); assert.deepEqual(opened, [22])
  } finally { f.cleanup() }
})

test('cached deactivation ignores old reads and initial activation does not duplicate mount requests', async () => {
  const pending = deferred(), f = fixture({ getFunctionalDefects: () => pending.promise })
  try {
    await f.mount(); f.hooks.activate.forEach(fn => fn()); assert.equal(f.reads.length, 1)
    f.hooks.stop.forEach(fn => fn()); pending.resolve({ data: [row()], totalSize: 1 }); await flush()
    assert.deepEqual(f.rows.value, []); assert.equal(f.loading.value, false)
    f.hooks.activate.forEach(fn => fn()); await flush(); assert.equal(f.reads.length, 2); assert.equal(f.rows.value.length, 1)
    f.hooks.unmount.forEach(fn => fn()); await f.pagination.onChange(); assert.equal(f.reads.length, 2); assert.equal(f.loading.value, false)
  } finally { f.cleanup() }
})

test('users and enum failure do not block the list and each has retry feedback', async () => {
  let fail = true
  const f = fixture({ getUserName: async () => { if (fail) throw Error('Offline'); return { data: [{ key: 4, title: 'Owner' }] } } }, { getEnum: async () => { if (fail) throw Error('Offline') } })
  try {
    await f.mount(); assert.equal(f.rows.value.length, 1); assert.equal(f.usersError.value, true); assert.equal(f.enumsError.value, true)
    assert.equal(f.usersLoading.value, false); assert.equal(f.enumsLoading.value, false)
    fail = false; await Promise.all([f.loadUsers(), f.loadEnums()]); assert.equal(f.usersError.value, false); assert.equal(f.enumsError.value, false); assert.equal(f.userOptions.value[0].key, 4)
  } finally { f.cleanup() }
})

test('saving reloads the canonical list and updates the actual public pagination total', async () => {
  let saved = false
  const f = fixture({ getFunctionalDefects: async () => ({ data: [row({ id: saved ? 22 : 11 })], totalSize: saved ? 46 : 45 }) })
  try {
    await f.refreshAll(); assert.equal(f.pagination.pageCount, 45); assert.equal('total' in f.pagination, false)
    saved = true; await f.onEditorSaved({ record: { id: 22 }, created: true })
    assert.equal(f.pagination.pageCount, 46); assert.equal(f.rows.value[0].id, 22)
  } finally { f.cleanup() }
})

test('malformed column storage recovers defaults, enforces navigation order and retries failed storage writes', async () => {
  const f = fixture({}, { saved: '{broken', storageFailure: true })
  try {
    await f.mount(); assert.equal(f.columnStorageError.value, true); assert.equal(f.rows.value.length, 1)
    f.storage.fail = false; f.saveColumns(); assert.equal(f.columnStorageError.value, false)
    const config = f.load('config.ts'), restored = config.restoreDefectColumns([{ key: 'actions', visible: false }, { key: 'module', visible: false }, { key: 'title', visible: false }, { key: 'title' }, { key: 'unknown' }, null])
    assert.deepEqual(restored.slice(-3).map(config.defectColumnKey), ['project_product', 'module', 'actions'])
    assert.ok(restored.slice(-3).every(column => column.visible !== false)); assert.equal(restored.filter(column => column.dataIndex === 'title').length, 1)
    const fixedIndex = f.configuredColumns.value.findIndex(column => column.slotName === 'actions'); f.setColumnVisible(fixedIndex, false); f.moveColumn(fixedIndex, -1)
    assert.equal(f.configuredColumns.value.at(-1).slotName, 'actions'); assert.notEqual(f.configuredColumns.value.at(-1).visible, false)
    f.setColumnVisible(0, false); await flush(); assert.equal(JSON.parse(f.stored.get('mango-functional-defect-columns'))[0].visible, false)
  } finally { f.cleanup() }
})

test('quick edits await acknowledgement, reject duplicates and separate later stats failure from write success', async () => {
  const pending = deferred(); let statsFail = false
  const f = fixture({ putFunctionalDefect: () => pending.promise, getFunctionalDefectStats: async () => { if (statsFail) throw Error('Stats unavailable'); return { data: stats() } } })
  try {
    await f.refreshAll(); const original = f.rows.value[0], writing = f.quickUpdate(original, 'priority', 0)
    assert.equal(original.priority, 1); assert.equal(f.rowBusy.get(11).kind, 'priority')
    await f.quickUpdate(original, 'severity', 0); assert.equal(f.writes.length, 1)
    statsFail = true; pending.resolve({ data: row({ priority: 0 }) }); await writing; await flush()
    assert.equal(f.rows.value[0].priority, 0); assert.equal(f.mutationError.value, ''); assert.equal(f.statsError.value, true); assert.equal(f.rowBusy.size, 0)
  } finally { f.cleanup() }
})

test('failed assignee edits keep the original display object and can be retried or cleared', async () => {
  let fail = true
  const f = fixture({ putFunctionalDefect: async body => { if (fail) throw Error('Rejected'); return { data: row({ assignee: body.assignee === null ? null : { id: body.assignee, name: 'New owner' } }) } } })
  try {
    await f.refreshAll(); await f.quickUpdate(f.rows.value[0], 'assignee', 8)
    assert.deepEqual(f.rows.value[0].assignee, { id: 4, name: 'Owner' }); assert.ok(f.mutationError.value); assert.equal(f.rowBusy.size, 0)
    fail = false; await f.quickUpdate(f.rows.value[0], 'assignee', 8); assert.equal(f.rows.value[0].assignee.name, 'New owner')
    await f.quickUpdate(f.rows.value[0], 'assignee', undefined); assert.equal(f.writes.at(-1).assignee, null); assert.equal(f.rows.value[0].assignee, null)
  } finally { f.cleanup() }
})

test('a late read cannot overwrite an acknowledged quick edit', async () => {
  const write = deferred(), read = deferred(); let calls = 0
  const f = fixture({ putFunctionalDefect: () => write.promise, getFunctionalDefects: () => ++calls === 1 ? Promise.resolve({ data: [row()], totalSize: 1 }) : read.promise })
  try {
    await f.refreshAll(); const writing = f.quickUpdate(f.rows.value[0], 'priority', 0), reading = f.loadRows()
    write.resolve({ data: row({ priority: 0 }) }); await writing
    read.resolve({ data: [row({ priority: 1 })], totalSize: 1 }); await reading
    assert.equal(f.rows.value[0].priority, 0); assert.equal(f.loading.value, false)
  } finally { f.cleanup() }
})

test('identity change keeps physical write locks but rejects old acknowledgements and errors', async () => {
  const pending = deferred(), f = fixture({ putFunctionalDefect: () => pending.promise })
  try {
    await f.mount(); const writing = f.quickUpdate(f.rows.value[0], 'priority', 0)
    f.user.roleId = 2; await flush(); assert.equal(f.rowBusy.has(11), true)
    await f.quickUpdate(f.rows.value[0], 'priority', 0); assert.equal(f.writes.length, 1)
    pending.resolve({ data: row({ priority: 0 }) }); await writing
    assert.equal(f.rows.value[0].priority, 1); assert.equal(f.rowBusy.size, 0); assert.equal(f.mutationError.value, '')
  } finally { f.cleanup() }
})

test('status transitions needing fields open the window while simple transitions use the direct endpoint', async () => {
  const f = fixture(), opened = []
  try {
    await f.refreshAll(); f.transitionDialog.value = { open: (record, target) => opened.push([record.id, target]) }
    await f.quickStatus(f.rows.value[0], 3); assert.deepEqual(opened, [[11, 3]]); assert.equal(f.writes.length, 0)
    f.rows.value[0].status = 0; await f.quickStatus(f.rows.value[0], 1)
    assert.deepEqual(f.writes, [{ id: 11, status: 1 }]); assert.equal(f.rows.value[0].status, 1)
    await f.quickStatus(f.rows.value[0], 5); assert.equal(f.writes.length, 1)
  } finally { f.cleanup() }
})

test('delete confirmation retries failures, prevents duplicate writes and closes independently of read failures', async () => {
  let fail = true, readsFail = false
  const pending = deferred()
  const f = fixture({ deleteFunctionalDefect: async () => { if (fail) throw Error('Rejected'); return pending.promise }, getFunctionalDefects: async () => { if (readsFail) throw Error('Offline'); return { data: [row()], totalSize: 1 } } })
  try {
    await f.refreshAll(); f.removeRow(f.rows.value[0]); const dialog = f.confirmations[0]
    assert.equal(await dialog.config.onBeforeOk(), false); assert.equal(f.mutationError.value, '缺陷删除失败，请重试')
    fail = false; const deleting = dialog.config.onBeforeOk(); assert.equal(await dialog.config.onBeforeOk(), false)
    assert.equal(f.rowBusy.get(11).kind, 'delete'); readsFail = true; pending.resolve(); assert.equal(await deleting, true)
    dialog.close(); await flush(); assert.equal(f.rows.value.length, 0); assert.equal(f.pagination.pageCount, 0)
    assert.equal(f.listError.value, true); assert.equal(f.rowBusy.size, 0); assert.equal(f.deletes.length, 2)
  } finally { f.cleanup() }
})

test('scope changes close delete confirmations and make their captured callbacks inert', async () => {
  const f = fixture()
  try {
    await f.refreshAll(); f.removeRow(f.rows.value[0]); const dialog = f.confirmations[0]
    f.filters.keyword = 'New'; await f.search(); assert.equal(dialog.closed, true)
    assert.equal(await dialog.config.onBeforeOk(), false); assert.deepEqual(f.deletes, [])
  } finally { f.cleanup() }
})

test('malformed list and statistics responses remain retryable without replacing known data', async () => {
  let malformed = false
  const f = fixture({ getFunctionalDefects: async () => ({ data: malformed ? {} : [row()], totalSize: 1 }), getFunctionalDefectStats: async () => ({ data: malformed ? {} : stats(8) }) })
  try {
    await f.refreshAll(); malformed = true; await f.refreshAll()
    assert.equal(f.listError.value, true); assert.equal(f.statsError.value, true)
    assert.equal(f.rows.value[0].id, 11); assert.equal(f.stats.value.open_count, 8)
    malformed = false; await f.refreshAll(); assert.equal(f.listError.value, false); assert.equal(f.statsError.value, false)
  } finally { f.cleanup() }
})

test('window physical saves block same-record quick writes and deletion until the window releases them', async () => {
  const f = fixture(); let locked = true
  try {
    await f.refreshAll(); f.editorDrawer.value = { isSaving: id => locked && id === 11, open: async () => {}, openById: async () => {}, openFromRoute: async () => {} }
    await f.quickUpdate(f.rows.value[0], 'priority', 0); f.removeRow(f.rows.value[0]); await f.quickStatus(f.rows.value[0], 3)
    assert.deepEqual(f.writes, []); assert.deepEqual(f.confirmations, [])
    locked = false; await f.quickUpdate(f.rows.value[0], 'priority', 0); assert.equal(f.writes.length, 1)
  } finally { f.cleanup() }
})

test('wrong-record write acknowledgement and late failure cannot corrupt current rows', async () => {
  let wrong = true
  const pending = deferred(), f = fixture({ putFunctionalDefect: () => wrong ? Promise.resolve({ data: row({ id: 999, priority: 0 }) }) : pending.promise })
  try {
    await f.mount(); await f.quickUpdate(f.rows.value[0], 'priority', 0)
    assert.equal(f.rows.value[0].priority, 1); assert.equal(f.mutationError.value, '缺陷更新失败，请重试')
    wrong = false; const saving = f.quickUpdate(f.rows.value[0], 'priority', 0)
    f.hooks.stop.forEach(fn => fn()); pending.reject(Error('Late failure')); await saving
    assert.equal(f.mutationError.value, ''); assert.equal(f.rowBusy.size, 0)
  } finally { f.cleanup() }
})

test('delete completion from an old identity neither removes new rows nor triggers stale refresh', async () => {
  const pending = deferred(), f = fixture({ deleteFunctionalDefect: () => pending.promise })
  try {
    await f.mount(); f.removeRow(f.rows.value[0]); const dialog = f.confirmations[0], deleting = dialog.config.onBeforeOk()
    f.user.roleId = 2; await flush(); const before = f.reads.length
    assert.equal(dialog.closed, true); assert.equal(f.rowBusy.has(11), true)
    pending.resolve(); assert.equal(await deleting, false); await flush()
    assert.equal(f.rows.value[0].id, 11); assert.equal(f.reads.length, before); assert.equal(f.rowBusy.size, 0)
  } finally { f.cleanup() }
})

test('stale row events cannot open editing or transition windows in the current scope', async () => {
  const f = fixture(), opened = []
  try {
    await f.refreshAll(); const stale = f.rows.value[0]; await f.loadRows()
    f.editorDrawer.value = { isSaving: () => false, open: async () => opened.push('editor'), openById: async () => {}, openFromRoute: async () => {} }
    f.transitionDialog.value = { isSaving: () => false, open: () => opened.push('transition') }
    await f.openEditor(stale); await f.quickStatus(stale, 3); await f.quickUpdate(stale, 'priority', 0)
    assert.deepEqual(opened, []); assert.deepEqual(f.writes, [])
  } finally { f.cleanup() }
})
