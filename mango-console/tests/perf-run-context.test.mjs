import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { harness, deferred } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/run/details')
const ok = data => ({ code: 200, data })
function moduleAt(filename, modules = {}) {
  const exports = {}
  const source = ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, id => { if (!(id in modules)) { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error(`Unmocked ${id}`); } return modules[id] })
  return exports
}
async function settle() { for (let i = 0; i < 60; i++) await Promise.resolve(); await vue.nextTick() }
function clock() {
  let now = 0, sequence = 0
  const tasks = new Map()
  return {
    tasks,
    setTimeout(fn, delay = 0) { const id = ++sequence; tasks.set(id, { fn, at: now + delay }); return id },
    clearTimeout(id) { tasks.delete(id) },
    async advance(milliseconds) {
      const end = now + milliseconds
      for (let n = 0; n < 1000; n++) {
        const next = [...tasks].filter(([, value]) => value.at <= end).sort((a, b) => a[1].at - b[1].at)[0]
        if (!next) { now = end; await settle(); return }
        now = next[1].at; tasks.delete(next[0]); next[1].fn(); await settle()
      }
      throw Error('Unbounded timers')
    },
  }
}
function setup(options = {}) {
  const saved = { window: globalThis.window, document: globalThis.document, setTimeout: globalThis.setTimeout, clearTimeout: globalThis.clearTimeout, ResizeObserver: globalThis.ResizeObserver, getComputedStyle: globalThis.getComputedStyle }
  const time = clock(), hooks = { mounted: [], activated: [], deactivated: [], unmounted: [] }
  const surface = Object.assign(new EventTarget(), { setTimeout: time.setTimeout, location: { href: 'https://example.com/perf/run/details?id=1' } })
  const links = [], doc = Object.assign(new EventTarget(), { visibilityState: options.hidden ? 'hidden' : 'visible', documentElement: {}, body: { appendChild() {} }, createElement() { const link = { removed: false, click() { links.push(link); if (options.throwClick) throw Error('click failed') }, remove() { link.removed = true } }; return link } })
  Object.assign(globalThis, { window: surface, document: doc, setTimeout: time.setTimeout, clearTimeout: time.clearTimeout,
    ResizeObserver: class { observe() {} disconnect() {} }, getComputedStyle: () => ({ getPropertyValue: () => '' }),
  })
  const route = vue.reactive({ path: '/perf/run/details', fullPath: '/perf/run/details?id=1', query: { id: options.id ?? '1' } })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-A', selected_environment: 0 })
  const calls = [], dialogs = [], messages = [], charts = []
  const vueHooks = { ...vue, ...Object.fromEntries(Object.entries({ onMounted: 'mounted', onActivated: 'activated', onDeactivated: 'deactivated', onBeforeUnmount: 'unmounted' }).map(([name, key]) => [name, fn => hooks[key].push(fn)])) }
  const pollingUtil = moduleAt(path.resolve('src/utils/page-polling.ts'))
  const pollingHook = moduleAt(path.resolve('src/hooks/use-page-polling.ts'), { vue: vueHooks, 'vue-router': { useRoute: () => route }, '@/utils/page-polling': pollingUtil })
  const defaults = {
    getPerfRunOverview: id => ok({ id: Number(id), name: `Run ${id}`, status: 'running', verdict: 'not_evaluated', engine: 'k6', scenario_id: 10, summary: {}, test_env: 0 }),
    getPerfRunMetrics: id => ok({ run_id: Number(id), cursor: `cursor-${id}`, has_more: false, run_status: 'running', verdict: 'not_evaluated', points: [] }),
    getPerfRunComparison: () => ok({ available: false, metrics: [] }),
    getPerfRunRequests: id => ok([{ id: 1, request_name: `Request ${id}`, step_key: '', method: 'GET', url_path: '/example', request_count: 0, failure_count: 0 }]),
    exportPerfRun: async id => ({ data: new Blob([JSON.stringify({ schema_version: 1, run: { id: Number(id) } })], { type: 'application/json' }) }),
  }
  const names = ['getPerfRunOverview', 'getPerfRunMetrics', 'getPerfRunComparison', 'getPerfRunRequests', 'getPerfRunStages', 'getPerfRunNodes', 'getPerfRunValidity', 'getPerfRunThresholds', 'getPerfRunErrors', 'subscribePerfRun', 'unsubscribePerfRun', 'stopPerfRun', 'setPerfRunBaseline', 'exportPerfRun', 'getPerfRunCaptureDownload']
  const api = Object.fromEntries(names.map(name => [name, (...args) => {
    const call = { name, args, userId: user.userId, roleId: user.roleId, environment: user.selected_environment }; calls.push(call)
    return Promise.resolve().then(() => (options.api?.[name] || defaults[name] || (() => ok([])))(...args, call))
  }]))
  const h = harness('index', 'id,runContext,overviewRecord,overviewRegion,requestRegion,requests,kpis,clientMetricGroups,overviewLoading,requestsLoading,overviewError,metricsError,subscriptionError,metricStream,refreshAll,refreshFinal,loadMetrics,handleWebsocket,renderChart,chartRef,loadChartRef,resourceChartRef,stop,stopping,baseline,baselineSaving,exportReport,exporting,downloadCapture,captureDownloadingNodeId,rerun', { base, modules: {
    vue: vueHooks, 'vue-router': { useRoute: () => route, useRouter: () => ({ push() {}, back() {} }) },
    '@/store/modules/user': { default: () => user }, '@/hooks/use-page-polling': pollingHook, '@/api/perf': api,
    '@/utils/chartDensity': { makeChartDensityAware: value => value },
    echarts: { init() { const chart = { updates: 0, disposed: false, option: null, setOption(option) { chart.updates++; chart.option = option }, resize() {}, dispose() { chart.disposed = true } }; charts.push(chart); return chart } },
    '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(type => [type, text => messages.push({ type, text })])), Modal: { confirm(config) { const dialog = { config, closed: false, close() { dialog.closed = true; config.onClose?.() } }; dialogs.push(dialog); return dialog } } },
  } })
  hooks.mounted.forEach(fn => fn())
  return { ...h, time, user, route, hooks, calls, dialogs, messages, charts, links,
    count: name => calls.filter(call => call.name === name).length,
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    websocket(detail) { surface.dispatchEvent(Object.assign(new Event('mango:websocket-message'), { detail })) },
    async dispose() { hooks.unmounted.forEach(fn => fn()); h.close(); await settle(); Object.assign(globalThis, saved) },
  }
}

test('same-route run A-B-A clears synchronously and late A cannot replace the newest A', async () => {
  const jobs = [deferred(), deferred(), deferred()]; let n = 0
  const h = setup({ api: { getPerfRunOverview: () => jobs[n++].promise } }); await settle()
  h.route.query.id = '2'; assert.equal(h.overviewRecord.value, null); await settle()
  h.route.query.id = '1'; await settle(); assert.equal(n, 3)
  jobs[0].resolve(ok({ id: 1, name: 'old A', status: 'running', verdict: '', engine: 'k6' })); jobs[1].reject(Error('old B')); await settle()
  assert.equal(h.overviewRecord.value, null); assert.equal(h.overviewLoading.value, true); assert.equal(h.overviewError.value, '')
  jobs[2].resolve(ok({ id: 1, name: 'new A', status: 'running', verdict: '', engine: 'k6' })); await settle()
  assert.equal(h.overviewRecord.value.name, 'new A'); assert.equal(h.overviewLoading.value, false); await h.dispose()
})
for (const field of ['userId', 'roleId', 'token', 'selected_environment']) test(`${field} A-B-A invalidates actual page readers, including pending errors`, async () => {
  const jobs = [deferred(), deferred(), deferred()]; let n = 0
  const h = setup({ api: { getPerfRunOverview: () => jobs[n++].promise } }); await settle()
  const saved = h.user[field]; h.user[field] = field === 'token' ? 'fixture-B' : 2; await settle(); h.user[field] = saved; await settle()
  assert.equal(n, 3); jobs[0].reject(Error('old A')); jobs[1].resolve(ok({ id: 1, name: 'old B', status: 'running', verdict: '', engine: 'k6' })); await settle()
  assert.equal(h.overviewRecord.value, null); assert.equal(h.overviewLoading.value, true); assert.equal(h.overviewError.value, '')
  jobs[2].resolve(ok({ id: 1, name: 'current A', status: 'running', verdict: '', engine: 'k6' })); await settle()
  assert.equal(h.overviewRecord.value.name, 'current A'); await h.dispose()
})
test('invalid or ambiguous query IDs never request an endpoint, including subscriptions', async () => {
  const h = setup({ id: 'invalid' }); await settle(); assert.equal(h.id.value, null); assert.equal(h.calls.length, 0)
  for (const id of ['', '0', '-1', '1.5', '1e2', ' 1 ', ['1', '2'], '9007199254740992']) {
    h.route.query.id = id; await settle(); assert.equal(h.id.value, null); assert.equal(h.calls.length, 0)
  }
  h.route.query.id = '001'; await settle(); assert.equal(h.id.value, '1'); assert.equal(h.overviewRecord.value.id, 1); await h.dispose()
})
test('background pause preserves the snapshot, ignores a pending response and stops all renewals', async () => {
  let pending = null
  const h = setup({ api: { getPerfRunOverview: id => pending ? pending.promise : ok({ id: Number(id), name: 'saved', status: 'running', verdict: '', engine: 'k6' }) } }); await settle()
  pending = deferred(); const job = h.refreshAll(); await settle(); h.visibility('hidden')
  assert.equal(h.overviewRecord.value.name, 'saved'); assert.equal(h.overviewLoading.value, false)
  pending.resolve(ok({ id: 1, name: 'late hidden', status: 'running', verdict: '', engine: 'k6' })); await job; await settle()
  assert.equal(h.overviewRecord.value.name, 'saved'); const reads = h.count('getPerfRunOverview'), subscriptions = h.count('subscribePerfRun')
  await h.time.advance(60000); assert.equal(h.count('getPerfRunOverview'), reads); assert.equal(h.count('subscribePerfRun'), subscriptions)
  pending = null; h.visibility('visible'); await settle(); assert.ok(h.count('getPerfRunOverview') > reads)
  assert.equal(h.overviewLoading.value, false); await h.dispose()
})
test('a context first opened or changed while hidden waits, then shows initial region loading on return', async () => {
  const h = setup({ hidden: true }); await settle(); assert.equal(h.calls.length, 0)
  h.user.roleId = 2; await settle(); assert.equal(h.calls.length, 0)
  h.visibility('visible'); assert.equal(h.overviewLoading.value, true); assert.equal(h.requestsLoading.value, true)
  await settle(); assert.equal(h.overviewLoading.value, false); assert.equal(h.overviewRecord.value.id, 1); await h.dispose()
})
test('KeepAlive deactivation ignores late reads and activation restores reads and the live lease', async () => {
  const pending = deferred(); let blocked = true
  const h = setup({ api: { getPerfRunOverview: () => blocked ? pending.promise : ok({ id: 1, name: 'resumed', status: 'running', verdict: '', engine: 'k6' }) } }); await settle()
  h.hooks.deactivated.forEach(fn => fn()); pending.reject(Error('late')); await settle()
  assert.equal(h.overviewRecord.value, null); assert.equal(h.overviewError.value, '')
  const before = h.calls.length; await h.time.advance(60000); assert.equal(h.calls.length, before)
  blocked = false; h.hooks.activated.forEach(fn => fn()); await settle()
  assert.equal(h.overviewRecord.value.name, 'resumed'); assert.equal(h.overviewLoading.value, false); await h.dispose()
})
test('route departure prevents further reads, and returning uses the latest route ID', async () => {
  const h = setup(); await settle(); h.route.path = '/perf/run/index'; await settle()
  const before = h.calls.length; await h.time.advance(60000); assert.equal(h.calls.length, before)
  h.route.query.id = '2'; await settle(); assert.equal(h.calls.length, before)
  h.route.path = '/perf/run/details'; await settle(); assert.equal(h.overviewRecord.value.id, 2)
  assert.ok(h.calls.filter(c => c.name === 'subscribePerfRun').at(-1).args[0] === '2'); await h.dispose()
})
test('actual public polling retries created/running failures every five seconds without region loading', async () => {
  let fail = false, status = 'created'
  const h = setup({ api: {
    getPerfRunOverview: () => { if (fail) throw Error('offline'); return ok({ id: 1, name: 'pending', status, verdict: '', engine: 'k6' }) },
    getPerfRunMetrics: () => { if (fail) throw Error('offline'); return ok({ run_id: 1, cursor: 'one', has_more: false, run_status: status, verdict: '', points: [] }) },
  } }); await settle(); const before = h.count('getPerfRunOverview')
  fail = true; await h.time.advance(5000); assert.ok(h.overviewError.value); assert.ok(h.metricsError.value)
  assert.equal(h.overviewLoading.value, false); assert.equal(h.count('getPerfRunOverview'), before + 1)
  fail = false; status = 'running'; await h.time.advance(5000)
  assert.equal(h.overviewRecord.value.status, 'running'); assert.equal(h.overviewError.value, ''); assert.equal(h.overviewLoading.value, false); await h.dispose()
})
test('malformed, foreign and suspended WebSocket updates cannot enqueue a metric read', async () => {
  const h = setup(); await settle(); const before = h.count('getPerfRunMetrics')
  for (const detail of [null, [], { data: { func_name: 'perf_run_update', func_args: { run_id: 2 } } }, { data: { func_name: 'other', func_args: { run_id: 1 } } }]) h.websocket(detail)
  await h.time.advance(150); assert.equal(h.count('getPerfRunMetrics'), before)
  h.websocket({ data: { func_name: 'perf_run_update', func_args: { run_id: 1 } } }); h.visibility('hidden')
  await h.time.advance(150); assert.equal(h.count('getPerfRunMetrics'), before)
  h.visibility('visible'); await settle(); const resumed = h.count('getPerfRunMetrics')
  h.websocket({ data: { func_name: 'perf_run_update', func_args: { run_id: 1 } } }); await h.time.advance(150)
  assert.equal(h.count('getPerfRunMetrics'), resumed + 1); await h.dispose()
})
test('subscriptions renew at thirty seconds and recover after a failed renewal', async () => {
  let attempts = 0
  const h = setup({ api: { subscribePerfRun: () => { if (++attempts === 2) throw Error('offline'); return ok({}) } } }); await settle()
  assert.equal(attempts, 1); await h.time.advance(30000); assert.equal(attempts, 2); assert.ok(h.subscriptionError.value)
  await h.time.advance(30000); assert.equal(attempts, 3); assert.equal(h.subscriptionError.value, ''); await h.dispose()
})
test('pending subscribe and cleanup are serialized across route A-B-A before renewing latest A', async () => {
  const first = deferred(); let attempts = 0
  const h = setup({ api: { subscribePerfRun: () => ++attempts === 1 ? first.promise : ok({}) } }); await settle()
  h.route.query.id = '2'; await settle(); h.route.query.id = '1'; await settle(); assert.equal(attempts, 1)
  first.resolve(ok({})); await settle()
  assert.deepEqual(h.calls.filter(call => ['subscribePerfRun', 'unsubscribePerfRun'].includes(call.name)).map(call => [call.name, call.args[0]]), [['subscribePerfRun', '1'], ['unsubscribePerfRun', '1'], ['subscribePerfRun', '1']])
  await h.dispose()
})
test('identity changes do not send an old lease cleanup under the new identity', async () => {
  const h = setup(); await settle(); h.user.token = 'fixture-B'; await settle()
  assert.equal(h.count('unsubscribePerfRun'), 0)
  assert.deepEqual(h.calls.filter(call => call.name === 'subscribePerfRun').map(call => call.args[1]), ['fixture-A', 'fixture-B'])
  await h.dispose()
})
test('queued chart work is ignored after deactivation; theme refresh and disposal use live instances only', async () => {
  const h = setup(); await settle(); h.chartRef.value = {}; h.loadChartRef.value = {}
  h.renderChart(); h.hooks.deactivated.forEach(fn => fn()); await settle(); assert.equal(h.charts.length, 0)
  h.hooks.activated.forEach(fn => fn()); await settle(); assert.equal(h.charts.length, 2)
  const updates = h.charts[0].updates; window.dispatchEvent(new Event('mango-theme-change')); await settle(); assert.ok(h.charts[0].updates > updates)
  h.visibility('hidden'); assert.ok(h.charts.every(chart => chart.disposed)); await h.dispose()
})
test('stop holds its physical lock across identity changes and ignores stale success', async () => {
  const result = deferred(), h = setup({ api: { stopPerfRun: () => result.promise } }); await settle()
  const job = h.stop(); await settle(); h.user.roleId = 2; await settle(); await h.stop()
  assert.equal(h.count('stopPerfRun'), 1); assert.equal(h.stopping.value, true)
  result.resolve(ok({})); await job; assert.equal(h.stopping.value, false); assert.equal(h.messages.filter(m => m.type === 'success').length, 0); await h.dispose()
})
test('baseline confirmation captures the record, closes on switch, and holds the save lock until settlement', async () => {
  const result = deferred()
  const h = setup({ api: { getPerfRunOverview: id => ok({ id: Number(id), name: `Run ${id}`, status: 'completed', verdict: 'passed', engine: 'k6' }), setPerfRunBaseline: () => result.promise } }); await settle()
  h.baseline(); const dialog = h.dialogs[0]; assert.equal(typeof dialog.config.onBeforeOk, 'function')
  const job = dialog.config.onBeforeOk(); await settle(); h.route.query.id = '2'; await settle()
  assert.equal(dialog.closed, true); h.baseline(); assert.equal(h.dialogs.length, 1); assert.equal(h.baselineSaving.value, true)
  assert.deepEqual(h.calls.find(c => c.name === 'setPerfRunBaseline').args.slice(0, 2), ['1', 'Run 1'])
  result.resolve(ok({})); await job; assert.equal(h.baselineSaving.value, false); assert.equal(h.messages.filter(m => m.type === 'success').length, 0); await h.dispose()
})
test('subscription API preserves endpoints and payload while pinning the provided authorization', async () => {
  const calls = [], capture = config => { calls.push(config); return Promise.resolve(ok({})) }
  const api = moduleAt(path.resolve('src/api/perf/index.ts'), { '@/api/http': { post: capture, http: capture }, '@/api/axios.config': {} })
  await api.subscribePerfRun('1', 'fixture-A'); await api.unsubscribePerfRun('1', 'fixture-A')
  assert.equal(calls[0].url, '/perf/run/1/realtime-subscription'); assert.equal(calls[1].method, 'DELETE')
  assert.deepEqual(calls.map(c => c.headers), [{ Authorization: 'fixture-A' }, { Authorization: 'fixture-A' }]); assert.deepEqual(calls.map(c => c.data()), [{}, {}])
})
test('an old metric batch cannot restore its cursor, points or terminal state after identity invalidation', async () => {
  const first = deferred(); let n = 0
  const h = setup({ api: { getPerfRunMetrics: () => ++n === 1 ? first.promise : ok({ run_id: 1, cursor: 'current', has_more: false, run_status: 'running', verdict: '', points: [] }) } }); await settle()
  h.user.roleId = 2; await settle(); assert.equal(h.metricStream.readCursor(), 'current')
  first.resolve(ok({ run_id: 1, cursor: 'obsolete', has_more: true, run_status: 'completed', verdict: 'passed', points: [] })); await settle()
  assert.equal(h.metricStream.readCursor(), 'current'); assert.equal(h.overviewRecord.value.status, 'running'); assert.equal(n, 2)
  await h.time.advance(5000); assert.ok(n > 2); await h.dispose()
})
test('a subscription completing after unmount is cleaned up without restarting renewal or polling', async () => {
  const first = deferred(), h = setup({ api: { subscribePerfRun: () => first.promise } }); await settle()
  h.hooks.unmounted.forEach(fn => fn()); first.resolve(ok({})); await settle()
  assert.equal(h.count('subscribePerfRun'), 1); assert.equal(h.count('unsubscribePerfRun'), 1)
  assert.equal(h.time.tasks.size, 0); await h.dispose()
})
test('stop failure restores its button and retry checks business success before reporting success', async () => {
  let fail = true
  const h = setup({ api: { stopPerfRun: () => fail ? { code: 400 } : ok({}) } }); await settle()
  await h.stop(); assert.equal(h.stopping.value, false); assert.equal(h.messages.at(-1).type, 'error')
  fail = false; await h.stop(); assert.equal(h.count('stopPerfRun'), 2); assert.equal(h.messages.at(-1).type, 'success'); await h.dispose()
})
test('a committed stop is not reported as failed when only the follow-up overview refresh fails', async () => {
  let failRead = false
  const h = setup({ api: { getPerfRunOverview: () => { if (failRead) throw Error('offline'); return ok({ id: 1, name: 'Run', status: 'running', verdict: '', engine: 'k6' }) } } }); await settle()
  failRead = true; await h.stop()
  assert.equal(h.stopping.value, false); assert.ok(h.overviewError.value)
  assert.equal(h.messages.filter(message => message.type === 'error').length, 1)
  assert.equal(h.messages.find(message => message.type === 'success').text, '停止请求已提交'); await h.dispose()
})
test('baseline failed confirmation stays retryable and duplicate confirmation cannot send another save', async () => {
  let result = deferred()
  const h = setup({ api: { getPerfRunOverview: () => ok({ id: 1, name: 'Baseline', status: 'completed', verdict: 'passed', engine: 'k6' }), setPerfRunBaseline: () => result.promise } }); await settle()
  h.baseline(); h.baseline(); assert.equal(h.dialogs.length, 1)
  const dialog = h.dialogs[0], first = dialog.config.onBeforeOk(); await settle()
  assert.equal(await dialog.config.onBeforeOk(), false); assert.equal(h.count('setPerfRunBaseline'), 1)
  result.reject(Error('offline')); assert.equal(await first, false); assert.equal(h.baselineSaving.value, false)
  result = deferred(); const second = dialog.config.onBeforeOk(); await settle(); result.resolve(ok({}))
  assert.equal(await second, true); assert.equal(h.count('setPerfRunBaseline'), 2); await h.dispose()
})
test('export rejects error JSON, malformed and foreign-run blobs and releases its physical lock', async () => {
  let response = { data: new Blob([JSON.stringify({ code: 403, msg: 'denied' })]) }
  const h = setup({ api: { exportPerfRun: () => response } }); await settle()
  for (const blob of [response.data, new Blob(['bad json']), new Blob([]), new Blob([JSON.stringify({ schema_version: 1, run: { id: 2 } })])]) {
    response = { data: blob }; await h.exportReport(); assert.equal(h.exporting.value, false); assert.equal(h.links.length, 0)
  }
  response = { data: new Blob([JSON.stringify({ schema_version: 1, run: { id: 1 } })]) }
  await h.exportReport(); assert.equal(h.links.length, 1); assert.equal(h.links[0].download, 'perf-run-1.json'); assert.equal(h.links[0].removed, true); await h.dispose()
})
test('export holds its lock across switches and a stale report never creates a download', async () => {
  const result = deferred(), h = setup({ api: { exportPerfRun: () => result.promise } }); await settle()
  const job = h.exportReport(); h.route.query.id = '2'; await settle(); await h.exportReport()
  assert.equal(h.count('exportPerfRun'), 1); assert.equal(h.exporting.value, true)
  result.resolve({ data: new Blob([JSON.stringify({ schema_version: 1, run: { id: 1 } })]) }); await job
  assert.equal(h.links.length, 0); assert.equal(h.exporting.value, false); await h.dispose()
})
test('object URL and anchor are cleaned even when the browser download click throws', async () => {
  const create = URL.createObjectURL, revoke = URL.revokeObjectURL, revoked = []
  URL.createObjectURL = () => 'blob:example'; URL.revokeObjectURL = url => revoked.push(url)
  const h = setup({ throwClick: true }); await settle()
  try {
    await h.exportReport(); assert.deepEqual(revoked, ['blob:example']); assert.equal(h.links[0].removed, true); assert.equal(h.exporting.value, false)
  } finally { await h.dispose(); URL.createObjectURL = create; URL.revokeObjectURL = revoke }
})
test('capture download validates the selected node and URL scheme, and recovers after failure', async () => {
  let url = 'javascript:alert(1)'
  const h = setup({ api: {
    getPerfRunNodes: () => ok([{ id: 7, shard_index: 0, status: 'completed', capture: { status: 'uploaded', bytes: 0 } }]),
    getPerfRunCaptureDownload: () => ok({ url, name: 'sample.csv' }),
  } }); await settle()
  await h.downloadCapture(99); assert.equal(h.count('getPerfRunCaptureDownload'), 0)
  await h.downloadCapture(7); assert.equal(h.links.length, 0); assert.equal(h.captureDownloadingNodeId.value, null)
  url = 'https://example.com/sample.csv'; await h.downloadCapture(7)
  assert.equal(h.links[0].download, 'sample.csv'); assert.equal(h.links[0].removed, true); await h.dispose()
})
test('unknown KPI and chart samples remain missing, while measured zero is preserved', async () => {
  const h = setup(); assert.equal(h.kpis.value[0].value, '-'); await settle()
  const raw = h.load('records.ts').readRunMetricPage(ok({ run_id: 1, cursor: 'one', has_more: false, run_status: 'running', verdict: '', points: [0, 1].map(index => ({ node_id: 1, window_start: `2026-11-07T10:00:0${index}`, window_seconds: 1, request_count: 0, failure_count: 0, iteration_count: 0, dropped_count: 0, response_time_sum_ms: 0, bytes_sent: 0, bytes_received: 0, connection_count: 0, connect_error_count: 0, generator_metrics: index === 0 ? { cpu_percent: 0 } : {} })) }), '1').points
  h.metricStream.points.value = h.load('metrics.ts').mergeRunMetricPoints([], raw)
  h.chartRef.value = {}; h.loadChartRef.value = {}; h.resourceChartRef.value = {}; h.renderChart(); await settle()
  assert.deepEqual(h.charts[0].option.series[1].data, [null, null])
  assert.deepEqual(h.charts[1].option.series[0].data, [null, null])
  assert.deepEqual(h.charts[2].option.series[0].data, [0, null]); assert.deepEqual(h.charts[2].option.series[1].data, [null, null]); await h.dispose()
})
