import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { ref } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = 'src/views/config/test-object/components/TestConnectionDialog.vue'
const source = readFileSync(filename, 'utf8')
const descriptor = parse(source).descriptor
const ast = ts.createSourceFile('probe.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)

function handlers(api) {
  const state = {
    dialog: ref({ show() {}, close() {}, setConfirmLoading() {} }),
    options: ref([]), address: ref(''), objectId: ref(0), loading: ref(false), result: ref(null), error: ref(''),
    testObjectConnection: api,
  }
  const functions = ast.statements.filter(node => ts.isFunctionDeclaration(node))
  const code = ts.transpileModule(functions.map(node => node.getText(ast)).join('\n'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
  return { ...state, ...new Function(...Object.keys(state),
    `let requestVersion = 0; ${code}; return {open, close, runTest}`)(...Object.values(state)) }
}

test('page and compact dialog compile, action is permission-gated and excludes non-network targets', () => {
  for (const file of [filename, 'src/views/config/test-object/index.vue']) {
    const content = readFileSync(file, 'utf8')
    const { descriptor } = parse(content)
    const script = compileScript(descriptor, { id: 'probe' })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename: file,
      id: 'probe', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  }
  assert.match(source, /v-permission="'config.test_object:change'"/)
  assert.match(source, /:loading="loading"/)
  assert.match(source, /@change="result = null; error = ''"/)
  const page = readFileSync('src/views/config/test-object/index.vue', 'utf8')
  assert.match(page, /permission: 'config.test_object:change', label: '测试', hidden: !record.network_test_addresses\?\.length/)
})

test('tests only selected saved address and prevents duplicate requests', async () => {
  let resolve
  const calls = []
  const state = handlers((...args) => { calls.push(args); return new Promise(r => { resolve = r }) })
  state.open({ id: 7, network_test_addresses: [{ label: '默认地址', value: 'https://api.example.com' },
    { label: '条件值：two', value: 'https://other.example.com' }] })
  assert.equal(calls.length, 0)
  state.address.value = 'https://other.example.com'
  const run = state.runTest()
  assert.equal(state.loading.value, true)
  await state.runTest()
  assert.deepEqual(calls, [[7, 'https://other.example.com']])
  resolve({ data: { connected: true, message: 'ok' } })
  await run
  assert.equal(state.result.value.connected, true)
  assert.equal(state.loading.value, false)
})

test('closing and opening a different object ignores stale result', async () => {
  let resolve
  const state = handlers(() => new Promise(r => { resolve = r }))
  state.open({ id: 7, network_test_addresses: [{ value: 'https://api.example.com' }] })
  const run = state.runTest()
  state.close()
  state.open({ id: 8, network_test_addresses: [{ value: 'https://other.example.com' }] })
  resolve({ data: { connected: true } })
  await run
  assert.equal(state.result.value, null)
  assert.equal(state.loading.value, false)
  assert.equal(state.objectId.value, 8)
})

test('request failure clears loading and exposes retryable error', async () => {
  const state = handlers(async () => { throw new Error('failed') })
  state.open({ id: 7, network_test_addresses: [{ value: 'https://api.example.com' }] })
  await state.runTest()
  assert.equal(state.loading.value, false)
  assert.match(state.error.value, /稍后重试/)
  assert.equal(state.result.value, null)
})
