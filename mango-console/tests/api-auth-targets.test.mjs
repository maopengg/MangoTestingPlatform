import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import ts from 'typescript'
import { ref } from 'vue'

const filename = 'src/views/apitest/auth-config/index.vue'
const source = readFileSync(filename, 'utf8')
const { descriptor } = parse(source)
const ast = ts.createSourceFile('auth.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)

test('submit normalizes cleared optional fields without dropping selected values', () => {
  const method = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name.text === 'normalizeSubmitValue')
  const code = ts.transpileModule(method.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const normalize = new Function(code + ';return normalizeSubmitValue')()
  for (const empty of [null, undefined]) {
    const value = normalize({ auth_type: 1, refresh_mode: 3, target_address: empty, public_variable_ids: empty })
    assert.equal(value.target_address, '')
    assert.deepEqual(value.public_variable_ids, [])
  }
  const value = normalize({ auth_type: 1, refresh_mode: 3, target_address: 'https://example.org', public_variable_ids: [7] })
  assert.equal(value.target_address, 'https://example.org')
  assert.deepEqual(value.public_variable_ids, [7])
})

test('target selector is optional and defaults to the configured default address', () => {
  const config = readFileSync('src/views/apitest/auth-config/config.ts', 'utf8')
  assert.match(config, /label: '适用目标地址', key: 'target_address', value: ref\(''\), type: 'select', required: false/)
  assert.match(source, /:options="targetOptions" :loading="targetsLoading"/)
  assert.match(source, /record.target_address \|\| '默认地址'/)
  const script = compileScript(descriptor, { id: 'auth-targets' })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: 'auth-targets',
    compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
})

test('target loading uses product scope and environment zero, with stale responses ignored', async () => {
  const method = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name.text === 'loadTargetOptions')
  const code = ts.transpileModule(method.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const product = ref({ value: [1, 2] })
  const options = ref([])
  const loading = ref(false)
  const pending = []
  const calls = []
  const load = new Function('projectProductItem', 'authEnvironment', 'targetOptions', 'targetsLoading',
    'getOptionId', 'getApiAuthTargets', 'let targetRequest=0;' + code + ';return loadTargetOptions')(
      product, ref(0), options, loading, value => value?.at(-1),
      query => { calls.push(query); return new Promise(resolve => pending.push(resolve)) },
    )
  const first = load()
  assert.equal(loading.value, true)
  assert.deepEqual(calls[0], { project_product: 2, test_env: 0 })
  product.value = { value: [1, 3] }
  const second = load()
  pending[1]({ data: [{ value: 'https://example.org', label: 'Example' }] })
  await second
  pending[0]({ data: [{ value: 'https://example.com' }] })
  await first
  assert.equal(options.value[0].value, 'https://example.org')
  assert.equal(loading.value, false)
})
