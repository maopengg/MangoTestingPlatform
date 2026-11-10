import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/run/details')
globalThis.window = new EventTarget()
globalThis.document = Object.assign(new EventTarget(), { visibilityState: 'visible' })
const ok = data => ({ code: 200, data })
const overview = patch => ok({ id: 1, name: 'Example run', status: 'running', verdict: 'not_evaluated', engine: 'k6', summary: {}, ...patch })
const request = name => ok([{ id: 1, step_key: '', request_name: name, method: 'GET', url_path: '/example', request_count: 0, failure_count: 0, avg_ms: null, p50_ms: null, p95_ms: null, p99_ms: null, rps: null, max_rps: null }])
const endpoints = ['getPerfRunOverview', 'getPerfRunRequests', 'getPerfRunStages', 'getPerfRunNodes', 'getPerfRunValidity', 'getPerfRunThresholds', 'getPerfRunErrors', 'getPerfRunComparison', 'getPerfRunMetrics']
function setup(overrides = {}) {
  const calls = [], polling = { stops: 0, refresh: null }
  const defaults = {
    getPerfRunOverview: () => overview(), getPerfRunRequests: () => request('Example request'),
    getPerfRunComparison: () => ok({ available: false, metrics: [] }),
    getPerfRunMetrics: () => ok({ run_id: 1, cursor: 'cursor', has_more: false, run_status: 'running', verdict: 'not_evaluated', points: [] }),
  }
  const api = Object.fromEntries(endpoints.map(name => [name, (...args) => { calls.push({ name, args }); return Promise.resolve().then(() => (overrides[name] || defaults[name] || (() => ok([])))(...args)) }]))
  const h = harness('index', 'overviewRecord,overviewRegion,requestRegion,stageRegion,nodeRegion,validityRegion,thresholdRegion,errorRegion,comparisonRegion,resultRegions,metricStream,overviewLoading,requestsLoading,stagesLoading,nodesLoading,validityLoading,thresholdsLoading,errorsLoading,comparisonLoading,metricsLoading,overviewError,requestsError,comparisonError,requests,errors,refreshFinal,refreshAll,retryRegion,readFinalPending:()=>finalRefreshPending', {
    base, modules: {
      'vue-router': { useRoute: () => ({ path: '/perf/run/details', fullPath: '/perf/run/details?id=1', query: { id: '1' } }), useRouter: () => ({}) },
      '@/store/modules/user': { default: () => ({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }) },
      '@/api/perf': { ...api, unsubscribePerfRun: async () => ok({}) },
      echarts: {}, '@/utils/chartDensity': {},
      '@/hooks/use-page-polling': { usePagePolling: refresh => { polling.refresh = refresh; return { start() {}, stop() { polling.stops++ }, pause() {}, resume() {}, isAvailable: () => true } } },
    },
  })
  return { ...h, calls, polling, poll: () => polling.refresh({ isCurrent: () => true }), count: name => calls.filter(call => call.name === name).length }
}

test('actual page publishes fast regions and releases their loading while a different region is pending', async () => {
  const nodes = deferred(), h = setup({ getPerfRunNodes: () => nodes.promise })
  const job = h.refreshFinal(); await flush()
  assert.equal(h.overviewRecord.value.name, 'Example run'); assert.equal(h.overviewLoading.value, false)
  assert.equal(h.requests.value[0].request_name, 'Example request'); assert.equal(h.requestsLoading.value, false)
  assert.equal(h.nodesLoading.value, true); assert.equal(h.nodeRegion.hasLoaded.value, false)
  assert.equal(h.comparisonLoading.value, false); assert.equal(h.comparisonRegion.hasLoaded.value, true)
  nodes.resolve(ok([])); await job
  assert.equal(h.nodesLoading.value, false); assert.equal(h.readFinalPending(), false); h.close()
})
test('one failed endpoint leaves other successful regions available and final refresh pending', async () => {
  const h = setup({ getPerfRunRequests: () => { throw Error('offline') } })
  await assert.rejects(h.refreshFinal())
  assert.ok(h.requestsError.value); assert.equal(h.requestRegion.hasLoaded.value, false)
  assert.equal(h.overviewRegion.hasLoaded.value, true); assert.equal(h.errorRegion.hasLoaded.value, true)
  assert.equal(h.errorsLoading.value, false); assert.equal(h.requestsLoading.value, false)
  assert.equal(h.readFinalPending(), true); assert.equal(h.polling.stops, 0); h.close()
})
test('failed refresh preserves the last successful request snapshot and retry only reloads that region', async () => {
  let broken = false
  const h = setup({ getPerfRunRequests: () => broken ? ok([{}]) : request('Saved request') })
  await h.refreshFinal(); const saved = h.requests.value; broken = true
  await assert.rejects(h.refreshFinal()); assert.equal(h.requests.value, saved)
  const before = h.calls.length; broken = false; await h.retryRegion(h.requestRegion)
  assert.equal(h.calls.length, before + 1); assert.equal(h.calls.at(-1).name, 'getPerfRunRequests')
  assert.equal(h.requestsError.value, ''); assert.equal(h.requestsLoading.value, false); h.close()
})
test('overlapping refreshes share one physical request per region and do not release loading early', async () => {
  const response = deferred(), h = setup({ getPerfRunRequests: () => response.promise })
  const a = h.refreshFinal(), b = h.refreshFinal(true); await flush()
  for (const name of endpoints.filter(name => name !== 'getPerfRunMetrics')) assert.equal(h.count(name), 1, name)
  assert.equal(h.requestsLoading.value, true); response.resolve(request('Shared'))
  await Promise.all([a, b]); assert.equal(h.requestsLoading.value, false); h.close()
})
test('silent page polling retries initial region failure without opening region loading', async () => {
  let broken = true
  const h = setup({ getPerfRunRequests: () => { if (broken) throw Error('offline'); return request('Recovered') } })
  await assert.rejects(h.refreshFinal()); broken = false
  const poll = h.poll()
  for (const key of ['overviewLoading', 'requestsLoading', 'stagesLoading', 'nodesLoading', 'validityLoading', 'thresholdsLoading', 'errorsLoading', 'comparisonLoading', 'metricsLoading']) assert.equal(h[key].value, false, key)
  await poll; assert.equal(h.requests.value[0].request_name, 'Recovered'); assert.equal(h.requestsError.value, '')
  assert.equal(h.polling.stops, 0); h.close()
})
test('failed initial overview is retried by page polling and cannot masquerade as a finished run', async () => {
  let broken = true
  const h = setup({ getPerfRunOverview: () => { if (broken) throw Error('offline'); return overview() } })
  await assert.rejects(h.refreshFinal()); assert.equal(h.overviewRecord.value, null)
  await h.poll(); assert.equal(h.polling.stops, 0); assert.ok(h.overviewError.value)
  broken = false; await h.poll(); assert.equal(h.overviewRecord.value.status, 'running')
  assert.equal(h.overviewError.value, ''); assert.equal(h.overviewLoading.value, false); h.close()
})
test('terminal partial failure keeps polling until final results succeed, then stops', async () => {
  let broken = true
  const h = setup({
    getPerfRunOverview: () => overview({ status: 'completed', verdict: 'passed' }),
    getPerfRunRequests: () => { if (broken) throw Error('offline'); return request('Final') },
    getPerfRunMetrics: () => ok({ run_id: 1, cursor: 'done', has_more: false, run_status: 'completed', verdict: 'passed', points: [] }),
  })
  await assert.rejects(h.poll()); assert.equal(h.readFinalPending(), true); assert.equal(h.polling.stops, 0)
  broken = false; await h.poll(); assert.equal(h.requests.value[0].request_name, 'Final')
  assert.equal(h.readFinalPending(), false); assert.equal(h.polling.stops, 1); h.close()
})
test('actual page manual refresh merges concurrent clicks and settles even when one region fails', async () => {
  const response = deferred(), h = setup({ getPerfRunRequests: () => response.promise })
  const first = h.refreshAll(), repeated = h.refreshAll(); await flush()
  assert.equal(h.count('getPerfRunRequests'), 1); response.reject(Error('offline'))
  await Promise.all([first, repeated]); assert.equal(h.requestsLoading.value, false)
  assert.ok(h.requestsError.value); h.close()
})
test('page disposal invalidates every outstanding result request and its late error', async () => {
  const response = deferred(), h = setup({ getPerfRunRequests: () => response.promise })
  const job = h.refreshFinal(); await flush(); h.close(); response.reject(Error('late'))
  await job; assert.equal(h.requests.value.length, 0); assert.equal(h.requestsError.value, '')
  assert.equal(h.requestsLoading.value, false); assert.equal(h.overviewRecord.value, null)
})
test('region reset protects A-B-A responses and old finally cannot clear the new request loading', async () => {
  const h = setup(), first = deferred(), second = deferred()
  let next = first, id = '1'
  const region = h.load('composables/useRunResultRegion.ts').useRunResultRegion({ runId: () => id, initial: () => null,
    request: () => next.promise, read: value => value, failureMessage: 'Failed',
  })
  const a = region.load(); await flush(); id = '2'; region.reset(); id = '1'; region.reset()
  next = second; const b = region.load(); await flush()
  first.resolve('old A'); await a; assert.equal(region.data.value, null); assert.equal(region.loading.value, true)
  second.resolve('new A'); assert.equal(await b, true); assert.equal(region.data.value, 'new A')
  assert.equal(region.loading.value, false); region.dispose(); h.close()
})
test('region skips absent ID and expired context, and rejects an invalidated response without publishing it', async () => {
  const h = setup(), response = deferred(); let id = null, current = true, calls = 0
  const region = h.load('composables/useRunResultRegion.ts').useRunResultRegion({ runId: () => id, initial: () => [],
    request: () => { calls++; return response.promise }, read: value => value, failureMessage: 'Failed',
  })
  assert.equal(await region.load(), false); assert.equal(calls, 0)
  id = '1'; current = false; assert.equal(await region.load(true, { isCurrent: () => current }), false)
  current = true; const job = region.load(false, { isCurrent: () => current }); await flush(); current = false
  response.resolve(['old']); assert.equal(await job, false); assert.deepEqual(region.data.value, [])
  assert.equal(region.hasLoaded.value, false); assert.equal(region.loading.value, false); region.dispose(); h.close()
})
