import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { createPinia, defineStore, setActivePinia } from 'pinia'
import ts from 'typescript'

const source = readFileSync(new URL('../../src/store/modules/platform-branding.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
})

function harness(get) {
  const exports = {}
  new Function('require', 'exports', outputText)(name => name === 'pinia' ? { defineStore } : { get }, exports)
  setActivePinia(createPinia())
  return exports.default()
}

test('platform names have the required Chinese and English defaults', () => {
  const store = harness(async () => {})
  assert.equal(store.projectName, '芒果测试平台')
  assert.equal(store.englishName, 'mango-test-platform')
})

test('public config updates both names and trims surrounding whitespace', async () => {
  const store = harness(async options => {
    assert.equal(options.url, '/user/registration-config')
    return { data: { platform_name: ' 演示平台 ', platform_name_en: ' ExamplePlatform ' } }
  })
  await store.loadPublicConfig()
  assert.equal(store.projectName, '演示平台')
  assert.equal(store.englishName, 'ExamplePlatform')
  assert.equal(store.loading, false)
})

test('concurrent login, layout and app initialization share a single request', async () => {
  let resolve, calls = 0
  const store = harness(() => { calls++; return new Promise(done => { resolve = done }) })
  const first = store.loadPublicConfig()
  const second = store.loadPublicConfig()
  assert.equal(store.loading, true)
  assert.equal(calls, 1)
  resolve({ data: { platform_name: '演示平台' } })
  await Promise.all([first, second])
  assert.equal(store.projectName, '演示平台')
  assert.equal(store.loading, false)
})

test('failed requests retain defaults and allow a later retry', async () => {
  let fail = true
  const store = harness(async () => {
    if (fail) throw new Error('offline')
    return { data: { platform_name: '演示平台' } }
  })
  await assert.rejects(store.loadPublicConfig())
  assert.equal(store.projectName, '芒果测试平台')
  assert.equal(store.loading, false)
  fail = false
  await store.loadPublicConfig()
  assert.equal(store.projectName, '演示平台')
})

test('saving one name updates it without replacing the other, and empty values are ignored', () => {
  const store = harness(async () => {})
  store.apply({ platform_name: '演示平台' })
  assert.equal(store.projectName, '演示平台')
  assert.equal(store.englishName, 'mango-test-platform')
  store.apply({ platform_name: ' ', platform_name_en: '' })
  assert.equal(store.projectName, '演示平台')
  assert.equal(store.englishName, 'mango-test-platform')
})
