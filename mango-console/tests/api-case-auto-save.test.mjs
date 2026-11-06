import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { reactive, watch, effectScope } from 'vue'

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8')
function compile(source, names = [], values = [], result) {
  const plain = source.replace(/^import .*from .*$/gm, '').replace(/export /g, '')
  const js = ts.transpileModule(plain, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  return new Function(...names, `${js};return ${result}`)(...values)
}
const createChangeAwareSave = compile(read('../src/utils/change-aware-save.ts'), [], [], 'createChangeAwareSave')
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b }); return { promise, resolve, reject } }

test('unchanged blur, nested SQL and JSON formatting do not send requests', async () => {
  const writes = [], guard = createChangeAwareSave(async p => { writes.push(p); return { msg: 'saved' } })
  const sql = [{ key: 'result', value: 'SELECT 1', test_envs: [0], datasource_alias: 7 }]
  guard.seed({ id: 1, front_sql: sql, ass_json_all: '{\n "code": 0\n}', front_func: null })
  assert.equal(await guard.save({ id: 1, front_sql: structuredClone(sql) }), null)
  assert.equal(await guard.save({ id: 1, ass_json_all: { code: 0 }, front_func: '' }), null)
  assert.equal(writes.length, 0)
  await guard.save({ id: 1, front_sql: [{ ...sql[0], value: 'SELECT 2' }] })
  assert.equal(writes.length, 1)
})

test('editing then restoring a value needs no save; array order and SQL whitespace remain significant', async () => {
  const writes = [], guard = createChangeAwareSave(async p => writes.push(p))
  guard.seed({ id: 1, front_sql: ['SELECT 1'], headers: [1, 2] })
  const local = ['SELECT 2']; local[0] = 'SELECT 1'
  await guard.save({ id: 1, front_sql: local })
  assert.equal(writes.length, 0)
  await guard.save({ id: 1, front_sql: ['SELECT  1'], headers: [2, 1] })
  assert.equal(writes.length, 1)
})

test('only changed fields are sent and successful saves become the next baseline', async () => {
  const writes = [], guard = createChangeAwareSave(async p => { writes.push(p); return true })
  guard.seed({ id: 1, front_sql: [], posterior_sql: [], name: 'case' })
  await guard.save({ id: 1, front_sql: [], posterior_sql: [], name: 'renamed' })
  assert.deepEqual(writes, [{ id: 1, name: 'renamed' }])
  assert.equal(await guard.save({ id: 1, name: 'renamed' }), null)
})

test('concurrent duplicate events share one write; subsequent changes are serialized and frozen', async () => {
  const first = deferred(), writes = []
  const guard = createChangeAwareSave(async p => { writes.push(p); if (writes.length === 1) await first.promise; return true })
  guard.seed({ id: 1, values: [0] })
  const a = guard.save({ id: 1, values: [1] })
  const b = guard.save({ id: 1, values: [1] })
  const values = [2], c = guard.save({ id: 1, values })
  values[0] = 9
  await Promise.resolve()
  assert.equal(writes.length, 1)
  first.resolve(); await Promise.all([a, b, c])
  assert.deepEqual(writes.map(x => x.values), [[1], [2]])
})

test('failed writes keep the original baseline and retry on the next blur', async () => {
  let calls = 0
  const guard = createChangeAwareSave(async () => { if (++calls === 1) throw Error('offline'); return true })
  guard.seed({ id: 1, front_func: 'old' })
  await assert.rejects(guard.save({ id: 1, front_func: 'new' }), /offline/)
  await guard.save({ id: 1, front_func: 'new' })
  assert.equal(calls, 2)
  assert.equal(await guard.save({ id: 1, front_func: 'new' }), null)
})

test('records and refreshed versions are isolated; late responses cannot replace a fresh baseline', async () => {
  const first = deferred(), writes = []
  const guard = createChangeAwareSave(async p => { writes.push(p); if (writes.length === 1) await first.promise; return true })
  guard.seed({ id: 1, value: 'old' }); guard.seed({ id: 2, value: 'other' })
  const a = guard.save({ id: 1, value: 'pending' })
  const queued = guard.save({ id: 1, value: 'stale' })
  await Promise.resolve()
  guard.seed({ id: 1, value: 'fresh version' })
  first.resolve(); await Promise.all([a, queued])
  await guard.save({ id: 1, value: 'fresh version' })
  await guard.save({ id: 2, value: 'other' })
  assert.equal(writes.length, 1)
})

test('page provides one shared saver, seeds loaded data and does not re-seed on model edits', async () => {
  const writes = [], provided = new Map()
  const hooks = compile(read('../src/views/apitest/case/details/composables/useApiCaseAutoSave.ts'),
    ['watch', 'provide', 'inject', 'createChangeAwareSave', 'putApiCase', 'putApiCaseDetailedParameter'],
    [watch, (k, v) => provided.set(k, v), (k, fallback) => provided.get(k) || fallback, createChangeAwareSave,
      async p => { writes.push(p); return true }, async p => { writes.push(p); return true }],
    '{useApiCaseAutoSave,useApiCaseParameterSave}')
  const state = reactive({ record: { id: 1, front_sql: [] }, scenarios: [{ id: 2, front_sql: [] }] })
  const scope = effectScope()
  const page = scope.run(() => hooks.useApiCaseAutoSave(() => state.record, () => state.scenarios))
  const childSave = hooks.useApiCaseParameterSave()
  await page.saveCase({ id: 1, front_sql: [] }); await childSave({ id: 2, front_sql: [] })
  assert.equal(writes.length, 0)
  state.scenarios[0].front_sql.push({ value: 'SELECT 1' })
  await childSave({ id: 2, front_sql: state.scenarios[0].front_sql })
  await page.saveParameter({ id: 2, front_sql: state.scenarios[0].front_sql })
  assert.equal(writes.length, 1)
  scope.stop()
})

test('all scenario autosave panels use the shared guard without focus snapshots hiding retries', () => {
  for (const name of ['ApiCaseScenarioFrontPanel', 'ApiCasePosteriorPanel', 'ApiCaseRequestPanel']) {
    const source = read(`../src/views/apitest/case/details/components/${name}.vue`)
    assert.match(source, /useApiCaseParameterSave\(\)/)
    assert.doesNotMatch(source, /codeSnapshot/)
  }
  const page = read('../src/views/apitest/case/details/index.vue')
  assert.match(page, /return saveParameter\(payload\)/)
  assert.match(page, /saveCase\(\{/)
})
