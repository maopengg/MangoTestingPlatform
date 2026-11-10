import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/run/details')
// Read-handler tests do not mount the page; cleanup still uses its event surface.
globalThis.window = new EventTarget()
globalThis.document = Object.assign(new EventTarget(), { visibilityState: 'visible' })
const envelope = data => ({ code: 200, data })
const overview = (patch = {}) => ({ id: 1, name: 'Example run', status: 'running', verdict: 'not_evaluated', engine: 'k6', scenario_id: null, summary: {}, test_env: 0, ...patch })
const point = (node_id = 1, patch = {}) => ({
  node_id, window_start: '2026-11-07T10:00:00', window_seconds: 1, request_count: 10, failure_count: 1,
  iteration_count: 2, dropped_count: 0, response_time_sum_ms: 100, bytes_sent: 10, bytes_received: 20,
  connection_count: 2, connect_error_count: 0, ...patch,
})
const metricPage = points => envelope({ run_id: 1, cursor: 'opaque-cursor', has_more: false, run_status: 'running', verdict: 'not_evaluated', points })
function setup(api = {}) {
  const route = { path: '/perf/run/details', fullPath: '/perf/run/details?id=1', query: { id: '1' } }
  const h = harness('index', 'overviewRecord,overview,requests,points,sampledSummary,loadOverview,loadMetrics,readCursor:metricStream.readCursor', {
    base, modules: {
      'vue-router': { useRoute: () => route, useRouter: () => ({ push() {}, back() {} }) },
      '@/store/modules/user': { default: () => ({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }) },
      '@/api/perf': { getPerfRunOverview: async () => envelope(overview()), getPerfRunMetrics: async () => metricPage([]), unsubscribePerfRun: async () => envelope({}), ...api },
      echarts: {}, '@/utils/chartDensity': { makeChartDensityAware: value => value },
      '@/hooks/use-page-polling': { usePagePolling: () => ({ start() {}, stop() {}, pause() {}, resume() {}, isAvailable: () => true }) },
    },
  })
  return { ...h, records: h.load('records.ts'), metrics: h.load('metrics.ts') }
}

test('overview starts as null and actual main reader stores a finite detached DTO, including zero and null', async () => {
  const fixture = overview({ requested_node_count: 0, summary: { request_count: 0, avg_ms: '1.250', timing_breakdown: { connect_ms: 0 }, ignored: 'extra' }, injected: 'extra' })
  const h = setup({ getPerfRunOverview: async () => envelope(fixture) })
  assert.equal(h.overviewRecord.value, null); assert.equal(h.overview.value.status, '')
  await h.loadOverview(); assert.equal(h.overviewRecord.value.scenario_id, null); assert.equal(h.overview.value.test_env, 0)
  assert.equal(h.overview.value.requested_node_count, 0); assert.equal(h.overview.value.summary.avg_ms, 1.25)
  assert.equal('injected' in h.overview.value, false); assert.equal('ignored' in h.overview.value.summary, false)
  fixture.summary.avg_ms = 99; assert.equal(h.overview.value.summary.avg_ms, 1.25); h.close()
})
test('wrong run ID, failed code and malformed summary cannot replace previous main snapshot', async () => {
  let fixture = envelope(overview()), h = setup({ getPerfRunOverview: async () => fixture }); await h.loadOverview()
  const saved = h.overviewRecord.value
  for (const value of [{ code: 400, data: overview() }, envelope(overview({ id: 2 })), envelope(overview({ summary: [] })), envelope(overview({ summary: { avg_ms: false } }))]) {
    fixture = value; await assert.rejects(h.loadOverview()); assert.equal(h.overviewRecord.value, saved)
  }
  h.close()
})
test('request DTO preserves Decimal strings as numbers and whitelists known summary fields', () => {
  const h = setup(), rows = h.records.readRunRequests(envelope([{ id: 1, step_key: '', request_name: 'Example', method: 'GET', url_path: '/example', request_count: 0, failure_count: 0, avg_ms: '2.125', p50_ms: '0', p95_ms: null, p99_ms: '3', rps: '4.2500', max_rps: 5, bytes_received: 0, min_ms: 0, extra: 'drop' }]))
  assert.equal(rows[0].avg_ms, 2.125); assert.equal(rows[0].min_ms, 0); assert.equal(rows[0].p95_ms, null)
  assert.equal(rows[0].request_count, 0); assert.equal('extra' in rows[0], false); h.close()
})
test('comparison unavailable DTO clears optional baseline fields and keeps null versus zero', () => {
  const h = setup()
  assert.deepEqual(h.records.readRunComparison(envelope({ available: false, metrics: [] })), { available: false, same_snapshot: null, metrics: [] })
  const result = h.records.readRunComparison(envelope({ available: true, same_snapshot: false, metrics: [{ metric: 'rps', current: '0', baseline: 1, delta: '-1', delta_percent: null }] }))
  assert.equal(result.metrics[0].current, 0); assert.equal(result.metrics[0].delta, -1); assert.equal(result.same_snapshot, false)
  assert.throws(() => h.records.readRunComparison(envelope({ available: 'false', metrics: [] }))); h.close()
})
test('actual backend stage, gate and threshold JSON shapes require no fictional IDs and preserve booleans', () => {
  const h = setup()
  const stages = h.records.readRunStages(envelope([{ stage_key: 'stage-1', stage_name: 'Example', duration_seconds: 0, target_load: { users: null, rate: 10 }, actual_load: { users: 0 }, rps: '0.125', p95_ms: 0, failure_count: 0 }]))
  assert.equal(stages[0].target_load.users, null); assert.equal(stages[0].duration_seconds, 0)
  const gates = h.records.readRunValidity(envelope([{ gate_key: 'clock_offset', name: 'Clock', status: 'passed', actual_value: 0, required_value: 1000, detail: {} }]))
  assert.equal(gates[0].gate_key, 'clock_offset'); assert.equal('id' in gates[0], false)
  const rules = h.records.readRunThresholds(envelope([{ metric: 'error_rate', operator: '<=', actual_value: 0, threshold_value: 0, passed: false }]))
  assert.equal(rules[0].passed, false); assert.equal(rules[0].threshold_value, 0); h.close()
})
test('node capture and error DTOs strip internal data and preserve missing values and response code zero', () => {
  const h = setup()
  const nodes = h.records.readRunNodes(envelope([{ id: 1, shard_index: 0, status: 'running', engine_version: '', capture: { status: 'uploaded', bytes: 0, path: 'internal' }, lease_token_hash: 'must-not-copy' }]))
  assert.equal(nodes[0].capture.bytes, 0); assert.equal(nodes[0].last_metric_at, null)
  assert.equal('path' in nodes[0].capture, false); assert.equal('lease_token_hash' in nodes[0], false)
  const errors = h.records.readRunErrors(envelope([{ id: 2, error_type: 'Example', count: 0, node_count: 0, message_template: 'Example', samples: [{ response_status: 0, response_excerpt: null, extra: 'drop' }] }]))
  assert.deepEqual(errors[0].samples, [{ response_status: 0, response_excerpt: null }]); h.close()
})
test('all row readers reject non-array or malformed records instead of publishing false empty success', () => {
  const h = setup()
  for (const key of ['readRunRequests', 'readRunStages', 'readRunNodes', 'readRunValidity', 'readRunThresholds', 'readRunErrors']) {
    for (const data of [null, {}, [null], [{}]]) assert.throws(() => h.records[key](envelope(data)))
    assert.throws(() => h.records[key]({ code: 403, data: [] })); assert.deepEqual(h.records[key](envelope([])), [])
  }
  h.close()
})
test('metric DTO preserves explicit zero, absent resource measurements and opaque paging protocol', () => {
  const h = setup(), result = h.records.readRunMetricPage(metricPage([point(1, { timing_breakdown: { connect_ms: 0, unknown: 99 }, generator_metrics: { cpu_percent: 0 } })]), '1')
  assert.equal(result.cursor, 'opaque-cursor'); assert.equal(result.has_more, false)
  assert.deepEqual(result.points[0].generator_metrics, { cpu_percent: 0, memory_bytes: null, event_loop_lag_ms: null })
  assert.deepEqual(result.points[0].timing_breakdown, { connect_ms: 0 }); h.close()
})
test('invalid metric batch cannot advance cursor or merge a partial batch in the actual main handler', async () => {
  let fixture = metricPage([point()]), h = setup({ getPerfRunMetrics: async () => fixture })
  await h.loadOverview(); await h.loadMetrics()
  const previous = h.points.value, cursor = h.readCursor()
  fixture = metricPage([point(2), point(3, { request_count: false })])
  await assert.rejects(h.loadMetrics()); assert.equal(h.points.value, previous); assert.equal(h.readCursor(), cursor)
  fixture = { ...metricPage([]), data: { ...metricPage([]).data, run_id: 2 } }
  await assert.rejects(h.loadMetrics()); assert.equal(h.points.value, previous); await flush(); h.close()
})
test('metric decoder rejects zero windows, non-finite values and non-boolean paging flags', () => {
  const h = setup()
  for (const patch of [{ window_seconds: 0 }, { request_count: Infinity }, { node_id: -1 }, { timing_breakdown: { connect_ms: 'bad' } }]) {
    assert.throws(() => h.records.readRunMetricPage(metricPage([point(1, patch)]), '1'))
  }
  const fixture = metricPage([]); fixture.data.has_more = 'false'; assert.throws(() => h.records.readRunMetricPage(fixture, '1')); h.close()
})
test('window merge deduplicates node/window across batches, sums totals and detaches all inputs', () => {
  const h = setup(), raw = h.records.readRunMetricPage(metricPage([point(1), point(2, { request_count: 20 })]), '1').points
  const before = structuredClone(raw), first = h.metrics.mergeRunMetricPoints([], raw), snapshot = structuredClone(first)
  const merged = h.metrics.mergeRunMetricPoints(first, raw)
  assert.equal(merged.length, 1); assert.equal(merged[0].request_count, 30); assert.equal(merged[0]._nodes.size, 2)
  assert.deepEqual(raw, before); assert.deepEqual(first, snapshot)
  merged[0]._nodes.add(99); assert.equal(first[0]._nodes.has(99), false); h.close()
})
test('missing timings are excluded from each field denominator, including initial missing node and zero measurements', () => {
  const h = setup(), decode = points => h.records.readRunMetricPage(metricPage(points), '1').points
  const first = h.metrics.mergeRunMetricPoints([], decode([point(1, { request_count: 100 })]))
  const merged = h.metrics.mergeRunMetricPoints(first, decode([point(2, { request_count: 10, timing_breakdown: { connect_ms: 10, dns_ms: 0 } }), point(3, { request_count: 30, timing_breakdown: { connect_ms: 20 } })]))
  assert.equal(merged[0].timing_breakdown.connect_ms, 17.5); assert.equal(merged[0].timing_breakdown.dns_ms, 0)
  const summary = h.metrics.summarizeRunMetrics(merged)
  assert.equal(summary.timing_breakdown.connect_ms, 17.5); assert.equal(summary.timing_breakdown.dns_ms, 0)
  assert.equal(summary.timing_breakdown.tls_ms, undefined); h.close()
})
test('resource extrema and memory sums preserve uncollected fields while accepting measured zero', () => {
  const h = setup(), decode = points => h.records.readRunMetricPage(metricPage(points), '1').points
  const empty = h.metrics.mergeRunMetricPoints([], decode([point(1), point(2)]))
  assert.equal(empty[0].generator_metrics.cpu_percent, null); assert.equal(empty[0].generator_metrics.memory_bytes, null)
  const merged = h.metrics.mergeRunMetricPoints(empty, decode([point(3, { generator_metrics: { cpu_percent: 0, memory_bytes: 0, event_loop_lag_ms: 0 } })]))
  assert.deepEqual(merged[0].generator_metrics, { cpu_percent: 0, memory_bytes: 0, event_loop_lag_ms: 0 })
  assert.equal(h.metrics.summarizeRunMetrics(merged).peak_generator_cpu_percent, 0); h.close()
})
test('multiple windows preserve sorting, bounded 600-window history and weighted sample summaries', () => {
  const h = setup(), decode = points => h.records.readRunMetricPage(metricPage(points), '1').points
  const merged = h.metrics.mergeRunMetricPoints([], decode([
    point(1, { window_start: '2026-11-07T10:00:02', request_count: 20, response_time_sum_ms: 400, timing_breakdown: { connect_ms: 20 } }),
    point(1, { window_start: '2026-11-07T10:00:01', request_count: 10, response_time_sum_ms: 100, timing_breakdown: { connect_ms: 10 } }),
  ]))
  assert.equal(merged[0].window_start, '2026-11-07T10:00:01')
  const summary = h.metrics.summarizeRunMetrics(merged)
  assert.equal(summary.request_count, 30); assert.equal(summary.avg_ms, 500 / 30); assert.equal(summary.rps, 15)
  assert.equal(summary.timing_breakdown.connect_ms, 500 / 30); assert.equal(summary.p95_ms, undefined)
  assert.deepEqual(h.metrics.summarizeRunMetrics([]), {})
  const many = h.metrics.mergeRunMetricPoints([], decode(Array.from({ length: 601 }, (_, n) => point(1, { window_start: String(n).padStart(4, '0') }))))
  assert.equal(many.length, 600); assert.equal(many[0].window_start, '0001'); h.close()
})
test('main SFC compiles after integration of finite response and metric layers', () => {
  const filename = path.join(base, 'index.vue'), { descriptor } = parse(readFileSync(filename, 'utf8'))
  const script = compileScript(descriptor, { id: 'run60' }), template = compileTemplate({ source: descriptor.template.content, filename, id: 'run60', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
})
