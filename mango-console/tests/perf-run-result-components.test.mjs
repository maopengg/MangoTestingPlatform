import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { renderToString } from '@vue/server-renderer'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const base = path.resolve('src/views/perf/run/details'), cache = new Map()
const transpile = source => ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
function evaluate(source, file) {
  const exports = {}
  new Function('exports', 'require', transpile(source))(exports, id => {
    if (id === 'vue') return vue
    if (id.startsWith('.')) return load(path.resolve(path.dirname(file), id) + '.ts')
    { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error('Unexpected dependency: ' + id) }
  })
  return exports
}
function load(file) {
  if (!cache.has(file)) cache.set(file, evaluate(readFileSync(file, 'utf8'), file))
  return cache.get(file)
}
const presentation = load(path.join(base, 'presentation.ts'))
const request = (values = {}) => ({ id: 1, step_key: '', request_name: 'Example request', method: 'GET', url_path: '/example', request_count: 10, failure_count: 2, avg_ms: '10.125', p50_ms: 9, p95_ms: 12, p99_ms: 13, rps: '3.1250', max_rps: 5, ...values })
const metric = (values = {}) => ({ metric: 'avg_ms', current: 10, baseline: 12, delta: -2, delta_percent: -16.667, ...values })
const gate = (values = {}) => ({ gate_key: 'metric_coverage', name: '指标完整率', status: 'passed', actual_value: 0.95, required_value: 0.95, ...values })

async function render(name, props) {
  const filename = path.join(base, 'components', name + '.vue')
  const { descriptor } = parse(readFileSync(filename, 'utf8'))
  const code = compileScript(descriptor, { id: name, inlineTemplate: true }).content
  const component = evaluate(code, filename).default
  const app = vue.createSSRApp(component, props), tables = []
  app.component('a-table', vue.defineComponent({
    props: ['data', 'loading', 'rowKey', 'columns', 'scroll', 'pagination'],
    setup(props, { slots }) {
      tables.push(props); vue.provide('table-rows', props)
      return () => vue.h('div', [slots.columns?.(), !props.data.length && slots.empty?.()])
    },
  }))
  app.component('a-table-column', vue.defineComponent({
    setup(_, { slots }) { const table = vue.inject('table-rows'); return () => vue.h('section', table.data.map(record => slots.cell?.({ record }))) },
  }))
  app.component('a-tag', vue.defineComponent({ setup(_, { slots }) { return () => vue.h('span', slots.default?.()) } }))
  return { html: await renderToString(app), tables }
}

test('number formatting keeps zero and Decimal strings and rejects absent or malformed metrics', () => {
  assert.equal(presentation.formatRunNumber(0), '0')
  assert.equal(presentation.formatRunNumber('1234.125', 2), '1,234.13')
  for (const value of [null, undefined, '', ' ', false, true, {}, [], NaN, Infinity, 'bad']) {
    assert.equal(presentation.formatRunNumber(value), '-')
  }
})
test('request error rate preserves zero and supports ORM numeric strings without mutating the row', () => {
  const row = request({ request_count: '20', failure_count: '3' }), before = structuredClone(row)
  assert.equal(presentation.requestErrorRate(row), '15.00%'); assert.deepEqual(row, before)
  assert.equal(presentation.requestErrorRate(request({ request_count: 0, failure_count: 0 })), '0.00%')
  assert.equal(presentation.requestErrorRate(request({ request_count: null })), '-')
  assert.equal(presentation.requestErrorRate(request({ failure_count: 'bad' })), '-')
})
test('comparison formatting preserves null, zero, signed difference and metric units', () => {
  assert.equal(presentation.comparisonValue('avg_ms', '10.125'), '10.13 ms')
  assert.equal(presentation.comparisonValue('rps', '3.125'), '3.13')
  assert.equal(presentation.comparisonValue('request_count', 0), '0')
  assert.equal(presentation.comparisonValue('avg_ms', null), '-')
  assert.equal(presentation.comparisonDelta(metric()), '-2 ms')
  assert.equal(presentation.comparisonDelta(metric({ metric: 'rps', delta: 2.5 })), '+2.5')
  assert.equal(presentation.comparisonDelta(metric({ delta: null })), '-')
  assert.equal(presentation.comparisonPercent(null), '-')
  assert.equal(presentation.comparisonPercent(0), '0.00%')
})
test('comparison tone retains lower-latency/failure and higher-throughput semantics, unknown values stay neutral', () => {
  for (const key of ['failure_count', 'avg_ms', 'p95_ms', 'p99_ms']) {
    assert.equal(presentation.comparisonTone(metric({ metric: key, delta: -1 })), 'mango-perf-success-text')
    assert.equal(presentation.comparisonTone(metric({ metric: key, delta: 1 })), 'mango-perf-danger-text')
  }
  assert.equal(presentation.comparisonTone(metric({ metric: 'rps', delta: 1 })), 'mango-perf-success-text')
  for (const delta of [0, null, 'bad']) assert.equal(presentation.comparisonTone(metric({ delta })), '')
})
test('validity values use backend gate-specific units and preserve exact zero requirements', () => {
  for (const [key, value, actual, required] of [
    ['generator_cpu', 0, '0%', '≤ 0%'], ['clock_offset', '1000', '1,000 ms', '≤ 1,000 ms'],
    ['metric_coverage', 0.95, '95.00%', '≥ 95.00%'], ['dropped_iterations', 0.01, '1.00%', '≤ 1.00%'],
    ['node_completion', 2, '2', '2'], ['load_achievement', 0, '0', '0'],
  ]) {
    const row = gate({ gate_key: key, actual_value: value, required_value: value })
    assert.equal(presentation.validityActual(row), actual); assert.equal(presentation.validityRequired(row), required)
  }
})
test('missing gate values never fabricate passed zero or malformed units', () => {
  for (const gate_key of ['generator_cpu', 'clock_offset', 'metric_coverage', 'dropped_iterations', 'node_completion']) {
    assert.equal(presentation.validityActual(gate({ gate_key, actual_value: null })), '-')
    assert.equal(presentation.validityRequired(gate({ gate_key, required_value: 'bad' })), '-')
  }
})
test('request component renders rows and long text tooltip without mutating props; forwards loading and stable ID', async () => {
  const rows = [request({ request_name: 'Very long example name', url_path: '/example/long/path' })], before = structuredClone(rows)
  const { html, tables } = await render('RunRequestTable', { rows, loading: true })
  assert.match(html, /title="Very long example name"/); assert.match(html, /title="\/example\/long\/path"/)
  assert.match(html, /20.00%/); assert.match(html, /3.13 \/ 5/)
  assert.equal(tables[0].loading, true); assert.equal(tables[0].rowKey, 'id'); assert.deepEqual(rows, before)
})
test('comparison component renders translated metric, neutral missing values and signed deltas', async () => {
  const rows = [metric(), metric({ metric: 'rps', current: null, baseline: 0, delta: null, delta_percent: null })], before = structuredClone(rows)
  const { html, tables } = await render('RunComparisonTable', { rows, loading: false })
  assert.match(html, /平均响应时间/); assert.match(html, /-2 ms/); assert.doesNotMatch(html, /NaN|undefined/)
  assert.equal(tables[0].rowKey, 'metric'); assert.deepEqual(rows, before)
})
test('validity component renders actual backend records without nonexistent ID or English known status', async () => {
  const rows = [gate(), gate({ gate_key: 'generator_cpu', name: '发压端 CPU', status: 'failed', actual_value: 99, required_value: 90 })], before = structuredClone(rows)
  const { html } = await render('RunValidityGrid', { rows })
  assert.match(html, /通过/); assert.match(html, /失败/); assert.match(html, /95.00%/); assert.match(html, /≤ 90%/)
  assert.deepEqual(rows, before)
})
for (const [name, text] of [['RunRequestTable', '暂无请求统计'], ['RunComparisonTable', '暂无对比指标'], ['RunValidityGrid', '暂无有效性门禁结果']]) {
  test(`${name} renders the shared empty-state convention`, async () => {
    const { html } = await render(name, { rows: [], loading: false }); assert.match(html, /mango-empty-state/); assert.ok(html.includes(text))
  })
  test(`${name} actual SFC script/template compiles`, () => {
    const filename = path.join(base, 'components', name + '.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: name })
    const template = compileTemplate({ source: descriptor.template.content, filename, id: name, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
  })
}
