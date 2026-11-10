import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/run/details')
globalThis.window = new EventTarget()
globalThis.document = Object.assign(new EventTarget(), { visibilityState: 'visible' })
const page = (cursor, has_more = false, patch = {}) => ({ code: 200, data: {
  run_id: 1, cursor, has_more, run_status: 'running', verdict: 'not_evaluated', points: [], ...patch,
} })
const point = (node_id = 1) => ({ node_id, window_start: '2026-11-07T10:00:00', window_seconds: 1,
  request_count: 10, failure_count: 0, iteration_count: 1, dropped_count: 0, response_time_sum_ms: 100,
  bytes_sent: 10, bytes_received: 20, connection_count: 1, connect_error_count: 0 })
function setup(request, onDrained) {
  const h = harness('index', '', { base, modules: {
    'vue-router': { useRoute: () => ({ path: '/perf/run/details', query: { id: '1' } }), useRouter: () => ({}) },
    '@/store/modules/user': { default: () => ({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }) },
    '@/api/perf': { getPerfRunMetrics: request, unsubscribePerfRun: async () => ({ code: 200 }) },
    echarts: {}, '@/utils/chartDensity': {},
    '@/hooks/use-page-polling': { usePagePolling: () => ({ stop() {}, pause() {} }) },
  } })
  let id = '1', draws = 0
  const drained = []
  const stream = h.load('composables/useRunMetricStream.ts').useRunMetricStream({
    runId: () => id, onPoints: () => draws++, onDrained: async (value, context) => {
      assert.equal(context.isCurrent(), true)
      await onDrained?.(value, context)
      drained.push(value)
    },
  })
  return { stream, drained, draws: () => draws, select(value) { id = value; stream.reset() }, close() { stream.dispose(); h.close() } }
}

test('drains opaque pages in order and publishes terminal status only after the final batch', async () => {
  const second = deferred(), calls = []
  const h = setup(async (id, params) => {
    calls.push([id, { ...params }])
    return calls.length === 1 ? page('next', true, { points: [point()], run_status: 'completed' }) : second.promise
  })
  const job = h.stream.load(); await flush()
  assert.equal(h.stream.metricsLoading.value, true); assert.equal(h.drained.length, 0)
  assert.equal(h.stream.points.value[0].request_count, 10)
  second.resolve(page('last', false, { points: [point(2)], run_status: 'completed', verdict: 'passed' })); await job
  assert.deepEqual(calls.map(([, args]) => args.cursor), ['', 'next'])
  assert.ok(calls.every(([id, args]) => id === '1' && args.scope_type === 'global' && args.max_points === 1000))
  assert.equal(h.stream.readCursor(), 'last'); assert.equal(h.stream.points.value[0].request_count, 20)
  assert.equal(h.drained[0].run_status, 'completed'); assert.equal(h.draws(), 2)
  assert.equal(h.stream.metricsLoading.value, false); h.close()
})
test('overlapping WebSocket, polling and manual refresh share one physical stream and manual loading', async () => {
  const response = deferred(); let calls = 0
  const h = setup(() => { calls++; return response.promise })
  const silent = h.stream.load(true), manual = h.stream.load(), websocket = h.stream.load(true)
  assert.equal(silent, manual); assert.equal(websocket, silent); assert.equal(calls, 1)
  assert.equal(h.stream.metricsLoading.value, true)
  response.resolve(page('done')); await Promise.all([silent, manual, websocket])
  assert.equal(h.drained.length, 1); assert.equal(h.stream.metricsLoading.value, false); h.close()
})
test('failed continuation preserves successful batches and retries from the last committed cursor', async () => {
  const cursors = []; let fail = true
  const h = setup(async (_, args) => {
    cursors.push(args.cursor)
    if (!args.cursor) return page('first', true, { points: [point()] })
    if (fail) throw Error('offline')
    return page('last', false, { points: [point(2)] })
  })
  await assert.rejects(h.stream.load()); assert.equal(h.stream.readCursor(), 'first')
  assert.equal(h.stream.points.value[0].request_count, 10); assert.equal(h.drained.length, 0)
  assert.equal(h.stream.metricsLoading.value, false); assert.ok(h.stream.metricsError.value)
  fail = false; await h.stream.load(true)
  assert.deepEqual(cursors, ['', 'first', 'first']); assert.equal(h.stream.points.value[0].request_count, 20)
  assert.equal(h.stream.metricsError.value, ''); assert.equal(h.stream.metricsLoading.value, false); h.close()
})
test('non-advancing continuation rejects without committing the broken page or looping', async () => {
  let calls = 0
  const h = setup(async () => { calls++; return page('first', true, { points: [point(calls)] }) })
  await assert.rejects(h.stream.load()); assert.equal(calls, 2)
  assert.equal(h.stream.readCursor(), 'first'); assert.equal(h.stream.points.value[0].request_count, 10)
  assert.equal(h.drained.length, 0); h.close()
})
test('malformed batch cannot advance its cursor and a corrected retry keeps all points', async () => {
  let broken = true
  const h = setup(async () => page('next', false, { points: [point(), { ...point(2), failure_count: false }].filter((_, i) => broken || i === 0) }))
  await assert.rejects(h.stream.load()); assert.equal(h.stream.readCursor(), ''); assert.equal(h.stream.points.value.length, 0)
  broken = false; await h.stream.load(); assert.equal(h.stream.points.value[0].request_count, 10); h.close()
})
test('invalidated polling context stops continuation and cannot publish or merge its late response', async () => {
  const response = deferred(); let current = true
  const h = setup(() => response.promise), job = h.stream.load(true, { isCurrent: () => current })
  current = false; response.resolve(page('late', true, { points: [point()] })); await job
  assert.equal(h.stream.readCursor(), ''); assert.equal(h.stream.points.value.length, 0); assert.equal(h.drained.length, 0)
  assert.equal(h.stream.metricsLoading.value, false); h.close()
})
test('A-B-A reset invalidates the first A even though its ID matches again, and cannot clear new loading', async () => {
  const first = deferred(), last = deferred(); let calls = 0
  const h = setup(() => (++calls === 1 ? first.promise : last.promise))
  const a1 = h.stream.load(); h.select('2'); h.select('1'); const a2 = h.stream.load()
  first.resolve(page('obsolete', false, { points: [point()] })); await a1
  assert.equal(h.stream.readCursor(), ''); assert.equal(h.stream.metricsLoading.value, true)
  last.resolve(page('current', false, { points: [point(2)] })); await a2
  assert.equal(h.stream.readCursor(), 'current'); assert.equal(h.drained.length, 1); h.close()
})
test('dispose prevents late points, errors and final callbacks; missing ID performs no request', async () => {
  const response = deferred(); let calls = 0
  const h = setup(() => { calls++; return response.promise })
  h.select(null); await h.stream.load(); assert.equal(calls, 0)
  h.select('1'); const job = h.stream.load(); h.stream.dispose(); response.reject(Error('late'))
  await assert.rejects(job); assert.equal(h.stream.metricsError.value, ''); assert.equal(h.drained.length, 0)
  assert.equal(h.stream.metricsLoading.value, false); await h.stream.load(); assert.equal(calls, 1); h.close()
})
test('terminal callback failure retries on a later read without replaying committed windows', async () => {
  let attempts = 0
  const h = setup(async () => page('done', false, { run_status: 'completed', points: [point()] }), async () => {
    if (++attempts === 1) throw Error('final unavailable')
  })
  await assert.rejects(h.stream.load()); await h.stream.load(true)
  assert.equal(attempts, 2); assert.equal(h.stream.points.value[0].request_count, 10)
  assert.equal(h.stream.metricsError.value, ''); assert.equal(h.drained.length, 1); h.close()
})
test('metric loading ends when sampling finishes, without waiting for an unrelated final result region', async () => {
  const final = deferred()
  const h = setup(async () => page('done', false, { run_status: 'completed' }), () => final.promise)
  const job = h.stream.load(); await flush()
  assert.equal(h.stream.readCursor(), 'done'); assert.equal(h.stream.metricsLoading.value, false)
  assert.equal(h.stream.load(), job); assert.equal(h.stream.metricsLoading.value, false)
  final.reject(Error('final region failed')); await assert.rejects(job)
  assert.equal(h.stream.metricsError.value, ''); assert.equal(h.stream.metricsLoading.value, false); h.close()
})
