import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { ref } from 'vue'
import { parse } from '@vue/compiler-sfc'

const source = readFileSync(new URL('../src/components/business/ApiInfoRuntimeParametersModal.vue', import.meta.url), 'utf8')
const ast = ts.createSourceFile('modal.ts', parse(source).descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
const methods = ast.statements.filter(ts.isFunctionDeclaration).map(node => ts.transpileModule(node.getText(ast), {
  compilerOptions: { target: ts.ScriptTarget.ES2022 },
}).outputText).join('\n')
function setup(fetch) {
  let shown = 0
  const state = {
    rows: ref([]), modal: ref({ show() { shown++ }, close() {} }), getApiInfoExecutionParameters: fetch,
  }
  return { ...state, shown: () => shown, ...new Function(...Object.keys(state), `let pending = null, requestVersion = 0;
    ${methods};return {prepare,confirm,finish,formatVariable}`)(...Object.values(state)) }
}

test('variable labels retain the full placeholder syntax without changing cache keys', () => {
  const state = setup(async () => ({ data: { variables: [] } }))
  assert.equal(state.formatVariable('appId'), '${{appId}}')
  assert.equal(state.formatVariable('memory_access_context'), '${{memory_access_context}}')
  assert.match(source, /:title="formatVariable\(row.name\)"/)
})

test('no placeholders execute directly, without opening the modal', async () => {
  const state = setup(async () => ({ data: { variables: [] } }))
  assert.deepEqual(await state.prepare([{ id: 1 }]), {})
  assert.equal(state.shown(), 0)
})

test('single and batch execution deduplicate variables, omit blank values and reset values', async () => {
  const targets = []
  const state = setup(async target => { targets.push(target); return { data: { variables: ['token', 'item_id', 'body'] } } })
  const result = state.prepare([{ id: 1, revision_id: 7 }, { id: 2, release_id: 8 }])
  await new Promise(setImmediate)
  assert.equal(state.shown(), 1)
  assert.deepEqual(targets, [{ id: 1, revision_id: 7 }, { id: 2, release_id: 8 }])
  assert.deepEqual(state.rows.value.map(row => row.name), ['token', 'item_id', 'body'])
  state.rows.value[0].value = 'example-value'
  state.rows.value[1].value = '0'
  state.confirm()
  assert.deepEqual(await result, { token: 'example-value', item_id: '0' })
  assert.deepEqual(state.rows.value, [])
  const next = state.prepare([{ id: 1 }])
  await new Promise(setImmediate)
  assert.ok(state.rows.value.every(row => row.value === ''))
  state.finish(null)
  assert.equal(await next, null)
})

test('all rows are optional and cancellation does not provide execution parameters', async () => {
  const state = setup(async () => ({ data: { variables: ['optional'] } }))
  const result = state.prepare([{ id: 1 }])
  await new Promise(setImmediate)
  state.confirm()
  assert.deepEqual(await result, {})
  const cancelled = state.prepare([{ id: 2 }])
  await new Promise(setImmediate)
  state.finish(null)
  assert.equal(await cancelled, null)
})

test('runtime values are posted in the request body, not URL parameters', async () => {
  const source = readFileSync(new URL('../src/api/apitest/info.ts', import.meta.url), 'utf8').replace(/^import .*\n/gm, '').replace(/^export /gm, '')
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const calls = []
  const run = new Function('post', code + ';return getApiCaseInfoRun')(async request => { calls.push(request); return {} })
  await run(1, 0, { revision_id: 7 }, { token: 'example-token' })
  assert.equal(calls[0].url, '/api/info/test')
  assert.deepEqual(calls[0].data(), { id: 1, test_env: 0, revision_id: 7, runtime_parameters: { token: 'example-token' } })
})
