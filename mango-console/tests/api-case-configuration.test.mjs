import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { computed, reactive, ref } from 'vue'
import { parse } from '@vue/compiler-sfc'

const source = readFileSync(new URL('../src/views/apitest/case/useCaseConfigurationSummary.ts', import.meta.url), 'utf8')
const tree = ts.createSourceFile('summary.ts', source, ts.ScriptTarget.Latest, true)
const hook = tree.statements.find(node => ts.isFunctionDeclaration(node)).getText(tree).replace('export ', '')
const code = ts.transpileModule(hook, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
function setup(fetch) {
  let dispose
  const state = new Function('ref', 'onScopeDispose', 'getApiCaseConfigurationSummary', `${code};return useCaseConfigurationSummary()`)(
    ref, fn => { dispose = fn }, fetch,
  )
  return { ...state, dispose: () => dispose() }
}
const summary = id => ({ id, has_sql: true, sql_count: 1, has_data_factory: false, data_factory_count: 0 })

test('opening an empty configuration selector refreshes enums with loading and retry feedback', async () => {
  const component = readFileSync(new URL('../src/views/apitest/case/ApiCaseSearchFilters.vue', import.meta.url), 'utf8')
  const ast = ts.createSourceFile('case.ts', parse(component).descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
  const method = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name.text === 'loadConfigurationSearchOptions')
  const code = ts.transpileModule(method.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const loading = ref(false), messages = []
  let requests = 0, resolve
  const enumStore = { api_case_configuration_filter: [], getEnum: async force => {
    assert.equal(force, true)
    requests++
    await new Promise(done => { resolve = done })
  } }
  const load = new Function('configurationOptionsLoading', 'props', 'Message', code + ';return loadConfigurationSearchOptions')(
    loading, { enumStore }, { warning: text => messages.push(text), error: text => messages.push(text) },
  )
  const pending = load(true)
  assert.equal(loading.value, true)
  await load(true)
  assert.equal(requests, 1)
  enumStore.api_case_configuration_filter = [{ key: 'has_sql', title: '有 SQL' }]
  resolve()
  await pending
  assert.equal(loading.value, false)
  assert.deepEqual(messages, [])
  await load(false)
  await load(true)
  assert.equal(requests, 1)
  enumStore.api_case_configuration_filter = []
  enumStore.getEnum = async () => {}
  await load(true)
  assert.equal(messages.length, 1)
  enumStore.getEnum = async () => { throw new Error('offline') }
  await load(true)
  assert.equal(messages.length, 2)
  assert.equal(loading.value, false)
})

test('one configuration selector disables only the opposite option and resets immediately', () => {
  const readModule = path => readFileSync(new URL(path, import.meta.url), 'utf8').replace(/^import .*\n/gm, '').replaceAll('export function', 'function')
  const compiled = ts.transpileModule(readModule('../src/views/apitest/search-filter-options.ts') + '\n' +
    readModule('../src/views/apitest/case/api-case-search-filter-options.ts'), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const resolveOptions = new Function(compiled + ';return resolveApiCaseSearchOptions')()
  const conditions = reactive([{ key: 'execution_configuration', value: [] }])
  const enumStore = { api_case_configuration_filter: ['has_sql', 'no_sql', 'has_data_factory', 'no_data_factory'].map(key => ({ key })) }
  const options = computed(() => resolveOptions(conditions[0], [], enumStore))
  assert.equal(options.value.length, 4)
  const disabled = key => options.value.find(item => item.key === key).disabled
  assert.ok(options.value.every(item => !item.disabled))
  conditions[0].value = ['has_sql']
  assert.equal(disabled('no_sql'), true)
  assert.equal(disabled('has_sql'), false)
  assert.equal(disabled('has_data_factory'), false)
  conditions[0].value = ['has_sql', 'no_data_factory']
  assert.equal(disabled('no_sql'), true)
  assert.equal(disabled('has_data_factory'), true)
  conditions[0].value = ['no_sql', 'has_data_factory']
  assert.equal(disabled('has_sql'), true)
  assert.equal(disabled('no_data_factory'), true)
  conditions[0].value = []
  assert.ok(options.value.every(item => !item.disabled))
  assert.ok(enumStore.api_case_configuration_filter.every(item => item.disabled === undefined))
})

test('page changes and disposal ignore late summary responses', async () => {
  const pending = []
  const state = setup(() => new Promise(resolve => pending.push(resolve)))
  const old = state.load([1])
  const current = state.load([2])
  pending[1]({ data: [summary(2)] })
  await current
  pending[0]({ data: [summary(1)] })
  await old
  assert.deepEqual(Object.keys(state.summaries.value), ['2'])
  const closing = state.load([3])
  state.dispose()
  pending[2]({ data: [summary(3)] })
  await closing
  assert.deepEqual(state.summaries.value, {})
  assert.equal(state.loading.value, false)
})

test('large pages use bounded batches rather than per-case requests', async () => {
  const calls = []
  const state = setup(async ids => { calls.push(ids); return { data: ids.map(summary) } })
  await state.load([...Array.from({ length: 405 }, (_, index) => index + 1), 1, 0, NaN])
  assert.deepEqual(calls.map(ids => ids.length), [200, 200, 5])
  assert.equal(Object.keys(state.summaries.value).length, 405)
  assert.equal(state.loading.value, false)
})

test('failure and empty lists never fabricate a no-configuration result', async () => {
  let requests = 0
  const state = setup(async () => { requests++; throw new Error('offline') })
  await state.load([1])
  assert.equal(state.summaries.value[1], undefined)
  assert.equal(state.loading.value, false)
  await state.load([])
  assert.equal(requests, 1)
})

test('review drawer uses supplied configuration without fetching the editing case', async () => {
  const component = readFileSync(new URL('../src/views/apitest/case/components/ApiCaseConfigurationDrawer.vue', import.meta.url), 'utf8')
  const ast = ts.createSourceFile('drawer.ts', parse(component).descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
  const methods = ast.statements.filter(node => ts.isFunctionDeclaration(node) && ['openSnapshot', 'load', 'onVisibilityChange'].includes(node.name.text))
    .map(node => ts.transpileModule(node.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText).join('\n')
  let requests = 0, invalidations = 0
  const state = {
    snapshot: ref(null), summary: ref(null), visible: ref(false), loading: ref(true), failed: ref(true),
    detailPermission: ref('api.case:read'), title: ref(''),
    permissions: { hasPermission: () => true },
    pagination: { page: 3, setTotalSize(value) { this.total = value } },
    invalidateRequests: () => { invalidations++ },
    getApiCaseConfigurationDetails: () => { requests++; throw new Error('must not fetch editing configuration') },
  }
  const methodsUnderTest = new Function(...Object.keys(state), `${methods};return {openSnapshot,load,onVisibilityChange}`)(...Object.values(state))
  const details = { id: 29, name: 'Review snapshot', sql_count: 1, data_factory_count: 0,
    items: [{ kind: 'sql', configuration: { sql: 'select 1' } }] }
  methodsUnderTest.openSnapshot(details, 'api.case:read')
  assert.deepEqual(state.summary.value, details)
  assert.equal(state.pagination.page, 1)
  assert.equal(state.pagination.total, 1)
  assert.equal(state.visible.value, true)
  assert.equal(state.loading.value, false)
  await methodsUnderTest.load()
  assert.equal(requests, 0)
  methodsUnderTest.onVisibilityChange(false)
  assert.equal(state.snapshot.value, null)
  assert.equal(state.summary.value, null)
  assert.equal(invalidations, 2)
  state.permissions.hasPermission = () => false
  methodsUnderTest.openSnapshot(details, 'api.case:read')
  assert.equal(state.visible.value, false)
})

test('readonly factory opens the shared field preview with case overrides and cannot save', async () => {
  const component = readFileSync(new URL('../src/components/DataFactory/CaseConfigPanel.vue', import.meta.url), 'utf8')
  const script = parse(component).descriptor.scriptSetup.content
  const ast = ts.createSourceFile('panel.ts', script, ts.ScriptTarget.Latest, true)
  const functions = ast.statements.filter(node => ts.isFunctionDeclaration(node) && ['openReadonly', 'save'].includes(node.name.text))
    .map(node => ts.transpileModule(node.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText).join('\n')
  const template = { id: 7, entity: { id: 3, datasource_alias: { id: 4, name: '隔离数据库' } }, field_overrides: { name: '模板默认值' } }
  const fields = [{ name: 'order_name', generator_type: 1 }]
  const resets = []
  const state = {
    props: { readonly: true }, form: { template: 7 },
    templateList: ref([]), readonlyError: ref(false), visible: ref(false), templateLoading: ref(false), fieldLoading: ref(false),
    fieldRows: ref([]), datasourceAliasOptions: ref([]), canPreviewConfiguration: ref(true),
    getDataFactoryTemplate: async () => ({ data: [template] }),
    getDataFactoryField: async ({ entity }) => { assert.equal(entity, 3); return { data: fields } },
    resetForm: record => { resets.push(record) },
    loadItemFields: async () => {}, loadCasePreview: async () => {},
  }
  const run = new Function(...Object.keys(state), `let readonlyRequestVersion = 0;${functions};return {openReadonly,save}`)(...Object.values(state))
  const record = { id: 1, template: { id: 7 }, field_overrides: { name: '当前用例覆盖值' } }
  await run.openReadonly(record)
  assert.equal(state.visible.value, true)
  assert.deepEqual(state.templateList.value[0], template)
  assert.deepEqual(state.fieldRows.value, fields)
  assert.deepEqual(resets[1].field_overrides, record.field_overrides)
  assert.equal(state.readonlyError.value, false)
  assert.equal(state.fieldLoading.value, false)
  assert.equal(await run.save(), false)
})
