import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/capacity')
const row = (name = 'Example executor') => ({
  fingerprint: 'user:1', executor_name: name, online: true, engine: 'k6', engine_version: null,
  safe_vus: 100, safe_rps: 20, reserved_vus: 30, reserved_rps: 4, available_vus: 40, available_rps: 10,
})
const response = (name) => ({ code: 200, data: {
  summary: { executor_count: 1, online_count: 1, available_vus: 40, available_rps: 10 },
  defaults: { safe_vus: 100, safe_rps: 20, safety_factor: 0.7 }, rows: [row(name)],
} })
function setup(read = () => response()) {
  const hooks = { mounted: [], activated: [], deactivated: [], unmounted: [] }, calls = []
  const route = vue.reactive({ path: '/perf/capacity/index', fullPath: '/perf/capacity/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 })
  const h = harness('index', 'overview,summary,defaults,rows,loading,failed,safetyFactorPercent,refresh:load', {
    base, modules: {
      vue: { ...vue, ...Object.fromEntries(Object.entries({ onMounted: 'mounted', onActivated: 'activated', onDeactivated: 'deactivated', onBeforeUnmount: 'unmounted' }).map(([key, value]) => [key, fn => hooks[value].push(fn)])) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user },
      '@/api/perf/capacity': { getPerfCapacityOverview: () => { calls.push(calls.length + 1); return read(calls.length) } },
    },
  })
  hooks.mounted.forEach(fn => fn())
  return { ...h, hooks, route, user, calls, dispose() { hooks.unmounted.forEach(fn => fn()); h.close() } }
}

test('initial loading does not fabricate capacity and successful response supplies detached finite values', async () => {
  const job = deferred(), fixture = response(), h = setup(() => job.promise)
  assert.equal(h.loading.value, true); assert.equal(h.overview.value, null); assert.equal(h.safetyFactorPercent.value, '—')
  job.resolve(fixture); await flush()
  assert.equal(h.loading.value, false); assert.equal(h.failed.value, false)
  assert.equal(h.rows.value[0].available_vus, 40); assert.equal(h.safetyFactorPercent.value, 70)
  fixture.data.rows[0].executor_name = 'mutated'; assert.equal(h.rows.value[0].executor_name, 'Example executor')
  h.dispose()
})
test('zero defaults, counts and fractional capacities survive decoding and formatting', async () => {
  const fixture = response(); fixture.data.defaults = { safe_vus: 0, safe_rps: 0, safety_factor: 0 }
  fixture.data.summary = { executor_count: 0, online_count: 0, available_vus: 0, available_rps: 0 }; fixture.data.rows = []
  const h = setup(() => fixture); await flush()
  assert.equal(h.safetyFactorPercent.value, 0); assert.equal(h.defaults.value.safe_vus, 0); assert.deepEqual(h.rows.value, [])
  const { formatCapacity } = h.load('overview.ts')
  assert.equal(formatCapacity(0), '0'); assert.equal(formatCapacity(1234.567), '1,234.57')
  assert.equal(formatCapacity(null), '—'); assert.equal(formatCapacity(NaN), '—'); h.dispose()
})
test('concurrent manual refreshes share one request and loading lasts until settlement', async () => {
  const job = deferred(), h = setup(() => job.promise), a = h.refresh(), b = h.refresh()
  assert.equal(a, b); await flush(); assert.equal(h.calls.length, 1); assert.equal(h.loading.value, true)
  job.resolve(response()); await a; assert.equal(h.loading.value, false)
  await h.refresh(); assert.equal(h.calls.length, 2); h.dispose()
})
test('network, business and malformed responses preserve last good snapshot and permit retry', async () => {
  for (const broken of [new Error('offline'), { code: 300 }, { code: 200, data: {} }, { ...response(), data: { ...response().data, rows: [{}] } }]) {
    let failure = false
    const h = setup(() => { if (!failure) return response(); if (broken instanceof Error) throw broken; return broken })
    await flush(); failure = true; await h.refresh()
    assert.equal(h.failed.value, true); assert.equal(h.loading.value, false); assert.equal(h.rows.value[0].available_vus, 40)
    failure = false; await h.refresh(); assert.equal(h.failed.value, false); assert.equal(h.loading.value, false); h.dispose()
  }
})
test('first request failure keeps unknown capacity, supports retry, and never fakes empty success', async () => {
  let failure = true; const h = setup(() => { if (failure) throw new Error('offline'); return response() })
  await flush(); assert.equal(h.overview.value, null); assert.equal(h.failed.value, true)
  failure = false; await h.refresh(); assert.equal(h.rows.value.length, 1); assert.equal(h.failed.value, false); h.dispose()
})
for (const key of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`${key} A-B-A invalidates both older responses without clearing new loading`, async () => {
    const jobs = [deferred(), deferred(), deferred()], h = setup(n => jobs[n - 1].promise)
    await flush(); const previous = h.user[key]
    h.user[key] = key === 'token' ? 'changed' : 2; await flush(); h.user[key] = previous; await flush()
    assert.equal(h.calls.length, 3); assert.equal(h.overview.value, null)
    jobs[0].resolve(response('old A')); jobs[1].reject(new Error('old B')); await flush()
    assert.equal(h.loading.value, true); assert.equal(h.failed.value, false); assert.equal(h.overview.value, null)
    jobs[2].resolve(response('new A')); await flush(); assert.equal(h.rows.value[0].executor_name, 'new A'); h.dispose()
  })
}
test('KeepAlive suspension invalidates late reads and resumes once without mounted activation duplicate', async () => {
  const jobs = [deferred(), deferred()], h = setup(n => jobs[n - 1].promise)
  h.hooks.activated.forEach(fn => fn()); await flush(); assert.equal(h.calls.length, 1)
  h.hooks.deactivated.forEach(fn => fn()); jobs[0].resolve(response('old')); await flush()
  assert.equal(h.overview.value, null); assert.equal(h.loading.value, false)
  await h.refresh(); assert.equal(h.calls.length, 1)
  h.hooks.activated.forEach(fn => fn()); await flush(); assert.equal(h.calls.length, 2)
  jobs[1].resolve(response('resumed')); await flush(); assert.equal(h.rows.value[0].executor_name, 'resumed'); h.dispose()
})
test('route leave and reentry reject old response even before deactivation', async () => {
  const jobs = [deferred(), deferred()], h = setup(n => jobs[n - 1].promise); await flush()
  h.route.path = '/other'; h.route.fullPath = '/other'; await flush()
  jobs[0].reject(new Error('late')); await flush(); assert.equal(h.failed.value, false); assert.equal(h.overview.value, null)
  h.route.path = '/perf/capacity/index'; h.route.fullPath = '/perf/capacity/index'; await flush()
  assert.equal(h.calls.length, 2); jobs[1].resolve(response('returned')); await flush()
  assert.equal(h.rows.value[0].executor_name, 'returned'); h.dispose()
})
test('older success after newer success cannot replace current capacity snapshot', async () => {
  const jobs = [deferred(), deferred()], h = setup(n => jobs[n - 1].promise); await flush()
  h.user.selected_environment = 2; await flush()
  jobs[1].resolve(response('current')); await flush(); jobs[0].resolve(response('stale')); await flush()
  assert.equal(h.rows.value[0].executor_name, 'current'); assert.equal(h.loading.value, false); h.dispose()
})
test('identity switch clears already loaded values immediately and reloads with local feedback', async () => {
  const job = deferred(), h = setup(n => n === 1 ? response('first user') : job.promise); await flush()
  h.user.userId = 2
  assert.equal(h.overview.value, null); assert.equal(h.summary.value, null); assert.equal(h.loading.value, true)
  job.resolve(response('second user')); await flush(); assert.equal(h.rows.value[0].executor_name, 'second user'); h.dispose()
})
test('unmount prevents late state writes and does not leave loading active', async () => {
  const job = deferred(), h = setup(() => job.promise); await flush(); h.dispose()
  job.resolve(response()); await flush(); assert.equal(h.overview.value, null); assert.equal(h.loading.value, false)
})
test('DTO validation rejects malformed values instead of rendering NaN or truthy string online state', () => {
  const h = setup(), { readCapacityOverview } = h.load('overview.ts')
  for (const value of [null, Infinity, -1, '', '100', false]) {
    const fixture = response(); fixture.data.defaults.safe_vus = value
    assert.throws(() => readCapacityOverview(fixture))
  }
  for (const value of ['false', 0, null]) {
    const fixture = response(); fixture.data.rows[0].online = value; assert.throws(() => readCapacityOverview(fixture))
  }
  const fixture = response(); fixture.data.summary.executor_count = 1.5; assert.throws(() => readCapacityOverview(fixture))
  h.dispose()
})
test('page SFC script and template compile with local region loading and stable table row identity', () => {
  const filename = path.join(base, 'index.vue'), { descriptor } = parse(readFileSync(filename, 'utf8'))
  const script = compileScript(descriptor, { id: 'capacity-test' })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: 'capacity-test', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
})
test('capacity API keeps the original read-only URL and supplies unknown response boundary', async () => {
  const calls = [], exports = {}, source = readFileSync('src/api/perf/capacity.ts', 'utf8')
  new Function('exports', 'require', ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText)(exports, () => ({ get: options => { calls.push(options); return Promise.resolve(response()) } }))
  await exports.getPerfCapacityOverview(); assert.deepEqual(calls, [{ url: '/perf/capacity/overview' }])
})
