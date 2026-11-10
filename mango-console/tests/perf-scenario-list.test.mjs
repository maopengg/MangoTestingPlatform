import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/scenario')
const row = (patch = {}) => ({
  id: 1, name: 'Example', load_type: 'concurrency', target_users: 10, target_rate: null, rate_time_unit: null,
  duration_seconds: 60, step_count: 0, default_executor_count: 1, status: 1, update_time: '2026-11-08 10:00:00',
  project_product: { id: 10, name: 'Example product' }, module: { id: 20, name: 'Module', full_path: 'Group / Module' },
  module_full_path: 'Group / Module', ignored: 'extra', ...patch,
})
const response = (rows = [row()], total = rows.length) => ({ code: 200, data: rows, totalSize: total })
function paginationModule() {
  const exports = {}
  const source = ts.transpileModule(readFileSync('src/hooks/table.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, id => { if (id === 'vue') return vue; { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw new Error('Unmocked pagination module ' + id) } })
  return exports
}
function setup(api = {}) {
  const route = vue.reactive({ path: '/perf/scenario/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const requests = [], updates = [], deletes = [], messages = [], confirmations = [], navigations = []
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }
  const previousDoc = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const listeners = new Set(), add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (event, fn) => { listeners.add(fn); add(event, fn) }
  doc.removeEventListener = (event, fn) => { listeners.delete(fn); remove(event, fn) }
  globalThis.document = doc
  const h = harness('index', 'rows,loading,failed,filters,appliedFilters,pagination,resetKey,query,refresh:load,search,onNavigation,resetSearch,toggleStatus,remove,changingIds,deletingIds,goDetail,execute', {
    base, modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      'vue-router': { useRoute: () => route, useRouter: () => ({ push: value => navigations.push(value) }) },
      '@/store/modules/user': { default: () => user }, '@/hooks/table': paginationModule(),
      '@arco-design/web-vue': { Message: { success: text => messages.push(['success', text]), error: text => messages.push(['error', text]) },
        Modal: { confirm: options => { const modal = { options, closed: false, close() { modal.closed = true } }; confirmations.push(modal); return modal } } },
      '@/api/perf': {
        getPerfScenarios: async query => { requests.push(query); return api.read ? api.read(query) : response() },
        updatePerfScenario: async payload => { updates.push(payload); return api.update ? api.update(payload) : { code: 200, data: payload } },
        deletePerfScenario: async id => { deletes.push(id); return api.delete ? api.delete(id) : { code: 200 } },
      },
    },
  })
  return { ...h, route, user, doc, life, listeners, requests, updates, deletes, messages, confirmations, navigations,
    boundary: h.load('list.ts'), mount: () => life.mount.forEach(fn => fn()),
    hide: () => { doc.visibilityState = 'hidden'; doc.dispatchEvent(new Event('visibilitychange')) },
    show: () => { doc.visibilityState = 'visible'; doc.dispatchEvent(new Event('visibilitychange')) },
    pause: () => life.deactivate.forEach(fn => fn()), resume: () => life.activate.forEach(fn => fn()),
    close: () => { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = previousDoc },
  }
}

test('finite row mapping preserves zero and Decimal rates, detaches nested values and rejects bad totals or records', () => {
  const h = setup(), source = row({ target_rate: '10.2500' })
  const result = h.boundary.readScenarioRows(response([source]))
  assert.equal(result.rows[0].step_count, 0)
  assert.equal(result.rows[0].target_rate, 10.25)
  assert.equal('ignored' in result.rows[0], false)
  source.project_product.name = 'Changed'
  assert.equal(result.rows[0].project_product.name, 'Example product')
  for (const fixture of [response([row({ status: false })]), response([row({ target_rate: '' })]), response([row({ module: false })]), response([], false), response([], -1), response([row(), row()]), { code: 400, data: [] }, { code: 200, data: null, totalSize: 0 }])
    assert.throws(() => h.boundary.readScenarioRows(fixture))
  assert.deepEqual(h.boundary.readScenarioRows(response([], 0)), { rows: [], total: 0 })
  h.close()
})

test('search snapshots are detached; pagination uses applied filters until search is explicitly applied', async () => {
  const h = setup({ read: async () => response([row()], 100) })
  h.filters.name = 'Applied'; h.filters.load_type = ['arrival_rate', 'iteration_rate']
  await h.search()
  h.filters.name = 'Unsaved'; h.filters.load_type.push('concurrency')
  h.pagination.page = 2
  await h.pagination.onChange()
  assert.deepEqual(h.requests.at(-1), { page: 2, pageSize: 20, name: 'Applied', load_type__in: 'arrival_rate,iteration_rate' })
  await h.search()
  assert.equal(h.requests.at(-1).page, 1)
  assert.equal(h.requests.at(-1).name, 'Unsaved')
  h.close()
})

test('navigation converts IDs and reset clears navigation, multi-select, page and prior search parameters', async () => {
  const h = setup()
  h.filters.name = 'Example'; h.filters.load_type = ['arrival_rate']
  await h.onNavigation({ projectProduct: ['1', '10'], module: '20' })
  assert.equal(h.requests.at(-1).project_product, 10)
  assert.equal(h.requests.at(-1).module, 20)
  h.pagination.page = 4
  const reset = h.resetKey.value
  await h.resetSearch()
  assert.deepEqual(h.filters.load_type, [])
  assert.equal(h.filters.project_product, null)
  assert.equal(h.filters.module, null)
  assert.equal(h.resetKey.value, reset + 1)
  assert.deepEqual(h.requests.at(-1), { page: 1, pageSize: 20 })
  h.close()
})

test('duplicate reads coalesce and older A-B-A response/error/finalizer cannot replace the latest search', async () => {
  const reads = [deferred(), deferred(), deferred()]
  let index = 0
  const h = setup({ read: () => reads[index++].promise })
  const a = h.refresh(), duplicate = h.refresh()
  assert.equal(a, duplicate)
  await flush()
  h.filters.name = 'B'; const b = h.search(); await flush()
  h.filters.name = ''; const last = h.search(); await flush()
  reads[0].resolve(response([row({ name: 'Old A' })])); reads[1].reject(new Error('Old B'))
  assert.equal(await a, false); assert.equal(await b, false)
  assert.equal(h.loading.value, true)
  assert.equal(h.failed.value, false)
  reads[2].resolve(response([row({ name: 'New A' })]))
  assert.equal(await last, true)
  assert.equal(h.rows.value[0].name, 'New A')
  assert.equal(h.loading.value, false)
  h.close()
})

test('failed or malformed reads retain current rows and total and allow retry', async () => {
  let fixture = response()
  const h = setup({ read: async () => fixture })
  await h.refresh()
  const rows = h.rows.value
  fixture = response([row({ name: 'Bad', status: null })])
  assert.equal(await h.refresh(), false)
  assert.equal(h.failed.value, true)
  assert.equal(h.loading.value, false)
  assert.equal(h.rows.value, rows)
  assert.equal(h.pagination.pageCount, 1)
  fixture = response([row({ name: 'Recovered' })])
  assert.equal(await h.refresh(), true)
  assert.equal(h.failed.value, false)
  assert.equal(h.rows.value[0].name, 'Recovered')
  h.close()
})

test('out-of-range pages recover with the same applied filters and an actual second read', async () => {
  const h = setup({ read: async query => query.page > 2 ? response([], 21) : response([row()], 21) })
  h.filters.name = 'Applied'; await h.search()
  h.pagination.page = 3
  await h.pagination.onChange()
  assert.equal(h.pagination.page, 2)
  assert.deepEqual(h.requests.slice(-2).map(query => [query.page, query.name]), [[3, 'Applied'], [2, 'Applied']])
  assert.equal(h.pagination.pageCount, 21)
  assert.equal(h.loading.value, false)
  h.close()
})

test('status changes await business success, prevent overlapping delete and retain physical lock after identity change', async () => {
  const pending = deferred(), h = setup({ update: () => pending.promise })
  await h.refresh()
  const record = h.rows.value[0], first = h.toggleStatus(record, 0)
  assert.equal(record.status, 1)
  assert.equal(h.changingIds.has(1), true)
  assert.equal(await h.toggleStatus(record, 0), false)
  h.remove(record)
  assert.deepEqual(h.confirmations, [])
  h.user.roleId = 2
  assert.equal(h.changingIds.has(1), true)
  pending.resolve({ code: 200, data: { id: 1, status: 0 } })
  assert.equal(await first, false)
  assert.equal(record.status, 1)
  assert.equal(h.changingIds.has(1), false)
  assert.deepEqual(h.rows.value, [])
  assert.deepEqual(h.messages, [])
  h.close()
})

test('status failure or mismatched update leaves old status; valid update reloads authoritative data', async () => {
  let result = { code: 400 }, status = 1
  const h = setup({ read: async () => response([row({ status })]), update: async () => result })
  await h.refresh()
  assert.equal(await h.toggleStatus(h.rows.value[0], 0), false)
  assert.equal(h.rows.value[0].status, 1)
  result = { code: 200, data: { id: 2, status: 0 } }
  assert.equal(await h.toggleStatus(h.rows.value[0], 0), false)
  status = 0; result = { code: 200, data: { id: 1, status: 0 } }
  assert.equal(await h.toggleStatus(h.rows.value[0], 0), true)
  assert.equal(h.rows.value[0].status, 0)
  assert.equal(h.requests.length, 2)
  h.close()
})

test('delete confirmation returns its promise, retries failures and prevents concurrent status/delete requests', async () => {
  let result = { code: 400 }, deleted = false
  const h = setup({ read: async () => response(deleted ? [] : [row()]), delete: async () => { if (result.code === 200) deleted = true; return result } })
  await h.refresh()
  h.remove(h.rows.value[0])
  const modal = h.confirmations[0]
  assert.equal(typeof modal.options.onBeforeOk, 'function')
  assert.equal('onOk' in modal.options, false)
  assert.equal(await modal.options.onBeforeOk(), false)
  assert.equal(h.deletingIds.has(1), false)
  result = { code: 200 }
  const request = modal.options.onBeforeOk()
  assert.equal(h.deletingIds.has(1), true)
  assert.equal(await modal.options.onBeforeOk(), false)
  assert.equal(await h.toggleStatus(h.rows.value[0], 0), false)
  assert.equal(await request, true)
  assert.deepEqual(h.rows.value, [])
  assert.equal(h.pagination.pageCount, 0)
  assert.equal(h.deletingIds.has(1), false)
  h.close()
})

test('search changes close old confirmation and reject its callback before any delete HTTP', async () => {
  const h = setup()
  await h.refresh(); h.remove(h.rows.value[0])
  const old = h.confirmations[0]
  h.filters.name = 'Changed'; await h.search()
  assert.equal(old.closed, true)
  assert.equal(await old.options.onBeforeOk(), false)
  assert.deepEqual(h.deletes, [])
  h.close()
})

test('identity A-B-A clears rows and filters, discards old read, and reloads under the new scope', async () => {
  const pending = deferred()
  let first = true
  const h = setup({ read: async () => { if (first) { first = false; return pending.promise } return response([row({ name: 'New scope' })]) } })
  h.filters.name = 'Old scope'; const read = h.search(); await flush()
  h.user.token = 'fixture-b'; h.user.token = 'fixture-a'
  assert.equal(h.filters.name, '')
  assert.deepEqual(h.rows.value, [])
  pending.resolve(response([row({ name: 'Old scope' })]))
  assert.equal(await read, false)
  await h.refresh()
  assert.equal(h.rows.value[0].name, 'New scope')
  assert.equal('name' in h.requests.at(-1), false)
  h.close()
})

test('KeepAlive and background suspend reads; return preserves draft filters and reloads the applied query', async () => {
  const pending = deferred()
  let index = 0
  const h = setup({ read: async () => ++index === 1 ? pending.promise : response() })
  h.mount(); await flush()
  h.pause()
  pending.reject(new Error('stale failure'))
  await flush()
  assert.equal(h.failed.value, false)
  h.resume(); await flush()
  assert.equal(h.rows.value.length, 1)
  h.filters.name = 'Unsaved'
  h.hide()
  assert.equal(await h.refresh(), false)
  h.show(); await flush()
  assert.equal(h.filters.name, 'Unsaved')
  assert.equal('name' in h.requests.at(-1), false)
  h.close()
  assert.equal(h.listeners.size, 0)
  assert.equal(await h.refresh(), false)
})

test('late delete response cannot clear a new identity list or emit success; physical lock survives until settled', async () => {
  const pending = deferred(), h = setup({ delete: () => pending.promise })
  await h.refresh(); h.remove(h.rows.value[0])
  const first = h.confirmations[0].options.onBeforeOk()
  h.user.selected_environment = 1
  await h.refresh()
  assert.equal(h.deletingIds.has(1), true)
  pending.resolve({ code: 200 })
  assert.equal(await first, false)
  assert.equal(h.rows.value.length, 1)
  assert.equal(h.deletingIds.has(1), false)
  assert.deepEqual(h.messages, [])
  h.close()
})

test('detail and execute navigation accept only currently visible rows and preserve route protocols', async () => {
  const h = setup()
  await h.refresh()
  h.goDetail(h.rows.value[0]); h.execute(h.rows.value[0]); h.execute(row({ id: 99 }))
  assert.deepEqual(h.navigations, [
    { path: '/perf/scenario/details', query: { id: 1 } },
    { path: '/perf/scenario/details', query: { id: 1, execute: '1' } },
  ])
  h.route.path = '/perf/run/index'
  h.goDetail(row())
  assert.equal(h.navigations.length, 2)
  h.close()
})
