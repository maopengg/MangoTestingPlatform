import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/run')
const row = (id = 1, patch = {}) => ({ id, name: `Run ${id}`, status: 'running', verdict: 'not_evaluated', engine: 'k6', peak_target_users: 0, actual_node_count: 0, requested_node_count: 1, create_time: '2026-11-08 10:00:00', project_product: { id: 1, name: 'Example product' }, module: { id: 2, name: 'Example module', full_path: 'Parent/Example module' }, ...patch })
const result = (rows = [row()], totalSize = rows.length) => ({ code: 200, data: rows, totalSize })
async function settle() { for (let i = 0; i < 50; i++) await Promise.resolve(); await vue.nextTick() }
function moduleAt(file, modules = {}) {
  const exports = {}, source = ts.transpileModule(readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, id => { if (!(id in modules)) { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error(`Unmocked ${id}`); } return modules[id] })
  return exports
}
function setup(options = {}) {
  let now = 0, seq = 0
  const timers = new Map(), hooks = { mounted: [], activated: [], deactivated: [], unmounted: [] }
  const saved = { document: globalThis.document, window: globalThis.window, setTimeout: globalThis.setTimeout, clearTimeout: globalThis.clearTimeout }
  const clock = { setTimeout(fn, delay) { const id = ++seq; timers.set(id, { fn, at: now + delay }); return id }, clearTimeout(id) { timers.delete(id) } }
  const doc = Object.assign(new EventTarget(), { visibilityState: options.hidden ? 'hidden' : 'visible' })
  Object.assign(globalThis, { document: doc, window: new EventTarget(), setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout })
  const route = vue.reactive({ path: '/perf/run/index', fullPath: '/perf/run/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-A', selected_environment: 0 })
  const calls = [], stopCalls = [], messages = [], navigation = []
  const vueHooks = { ...vue, ...Object.fromEntries(Object.entries({ onMounted: 'mounted', onActivated: 'activated', onDeactivated: 'deactivated', onBeforeUnmount: 'unmounted' }).map(([name, key]) => [name, fn => hooks[key].push(fn)])) }
  const pollingUtil = moduleAt(path.resolve('src/utils/page-polling.ts'))
  const polling = moduleAt(path.resolve('src/hooks/use-page-polling.ts'), { vue: vueHooks, 'vue-router': { useRoute: () => route }, '@/utils/page-polling': pollingUtil })
  const table = moduleAt(path.resolve('src/hooks/table.ts'), { vue: vueHooks })
  const h = harness('index', 'rows,filters,appliedFilters,pagination,loading,failed,stoppingIds,search,resetSearch,refresh:load,stop,open', { base, modules: {
    vue: vueHooks, 'vue-router': { useRoute: () => route, useRouter: () => ({ push: target => navigation.push(target) }) },
    '@/store/modules/user': { default: () => user }, '@/hooks/use-page-polling': polling, '@/hooks/table': table,
    '@arco-design/web-vue': { Message: { success: text => messages.push({ type: 'success', text }), error: text => messages.push({ type: 'error', text }) } },
    '@/api/perf': {
      getPerfRuns(query) { calls.push({ ...query }); return Promise.resolve().then(() => options.read ? options.read(query, calls.length) : result()) },
      stopPerfRun(id) { stopCalls.push(id); return Promise.resolve().then(() => options.stop ? options.stop(id) : { code: 200, data: {} }) },
    },
  } })
  hooks.mounted.forEach(fn => fn())
  return { ...h, route, user, calls, stopCalls, messages, navigation, timers, hooks,
    visibility(state) { doc.visibilityState = state; doc.dispatchEvent(new Event('visibilitychange')) },
    async advance(ms) {
      const end = now + ms
      for (let n = 0; n < 1000; n++) {
        const next = [...timers].filter(([, value]) => value.at <= end).sort((a, b) => a[1].at - b[1].at)[0]
        if (!next) { now = end; await settle(); return }
        timers.delete(next[0]); now = next[1].at; next[1].fn(); await settle()
      }
      throw Error('Unbounded timers')
    },
    async dispose() { hooks.unmounted.forEach(fn => fn()); h.close(); await settle(); Object.assign(globalThis, saved) },
  }
}

test('initial table loading resolves to finite detached rows and keeps real zero counts', async () => {
  const job = deferred(), fixture = result([row(1, { injected: true, module_full_path: 'ignored duplicate path' })]), h = setup({ read: () => job.promise })
  assert.equal(h.loading.value, true); assert.equal(h.rows.value.length, 0)
  job.resolve(fixture); await settle()
  assert.equal(h.loading.value, false); assert.equal(h.rows.value[0].peak_target_users, 0)
  assert.equal(h.rows.value[0].actual_node_count, 0); assert.equal('injected' in h.rows.value[0], false)
  assert.equal(h.rows.value[0].module_full_path, 'Parent/Example module')
  fixture.data[0].project_product.name = 'mutated'; assert.equal(h.rows.value[0].project_product.name, 'Example product')
  assert.deepEqual(h.calls[0], { page: 1, pageSize: 20 }); await h.dispose()
})
test('search snapshots name and multi-selects, resets page and submits only collection query keys', async () => {
  const h = setup(); await settle(); h.pagination.page = 4
  h.filters.name = 'Example'; h.filters.status.push('created', 'running'); h.filters.verdict.push('passed', 'invalid')
  await h.search()
  assert.equal(h.pagination.page, 1)
  assert.deepEqual(h.calls.at(-1), { name: 'Example', page: 1, pageSize: 20, status__in: 'created,running', verdict__in: 'passed,invalid' })
  h.filters.name = 'unsubmitted'; h.filters.status.push('completed'); await h.advance(5000)
  assert.equal(h.calls.at(-1).name, 'Example'); assert.equal(h.calls.at(-1).status__in, 'created,running')
  await h.resetSearch(); assert.deepEqual(h.filters.status, []); assert.deepEqual(h.filters.verdict, [])
  assert.deepEqual(h.calls.at(-1), { page: 1, pageSize: 20 }); await h.dispose()
})
test('pagination and page-size changes use the applied search, not unsubmitted edits', async () => {
  const h = setup({ read: () => result([row()], 200) }); await settle()
  h.filters.name = 'active'; await h.search(); h.filters.name = 'draft'
  h.pagination.page = 2; await h.pagination.onChange()
  assert.equal(h.calls.at(-1).page, 2); assert.equal(h.calls.at(-1).name, 'active')
  h.pagination.page = 1; h.pagination.pageSize = 50; await h.pagination.onChange()
  assert.equal(h.calls.at(-1).pageSize, 50); assert.equal('size' in h.calls.at(-1), false); await h.dispose()
})
test('same-query reads coalesce and a manual join upgrades silent loading until actual settlement', async () => {
  let next = null
  const h = setup({ read: () => next ? next.promise : result() }); await settle(); next = deferred()
  const a = h.refresh(true), b = h.refresh(), c = h.refresh(true)
  assert.equal(a, b); assert.equal(b, c); assert.equal(h.loading.value, true); await settle(); assert.equal(h.calls.length, 2)
  next.resolve(result()); await a; assert.equal(h.loading.value, false); await h.dispose()
})
test('repeated identical search submits share the pending request rather than restarting its context', async () => {
  let pending = null
  const h = setup({ read: () => pending ? pending.promise : result() }); await settle(); pending = deferred()
  h.filters.name = 'Example'; const a = h.search(), b = h.search(); await settle()
  assert.equal(a, b); assert.equal(h.calls.length, 2); pending.resolve(result()); await a
  assert.equal(h.loading.value, false); await h.dispose()
})
test('rapid search A-B-A rejects old data, errors and finally without closing new loading', async () => {
  const jobs = [deferred(), deferred(), deferred()]; let n = 0
  const h = setup({ read: () => jobs[n++].promise }); await settle()
  h.filters.name = 'B'; const b = h.search(); await settle(); h.filters.name = ''; const a = h.search(); await settle()
  jobs[0].resolve(result([row(1, { name: 'old A' })])); jobs[1].reject(Error('old B')); await settle()
  assert.equal(h.rows.value.length, 0); assert.equal(h.loading.value, true); assert.equal(h.failed.value, false)
  jobs[2].resolve(result([row(1, { name: 'new A' })])); await Promise.all([a, b]); assert.equal(h.rows.value[0].name, 'new A'); await h.dispose()
})
test('rapid page A-B-A rejects late page results even when returning to the same page number', async () => {
  const jobs = [deferred(), deferred(), deferred()]; let n = 0
  const h = setup({ read: () => jobs[n++].promise }); await settle()
  h.pagination.page = 2; const b = h.pagination.onChange(); await settle(); h.pagination.page = 1; const a = h.pagination.onChange(); await settle()
  jobs[0].resolve(result([row(10)], 60)); jobs[1].resolve(result([row(20)], 60)); await settle()
  assert.equal(h.rows.value.length, 0); assert.equal(h.loading.value, true)
  jobs[2].resolve(result([row(30)], 60)); await Promise.all([a, b]); assert.equal(h.rows.value[0].id, 30); await h.dispose()
})
test('business and malformed failures preserve the previous table and permit retry', async () => {
  let fixture = result()
  const h = setup({ read: () => fixture }); await settle(); const previous = h.rows.value
  for (const bad of [{ code: 403, data: [] }, { code: 200, data: {}, totalSize: 0 }, result([row(1, { actual_node_count: false })]), result([row()], -1)]) {
    fixture = bad; assert.equal(await h.refresh(), false); assert.equal(h.rows.value, previous)
    assert.equal(h.failed.value, true); assert.equal(h.loading.value, false)
  }
  fixture = result([]); assert.equal(await h.refresh(), true); assert.equal(h.failed.value, false)
  assert.equal(h.pagination.pageCount, 0); await h.dispose()
})
test('successful empty responses without a total are empty lists, while malformed nonempty responses still fail', async () => {
  let fixture = { code: 200, data: [] }
  const h = setup({ read: () => fixture }); await settle()
  assert.equal(h.failed.value,false);assert.deepEqual(h.rows.value,[])
  assert.equal(h.pagination.pageCount,0)
  assert.deepEqual(h.messages,[])
  fixture = { code: 200, data: [row()] }
  assert.equal(await h.refresh(),false)
  assert.equal(h.messages.at(-1).type,'error')
  const count=h.messages.length
  assert.equal(await h.refresh(true),false)
  assert.equal(h.messages.length,count)
  fixture={code:200,data:[],totalSize:-1}
  assert.equal(await h.refresh(),false)
  await h.dispose()
})
test('an out-of-range page corrects itself before publishing results and keeps page size', async () => {
  const h = setup({ read: query => query.page > 2 ? result([], 21) : result([row(query.page)], 21) }); await settle()
  h.pagination.page = 5; await h.pagination.onChange()
  assert.equal(h.pagination.page, 2); assert.equal(h.rows.value[0].id, 2)
  assert.deepEqual(h.calls.slice(-2).map(q => q.page), [5, 2]); assert.equal(h.calls.at(-1).pageSize, 20); await h.dispose()
})
for (const field of ['userId', 'roleId', 'token', 'selected_environment']) test(`${field} A-B-A clears row and pagination state synchronously and rejects late responses`, async () => {
  const jobs = [deferred(), deferred(), deferred()]; let n = 0
  const h = setup({ read: () => jobs[n++].promise }); await settle()
  const saved = h.user[field]; h.user[field] = field === 'token' ? 'fixture-B' : 2; await settle(); h.user[field] = saved; await settle()
  assert.equal(n, 3); assert.equal(h.pagination.pageCount, 0)
  jobs[0].resolve(result([row(10)])); jobs[1].reject(Error('obsolete')); await settle()
  assert.equal(h.rows.value.length, 0); assert.equal(h.loading.value, true); assert.equal(h.failed.value, false)
  jobs[2].resolve(result([row(30)])); await settle(); assert.equal(h.rows.value[0].id, 30); await h.dispose()
})
test('real public polling retries initial failure every five seconds and keeps created/running rows silent', async () => {
  let fail = true, status = 'created'
  const h = setup({ read: () => { if (fail) throw Error('offline'); return result([row(1, { status })]) } }); await settle()
  assert.equal(h.failed.value, true); assert.equal(h.loading.value, false)
  await h.advance(5000); assert.equal(h.calls.length, 2); assert.equal(h.loading.value, false)
  fail = false; await h.advance(5000); assert.equal(h.rows.value[0].status, 'created'); assert.equal(h.failed.value, false)
  status = 'running'; await h.advance(5000); assert.equal(h.rows.value[0].status, 'running')
  status = 'completed'; await h.advance(5000); const count = h.calls.length
  await h.advance(20000); assert.equal(h.calls.length, count); await h.dispose()
})
test('visibility and KeepAlive pause polling, preserve snapshots and recover without loading flashes', async () => {
  const h = setup(); await settle(); const previous = h.rows.value
  h.visibility('hidden'); await h.advance(30000); assert.equal(h.calls.length, 1); assert.equal(h.rows.value, previous)
  h.visibility('visible'); assert.equal(h.loading.value, false); await settle(); assert.equal(h.calls.length, 2)
  h.hooks.deactivated.forEach(fn => fn()); await h.advance(30000); assert.equal(h.calls.length, 2)
  h.hooks.activated.forEach(fn => fn()); await settle(); assert.equal(h.calls.length, 3); assert.equal(h.loading.value, false); await h.dispose()
})
test('a hidden initial or replaced identity waits for visibility, then shows initial loading', async () => {
  const h = setup({ hidden: true }); await settle(); assert.equal(h.calls.length, 0)
  h.user.roleId = 2; await settle(); assert.equal(h.calls.length, 0)
  h.visibility('visible'); assert.equal(h.loading.value, true); await settle(); assert.equal(h.calls.length, 1); await h.dispose()
})
test('stale polling context cannot close a newer manual request loading', async () => {
  const request = deferred(), h = setup({ read: () => request.promise }); await settle()
  assert.equal(await h.refresh(true, { isCurrent: () => false }), false); assert.equal(h.loading.value, true)
  request.resolve(result()); await settle(); assert.equal(h.loading.value, false); await h.dispose()
})
test('route departure and unmount prevent late publication, polling, and navigation of stale rows', async () => {
  const pending = deferred(), h = setup({ read: () => pending.promise }); await settle()
  h.route.path = '/perf/capacity/index'; pending.resolve(result()); await settle()
  assert.equal(h.rows.value.length, 0); await h.advance(10000); assert.equal(h.calls.length, 1)
  h.open(row()); assert.equal(h.navigation.length, 0); await h.dispose(); assert.equal(h.timers.size, 0)
})
test('a late request after actual unmount cannot restore rows, totals or errors', async () => {
  const pending = deferred(), h = setup({ read: () => pending.promise }); await settle(); await h.dispose()
  pending.resolve(result([row(99)], 100)); await settle()
  assert.equal(h.rows.value.length, 0); assert.equal(h.pagination.pageCount, 0)
  assert.equal(h.failed.value, false); assert.equal(h.loading.value, false); assert.equal(h.timers.size, 0)
})
test('KeepAlive reactivation rejects an old pending response while loading the fresh snapshot', async () => {
  const first = deferred(), second = deferred(); let attempts = 0
  const h = setup({ read: () => ++attempts === 1 ? first.promise : second.promise }); await settle()
  h.hooks.deactivated.forEach(fn => fn()); h.hooks.activated.forEach(fn => fn()); await settle()
  first.reject(Error('old activation')); await settle()
  assert.equal(h.failed.value, false); assert.equal(h.rows.value.length, 0)
  second.resolve(result([row(2)])); await settle(); assert.equal(h.rows.value[0].id, 2); await h.dispose()
})
test('stop locks are per run, survive identity changes and ignore old completion without clearing another lock', async () => {
  const a = deferred(), b = deferred(), h = setup({ read: () => result([row(1), row(2)]), stop: id => id === 1 ? a.promise : b.promise }); await settle()
  const one = h.stop(h.rows.value[0]), repeated = h.stop(h.rows.value[0]), two = h.stop(h.rows.value[1]); await settle()
  assert.deepEqual(h.stopCalls, [1, 2]); h.user.roleId = 2; await settle(); await h.stop(h.rows.value[0]); assert.equal(h.stopCalls.length, 2)
  a.resolve({ code: 200 }); await Promise.all([one, repeated]); assert.equal(h.stoppingIds.has(1), false); assert.equal(h.stoppingIds.has(2), true)
  b.resolve({ code: 200 }); await two; assert.equal(h.stoppingIds.size, 0); assert.equal(h.messages.length, 0); await h.dispose()
})
test('stop failure permits retry and successful stop is not undone by a failed list refresh', async () => {
  let failStop = true, failRead = false
  const h = setup({ read: () => { if (failRead) throw Error('offline'); return result() }, stop: () => failStop ? { code: 400 } : { code: 200 } }); await settle()
  await h.stop(h.rows.value[0]); assert.equal(h.stoppingIds.size, 0); assert.equal(h.messages.at(-1).type, 'error')
  failStop = false; failRead = true; await h.stop(h.rows.value[0])
  assert.equal(h.messages.at(-1).type, 'success'); assert.equal(h.failed.value, true); assert.equal(h.stoppingIds.size, 0); await h.dispose()
})
test('a stop finishing after a filter switch neither refreshes nor reports success in the new query', async () => {
  const pending = deferred(), h = setup({ stop: () => pending.promise }); await settle()
  const operation = h.stop(h.rows.value[0]); h.filters.name = 'other'; await h.search()
  const reads = h.calls.length; pending.resolve({ code: 200 }); await operation
  assert.equal(h.calls.length, reads); assert.equal(h.messages.length, 0); assert.equal(h.stoppingIds.size, 0); await h.dispose()
})
test('details navigation preserves the route and only accepts a current visible row', async () => {
  const h = setup(); await settle(); h.open(h.rows.value[0])
  assert.deepEqual(h.navigation[0], { path: '/perf/run/details', query: { id: 1 } })
  h.open(row(99)); assert.equal(h.navigation.length, 1); await h.dispose()
})
test('returning from details keeps the list page, while an identity switch resets to the first page', async () => {
  const h = setup({ read: query => result([row(query.page)], 60) }); await settle()
  h.pagination.page = 2; await h.pagination.onChange()
  h.route.path = '/perf/run/details'; await settle(); h.route.path = '/perf/run/index'; await settle()
  assert.equal(h.pagination.page, 2); assert.equal(h.calls.at(-1).page, 2)
  h.user.roleId = 2; await settle(); assert.equal(h.pagination.page, 1); assert.equal(h.calls.at(-1).page, 1); await h.dispose()
})
test('actual page SFC compiles after typed state and lifecycle integration', () => {
  const filename = path.join(base, 'index.vue'), { descriptor } = parse(readFileSync(filename, 'utf8'))
  const script = compileScript(descriptor, { id: 'run61' })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: 'run61', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
})
