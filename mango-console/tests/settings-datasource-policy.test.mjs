import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/system/settings')
const runtimeRow = () => ({ group: 'example-group', connections: [0, '90071992547409931234'], budget: { concurrency: 6, connections: 12 } })
const setup = (props = {}) => harness('DatasourcePerformanceEditor', 'draft,error,modelError,runtime,budgetFields,sharedFields,save', { base, props: { modelValue: {}, loading: false, ...props } })
test('finite policy copies only registered fields and creates independent budgets/defaults', t => {
  const h = setup(); t.after(h.close); const m = h.load('datasource-policy.ts')
  const raw = { mysql: { concurrency: 4, unknown: 'omit' }, instances: [1], scopes: [2], unrelated: 'omit' }, before = structuredClone(raw)
  const first = m.createDatasourcePolicy(raw), second = m.createDatasourcePolicy({})
  assert.equal(first.version, 1); assert.equal(first.mysql.concurrency, 4); assert.equal(first.redis.concurrency, 12); assert.equal(first.elasticsearch.requests_per_second, 15)
  assert.equal('unknown' in first.mysql, false); assert.equal('instances' in first, false); assert.equal('scopes' in first, false); assert.equal('unrelated' in first, false)
  first.mysql.connections = 4; assert.equal(second.mysql.connections, 12); assert.equal(first.redis.connections, 16); assert.deepEqual(raw, before)
  assert.equal(m.createDatasourcePolicy({ mysql: { concurrency: 2, connections: 3 } }).mysql.cleanup_reserved, 1)
  assert.equal(m.createDatasourcePolicy({ mysql: { concurrency: 2, connections: 3 } }).pool_size, 2)
})
test('malformed input cannot be silently replaced with a default save and corrected props recover', async t => {
  const h = setup({ modelValue: null }); t.after(h.close); assert.ok(h.modelError.value); h.save(); assert.equal(h.events.length, 0)
  for (const value of ['invalid', [], { mysql: null }, { version: 2 }, { mysql: { concurrency: false } }]) {
    h.props.modelValue = value; await flush(); assert.ok(h.modelError.value); h.save(); assert.equal(h.events.length, 0)
  }
  h.props.modelValue = {}; await flush(); assert.equal(h.modelError.value, ''); h.save(); assert.equal(h.events.filter(e => e[0] === 'save').length, 1)
})
test('draft, submitted snapshots and external rollbacks have separate ownership', async t => {
  const source = { mysql: { concurrency: 4 } }, h = setup({ modelValue: source }); t.after(h.close)
  h.draft.mysql.concurrency = 5; assert.equal(source.mysql.concurrency, 4); h.save(); const payload = h.events[0][1]
  h.draft.mysql.concurrency = 6; assert.equal(payload.mysql.concurrency, 5)
  h.props.modelValue = payload; await flush(); assert.equal(h.draft.mysql.concurrency, 6)
  h.props.modelValue = source; await flush(); assert.equal(h.draft.mysql.concurrency, 4)
})
test('all numeric fields enforce their existing bounds and integer requirements', t => {
  const h = setup(); t.after(h.close)
  for (const field of h.sharedFields) {
    const original = h.draft[field.key]
    for (const value of [undefined, null, false, '', NaN, Infinity, field.min - 1, field.max + 1, field.min + 0.5]) { h.draft[field.key] = value; h.save(); assert.equal(h.events.length, 0); assert.ok(h.error.value) }
    h.draft[field.key] = original
  }
  for (const field of h.budgetFields) {
    const original = h.draft.mysql[field.key]
    for (const value of [undefined, null, false, '', NaN, Infinity, field.min - 1, field.max + 1, field.min + 0.5]) { h.draft.mysql[field.key] = value; h.save(); assert.equal(h.events.length, 0); assert.ok(h.error.value) }
    h.draft.mysql[field.key] = original
  }
  h.save(); assert.equal(h.events.filter(e => e[0] === 'save').length, 1)
})
test('cleanup reservation, metadata rate and connection headroom remain mandatory', t => {
  const h = setup(); t.after(h.close)
  h.draft.mysql.cleanup_reserved = h.draft.mysql.concurrency; h.save(); assert.match(h.error.value, /清理保留/)
  h.draft.mysql.cleanup_reserved = 2; h.draft.mysql.requests_per_second = 2; h.draft.mysql.metadata_per_second = 3; h.save(); assert.match(h.error.value, /元数据速率/)
  h.draft.mysql.requests_per_second = 30; h.draft.mysql.metadata_per_second = 2; h.draft.mysql.connections = h.draft.pool_size; h.save(); assert.match(h.error.value, /清理保留连接容量/)
  assert.equal(h.events.length, 0)
})
test('runtime rows preserve missing counters as zero and long/zero connection IDs without retaining arbitrary state', t => {
  const h = setup({ runtimeStatus: [{ ...runtimeRow(), secret: 'omit' }] }); t.after(h.close)
  assert.equal(h.runtime.value.error, ''); assert.deepEqual(h.runtime.value.rows[0].connections, [0, '90071992547409931234'])
  assert.equal(h.runtime.value.rows[0].counts.operation_active, 0); assert.equal('secret' in h.runtime.value.rows[0], false)
  h.props.runtimeStatus = [{ ...runtimeRow(), counts: { operation_suspect: 1, connection_suspect: 1 }, queued: 2, throttled: 3 }]
  assert.equal(h.runtime.value.rows[0].counts.operation_suspect, 1); assert.equal(h.runtime.value.rows[0].queued, 2)
})
test('malformed runtime status shows a regional error while valid policy remains repairable', t => {
  const h = setup(); t.after(h.close)
  for (const value of [{}, [runtimeRow(), runtimeRow()], [{ ...runtimeRow(), connections: [false] }], [{ ...runtimeRow(), queued: false }], [{ ...runtimeRow(), counts: { operation_active: -1 } }]]) {
    h.props.runtimeStatus = value; assert.ok(h.runtime.value.error); assert.equal(h.runtime.value.rows.length, 0)
  }
  h.save(); assert.equal(h.events.filter(e => e[0] === 'save').length, 1)
})
test('parent saving blocks submissions and datasource component compiles', async t => {
  const h = setup({ loading: true }); t.after(h.close); h.save(); assert.equal(h.events.length, 0)
  const filename = path.join(base, 'components/DatasourcePerformanceEditor.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'datasource-settings' })
  assert.deepEqual(compileTemplate({ filename, id: 'datasource-settings', source: descriptor.template.content, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ filename, id: 'datasource-settings', source: style.content, scoped: style.scoped })).errors, [])
})
