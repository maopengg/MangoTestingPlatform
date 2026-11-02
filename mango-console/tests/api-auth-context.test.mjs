import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { ref, reactive } from 'vue'
import { parse } from '@vue/compiler-sfc'

const source = readFileSync('src/views/apitest/auth-config/index.vue', 'utf8')
const ast = ts.createSourceFile('auth.ts', parse(source).descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)

test('associated variables remain an optional array in create and edit payloads', () => {
  const config = readFileSync('src/views/apitest/auth-config/config.ts', 'utf8')
  const configAst = ts.createSourceFile('config.ts', config, ts.ScriptTarget.Latest, true)
  const declaration = configAst.statements.filter(ts.isVariableStatement)
    .flatMap(node => [...node.declarationList.declarations]).find(node => node.name.getText(configAst) === 'formItems')
  const code = ts.transpileModule(`const ${declaration.getText(configAst)}`, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const items = new Function('reactive', 'ref', code + ';return formItems')(reactive, ref)
  const item = items.find(item => item.key === 'public_variable_ids')
  assert.equal(item.multiple, true)
  assert.deepEqual(item.value, [])
  item.value = [7, 8]
  const exports = {}
  new Function('exports', ts.transpileModule(readFileSync('src/utils/datacleaning.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText)(exports)
  assert.deepEqual(exports.getFormItems(items).public_variable_ids, [7, 8])
  assert.match(source, /:loading="publicVariablesLoading"/)
  assert.match(source, /@change="onAuthVariableContextChange"/)
})

test('variable options use real product ID, accept environment zero and ignore stale results', async () => {
  const declaration = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name.text === 'loadPublicVariableOptions')
  const code = ts.transpileModule(declaration.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const options = ref([])
  const loading = ref(false)
  const product = ref({ value: [1, 3] })
  const pending = []
  const calls = []
  const load = new Function('projectProductItem', 'authEnvironment', 'publicVariableOptions', 'publicVariablesLoading',
    'getApiAuthPublicVariables', 'getOptionId', 'formItems',
    'let publicVariableRequest = 0;' + code + ';return loadPublicVariableOptions')(
      product, ref(0), options, loading,
      query => { calls.push(query); return new Promise(resolve => pending.push(resolve)) },
      value => value[value.length - 1], [{ key: 'public_variable_ids', value: [] }],
    )
  const first = load('tenant')
  assert.equal(loading.value, true)
  assert.equal(calls[0].project_product, 3)
  assert.equal(calls[0].test_env, 0)
  product.value = { value: [1, 4] }
  const second = load('user')
  pending[1]({ data: [{ id: 8, name: 'User', key: 'user_id' }] })
  await second
  pending[0]({ data: [{ id: 7, name: 'Tenant', key: 'tenant_id' }] })
  await first
  assert.deepEqual(options.value.map(item => item.value), [8])
  assert.equal(loading.value, false)
})
