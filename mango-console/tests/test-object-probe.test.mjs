import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { setupTarget } from './helpers/test-object-harness.mjs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = 'src/views/config/test-object/components/TestConnectionDialog.vue'
const source = readFileSync(filename, 'utf8')
const descriptor = parse(source).descriptor
function handlers(api) {
  return setupTarget(
    'TestConnectionDialog',
    'options,address,objectId,loading,result,error,visible,open,runTest,clearResult',
    { testObjectConnection: api }
  )
}
test('page and compact dialog compile, action follows business visibility without page-level permission guards', () => {
  for (const file of [filename, 'src/views/config/test-object/index.vue']) {
    const content = readFileSync(file, 'utf8')
    const { descriptor } = parse(content)
    const script = compileScript(descriptor, { id: 'probe' })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename: file,
        id: 'probe',
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
  assert.doesNotMatch(source, /v-permission/)
  assert.match(source, /:loading="loading"/)
  assert.match(source, /@change="clearResult"/)
  const page = readFileSync('src/views/config/test-object/index.vue', 'utf8')
  assert.match(page, /label: '测试',\s*hidden: !record.network_test_addresses\?\.length/)
})

test('probe separates status explanation, full address and aligned results with spaced footer actions', () => {
  assert.match(source, /:label="option.label"/)
  assert.match(source, /class="mango-target-probe__address">\{\{ address \}\}/)
  assert.match(source, /:type="result.connected \? 'success' : 'error'"/)
  assert.match(source, /:title="result.connected \? '连接成功' : '连接失败'"/)
  assert.match(source, /grid-template-columns: 72px minmax\(0, 1fr\)/)
  assert.match(source, /<a-space class="mango-modal-dialog-footer-actions">/)
  assert.doesNotMatch(source, /<a-tag/)
})

test('tests only selected saved address and prevents duplicate requests', async () => {
  let resolve
  const calls = []
  const state = handlers((...args) => {
    calls.push(args)
    return new Promise((r) => {
      resolve = r
    })
  })
  state.open({
    id: 7,
    network_test_addresses: [
      { label: '默认地址', value: 'https://api.example.com' },
      { label: '条件值：two', value: 'https://other.example.com' },
    ],
  })
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
  state.dispose()
})

test('closing and opening a different object ignores stale result', async () => {
  let resolve
  const state = handlers(
    () =>
      new Promise((r) => {
        resolve = r
      })
  )
  state.open({ id: 7, network_test_addresses: [{ value: 'https://api.example.com' }] })
  const run = state.runTest()
  state.exposed.close()
  resolve({ data: { connected: true } })
  await run
  assert.equal(state.result.value, null)
  assert.equal(state.loading.value, false)
  state.open({
    id: 8,
    network_test_addresses: [{ label: '默认地址', value: 'https://other.example.com' }],
  })
  assert.equal(state.objectId.value, 8)
  state.dispose()
})

test('request failure clears loading and exposes retryable error', async () => {
  const state = handlers(async () => {
    throw new Error('failed')
  })
  state.open({ id: 7, network_test_addresses: [{ value: 'https://api.example.com' }] })
  await state.runTest()
  assert.equal(state.loading.value, false)
  assert.match(state.error.value, /稍后重试/)
  assert.equal(state.result.value, null)
  state.dispose()
})
