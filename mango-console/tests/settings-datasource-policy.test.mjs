import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { harness, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/system/settings')
const setup = props => harness('DatasourcePerformanceEditor', 'draft,error,modelError,runtime,budgetFields,sharedFields,save',
  { base, props: { modelValue: {}, loading: false, ...props } })

test('v2 only exposes connection management and strict cleanup defaults', t => {
  const h = setup(); t.after(h.close)
  const m = h.load('datasource-policy.ts')
  const first = m.createDatasourcePolicy({}), second = m.createDatasourcePolicy({})
  assert.equal(first.version, 2)
  assert.deepEqual(first.mysql, { connections: 20 })
  assert.deepEqual(first.redis, { connections: 16 })
  assert.deepEqual(first.elasticsearch, { connections: 12 })
  assert.equal(first.pool_size, 4); assert.equal(first.cleanup_consumer_threads, 2)
  first.mysql.connections = 30; assert.equal(second.mysql.connections, 20)
  assert.deepEqual(h.budgetFields.map(field => field.key), ['connections'])
  assert.deepEqual(h.sharedFields.map(field => field.key), [
    'cleanup_consumer_threads', 'pool_size', 'pool_idle_seconds', 'max_local_pools', 'cleanup_completion_seconds'])
})
test('retired fields and malformed policies cannot be silently resaved', async t => {
  const h = setup(); t.after(h.close)
  for (const value of [null, 'invalid', [], { version: 1 }, { max_waiters: 100 },
    { mysql: { concurrency: 10 } }, { mysql: { requests_per_second: 60 } }]) {
    h.props.modelValue = value; await flush(); assert.ok(h.modelError.value)
    h.save(); assert.equal(h.events.length, 0)
  }
  h.props.modelValue = {}; await flush(); h.save()
  assert.equal(h.events.filter(([name]) => name === 'save').length, 1)
})
test('partial datasource objects keep per-type defaults and preserve explicit saved values', t => {
  const h = setup(); t.after(h.close)
  const m = h.load('datasource-policy.ts')
  const expected = m.createDatasourcePolicy({})
  for (const kind of ['mysql', 'redis', 'elasticsearch']) {
    const source = { version: 2, [kind]: {} }
    assert.deepEqual(m.createDatasourcePolicy(source), expected)
    assert.deepEqual(source[kind], {})
    assert.equal(m.createDatasourcePolicy({ [kind]: { connections: 9 } })[kind].connections, 9)
  }
  const editor = setup({ modelValue: { version: 2, mysql: {}, redis: {}, elasticsearch: {} } })
  t.after(editor.close)
  editor.save()
  assert.deepEqual(editor.events.find(([name]) => name === 'update:modelValue')[1], expected)
})
test('saving connection limits does not mutate parent values or invent operation quotas', t => {
  const source = { version: 2, mysql: { connections: 12 }, pool_size: 2 }
  const h = setup({ modelValue: source }); t.after(h.close)
  h.draft.mysql.connections = 20; h.save()
  const payload = h.events.find(([name]) => name === 'update:modelValue')[1]
  assert.equal(source.mysql.connections, 12)
  assert.deepEqual(payload.mysql, { connections: 20 })
  assert.equal('max_waiters' in payload, false)
  assert.equal('transaction_statement_budget' in payload, false)
})
test('cleanup cannot be disabled and reserved physical capacity is validated', t => {
  const h = setup(); t.after(h.close)
  h.draft.cleanup_consumer_threads = 0; h.save(); assert.ok(h.error.value)
  h.draft.cleanup_consumer_threads = 2; h.draft.mysql.connections = h.draft.pool_size
  h.save(); assert.match(h.error.value, /清理保留连接容量/)
  assert.equal(h.events.length, 0)
})
test('runtime shows real connection counts and waiting signal rather than SQL quotas', t => {
  const h = setup({ runtimeStatus: [{ group: 'example-group', connections: [1],
    budget: { connections: 20 }, counts: { connection_active: 6, connection_suspect: 1 }, connection_waiting: true }] })
  t.after(h.close)
  assert.equal(h.runtime.value.rows[0].counts.connection_active, 6)
  assert.equal(h.runtime.value.rows[0].connection_waiting, true)
  assert.equal('operation_active' in h.runtime.value.rows[0].counts, false)
})
