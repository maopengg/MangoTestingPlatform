import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/monitoring/report')
const table = {}
new Function('exports', 'require', ts.transpileModule(readFileSync('src/hooks/table.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText)(table, name => { assert.equal(name, 'vue'); return vue })
const report = (id = 1) => ({ id, task: null, task_name: '', task_notice_group: null, status: 0, status_display: '信息', msg: null, send_text: null, is_notice: 0, create_time: '2026-11-07 10:00:00', update_time: '2026-11-07 10:00:00' })
const page = (id = 1, total = 1) => ({ code: 200, data: [report(id)], totalSize: total })
function setup(read) {
  const hooks = { mounted: [], activated: [], deactivated: [], unmounted: [] }, calls = []
  const route = vue.reactive({ path: '/monitoring/report/index', fullPath: '/monitoring/report/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 })
  const h = harness('index', 'conditionItems,rows,listLoading,loadFailed,selectedReport,detailVisible,pagination,doRefresh,onSearchRefresh,onResetSearch,onViewDetail,closeDetail,statusTitle', {
    base,
    modules: {
      vue: { ...vue, onMounted: fn => hooks.mounted.push(fn), onActivated: fn => hooks.activated.push(fn), onDeactivated: fn => hooks.deactivated.push(fn), onBeforeUnmount: fn => hooks.unmounted.push(fn) },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ monitoring_log_status: [{ key: 2, title: '警告' }, { key: 0, title: '信息' }] }) },
      '@/hooks/table': table,
      '@/api/monitoring/report': { getMonitoringReportList: query => { calls.push(query); return read ? read(query, calls.length) : Promise.resolve(page()) } },
    },
  })
  hooks.mounted.forEach(fn => fn())
  return { ...h, calls, route, user, hooks }
}
function dispose(h) { h.hooks.unmounted.forEach(fn => fn()); h.close() }

test('initial local loading receives typed nullable reports and total zero is not replaced', async () => {
  const pending = deferred(), h = setup(() => pending.promise)
  assert.equal(h.listLoading.value, true); assert.deepEqual(h.calls[0], { page: 1, pageSize: 20 })
  pending.resolve({ code: 200, data: [], totalSize: 0 }); await flush()
  assert.equal(h.listLoading.value, false); assert.equal(h.pagination.pageCount, 0); assert.deepEqual(h.rows.value, []); dispose(h)
})
test('search fields belong to each instance and status uses multi-select collection query including zero', async () => {
  const a = setup(), b = setup(); await flush()
  a.conditionItems[0].value = ' Example '; a.conditionItems[1].value = [0, 2, 0, '']; a.pagination.page = 4
  await a.onSearchRefresh()
  assert.deepEqual(a.calls.at(-1), { page: 1, pageSize: 20, task__name__contains: 'Example', status__in: '0,2' })
  assert.equal(b.conditionItems[0].value, ''); assert.deepEqual(b.conditionItems[1].value, [])
  assert.equal(a.conditionItems[1].multiple, true); await a.onResetSearch()
  assert.deepEqual(a.calls.at(-1), { page: 1, pageSize: 20 }); assert.deepEqual(a.conditionItems[1].value, []); dispose(a); dispose(b)
})
test('empty inputs are omitted, unrelated fields cannot leak to query, status coercion rejects empty and invalid values', () => {
  const h = setup(), { createReportQuery } = h.load('records.ts')
  const items = [{ key: 'task_name', value: ' ' }, { key: 'status', value: ['', ' ', null, false, 'bad', '0', 2] }, { key: 'token', value: 'must-not-copy' }]
  assert.deepEqual(createReportQuery(items, 3, 50), { page: 3, pageSize: 50, status__in: '0,2' }); dispose(h)
})
test('pagination retains page and size while search and reset return to first page', async () => {
  const h = setup(); await flush(); h.pagination.page = 3; h.pagination.pageSize = 50
  await h.pagination.onChange(); assert.deepEqual(h.calls.at(-1), { page: 3, pageSize: 50 })
  await h.onSearchRefresh(); assert.equal(h.calls.at(-1).page, 1); dispose(h)
})
test('same-query concurrent refresh is coalesced without dropping local loading', async () => {
  const pending = deferred(), h = setup(() => pending.promise)
  const a = h.doRefresh(), b = h.doRefresh(); assert.equal(a, b); assert.equal(h.calls.length, 1)
  pending.resolve(page()); await a; assert.equal(h.listLoading.value, false); dispose(h)
})
test('newest search wins and late previous finally cannot remove newer loading', async () => {
  const jobs = [deferred(), deferred()], h = setup((_q, n) => jobs[n - 1].promise)
  h.conditionItems[0].value = 'new'; const next = h.onSearchRefresh()
  jobs[0].resolve(page(1)); await flush(); assert.equal(h.listLoading.value, true); assert.deepEqual(h.rows.value, [])
  jobs[1].resolve(page(2, 5)); await next; assert.equal(h.rows.value[0].id, 2); assert.equal(h.pagination.pageCount, 5); dispose(h)
})
test('older success cannot replace newer successful query', async () => {
  const jobs = [deferred(), deferred()], h = setup((_q, n) => jobs[n - 1].promise)
  h.conditionItems[0].value = 'new'; const next = h.onSearchRefresh(); jobs[1].resolve(page(2)); await next
  jobs[0].resolve(page(1)); await flush(); assert.equal(h.rows.value[0].id, 2); dispose(h)
})
test('failed and malformed pages keep prior snapshot, stop loading and allow retry', async () => {
  for (const broken of [new Error('offline'), { code: 300, data: [], totalSize: 0 }, { code: 200, data: {}, totalSize: 1 }, { code: 200, data: [{}], totalSize: 1 }]) {
    let fail = false; const h = setup(async () => { if (!fail) return page(); if (broken instanceof Error) throw broken; return broken }); await flush()
    fail = true; await h.doRefresh(); assert.equal(h.rows.value[0].id, 1); assert.equal(h.pagination.pageCount, 1)
    assert.equal(h.loadFailed.value, true); assert.equal(h.listLoading.value, false)
    fail = false; await h.doRefresh(); assert.equal(h.loadFailed.value, false); dispose(h)
  }
})
test('drawer owns a detached snapshot and close/reopen does not reuse old selection', async () => {
  const h = setup(); await flush(); const original = { ...report(8), task_notice_group: { id: 4, name: 'Example group' } }
  h.onViewDetail(original); original.task_notice_group.name = 'changed'
  assert.equal(h.selectedReport.value.task_notice_group.name, 'Example group'); assert.equal(h.detailVisible.value, true)
  h.detailVisible.value = false; assert.equal(h.selectedReport.value, null)
  h.onViewDetail(report(9)); assert.equal(h.selectedReport.value.id, 9); await h.onSearchRefresh()
  assert.equal(h.detailVisible.value, false); assert.equal(h.selectedReport.value, null); dispose(h)
})
test('status display uses enum key instead of array position with server fallback for unknown values', async () => {
  const h = setup(); await flush(); assert.equal(h.statusTitle(report()), '信息')
  assert.equal(h.statusTitle({ ...report(), status: 99, status_display: '未知状态' }), '未知状态'); dispose(h)
})
test('identity, environment and route A-B-A invalidate old reads synchronously', async () => {
  for (const change of [h => { h.user.token = 'other'; h.user.token = 'fixture' }, h => { h.user.selected_environment = 2; h.user.selected_environment = 0 }, h => { h.route.fullPath = '/away'; h.route.fullPath = '/monitoring/report/index' }]) {
    const pending = deferred(), h = setup((_q, n) => n === 1 ? pending.promise : Promise.resolve(page(9)))
    h.onViewDetail(report()); change(h); await flush(); pending.resolve(page(1)); await flush()
    assert.equal(h.rows.value[0].id, 9); assert.equal(h.detailVisible.value, false); dispose(h)
  }
})
test('KeepAlive suspends and ignores old reads, resumes once, unmounted responses stay ignored', async () => {
  const pending = deferred(), h = setup((_q, n) => n === 1 ? pending.promise : Promise.resolve(page(2)))
  h.hooks.activated.forEach(fn => fn()); assert.equal(h.calls.length, 1)
  h.hooks.deactivated.forEach(fn => fn()); await h.doRefresh(); assert.equal(h.calls.length, 1)
  h.hooks.activated.forEach(fn => fn()); await flush(); pending.resolve(page(1)); await flush()
  assert.equal(h.calls.length, 2); assert.equal(h.rows.value[0].id, 2)
  h.hooks.unmounted.forEach(fn => fn()); assert.deepEqual(h.rows.value, []); await h.doRefresh(); assert.equal(h.calls.length, 2); h.close()
})
test('pending response after unmount cannot repopulate rows or leave an error/loading state', async () => {
  for (const reject of [false, true]) {
    const pending = deferred(), h = setup(() => pending.promise)
    h.hooks.unmounted.forEach(fn => fn())
    if (reject) pending.reject(new Error('offline')); else pending.resolve(page())
    await flush(); assert.deepEqual(h.rows.value, []); assert.equal(h.pagination.pageCount, 0)
    assert.equal(h.loadFailed.value, false); assert.equal(h.listLoading.value, false); h.close()
  }
})
test('route departure suppresses reads and clears open report until returning', async () => {
  const h = setup(); await flush(); h.onViewDetail(report())
  h.route.path = '/elsewhere'; h.route.fullPath = '/elsewhere'; await h.doRefresh()
  assert.equal(h.calls.length, 1); assert.equal(h.detailVisible.value, false); assert.deepEqual(h.rows.value, [])
  h.route.path = '/monitoring/report/index'; h.route.fullPath = '/monitoring/report/index'; await flush()
  assert.equal(h.calls.length, 2); dispose(h)
})
test('report API retains list/detail/create endpoints and typed nullable detail lookup', async () => {
  const exports = {}, calls = []
  const response = page()
  const request = async options => { calls.push({ url: options.url, data: options.data() }); return response }
  new Function('exports', 'require', ts.transpileModule(readFileSync('src/api/monitoring/report.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText)(exports, () => ({ get: request, post: request }))
  await exports.getMonitoringReportList({ page: 2, pageSize: 20, status__in: '0,1' })
  assert.deepEqual(calls.at(-1), { url: 'monitoring/report', data: { page: 2, pageSize: 20, status__in: '0,1' } })
  assert.equal((await exports.getMonitoringReportDetail(1)).data.id, 1)
  assert.equal((await exports.getMonitoringReportDetail(99)).data, null)
  await exports.createMonitoringReport({ task_id: 1, status: 0, msg: 'Example' })
  assert.deepEqual(calls.at(-1), { url: 'monitoring/report/create', data: { task_id: 1, status: 0, msg: 'Example' } })
})
test('snapshot mapping preserves nulls/zero and whitelists nested data', () => {
  const h = setup(), { readMonitoringReport } = h.load('records.ts')
  const row = readMonitoringReport({ ...report(), hidden: 'must-not-copy', task_notice_group: { id: 0, name: 'Example', credentials: 'must-not-copy' } })
  assert.equal(row.task, null); assert.equal(row.status, 0); assert.equal(row.is_notice, 0); assert.equal(row.msg, null)
  assert.equal('hidden' in row, false); assert.deepEqual(row.task_notice_group, { id: 0, name: 'Example' }); dispose(h)
})
test('page script/template compile with snapshot drawer and finite configuration', () => {
  const filename = path.join(base, 'index.vue'), source = readFileSync(filename, 'utf8'), { descriptor } = parse(source, { filename })
  const script = compileScript(descriptor, { id: 'monitoring55' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'monitoring55', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})
