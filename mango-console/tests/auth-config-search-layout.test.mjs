import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { reactive } from 'vue'
import { parse } from '@vue/compiler-sfc'
import { config as apiAuthConfig } from './helpers/auth-config-harness.mjs'

function loadUtils(filename, modules = {}) {
  const exports = {}
  new Function('exports', 'require', ts.transpileModule(readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText)(exports, id => { if (!(id in modules)) { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error('Unexpected utility dependency '+id); } return modules[id] })
  return exports
}
const { enableMultiSelectSearch } = loadUtils('src/utils/search-condition.ts')
const { getFormItems } = loadUtils('src/utils/datacleaning.ts')
const uiSource = readFileSync('src/views/uitest/auth-config/index.vue', 'utf8')

test('API authorization name search serializes and resets with the existing search controls', () => {
  const conditions = apiAuthConfig.createConditionItems()
  assert.deepEqual(conditions.slice(0, 2).map(item => item.key), ['id', 'name'])
  const name = conditions.find(item => item.key === 'name')
  assert.equal(name.label, '授权名称')
  assert.equal(name.type, 'input')
  name.value = '演示授权'
  assert.equal(getFormItems(conditions).name, '演示授权')
  name.reset()
  assert.equal(name.value, '')
  const page = readFileSync('src/views/apitest/auth-config/index.vue', 'utf8')
  assert.match(page, /for \(const key of Object.keys\(value\)\) clearEmptyFilter\(value, key\)/)
  assert.match(page, /function onSearchRefresh\(\)\s*\{\s*selectedRowKeys.value = \[\]\s*pagination.page = 1/)
  assert.match(page, /function onResetSearch\(\)[\s\S]*?pagination.page = 1[\s\S]*?doRefresh\(true\)/)
})

function loadConfig(kind) {
  if (kind === 'apitest') return apiAuthConfig
  const source = readFileSync(`src/views/${kind}/auth-config/config.ts`, 'utf8')
  const exports = {}, modules = {
    vue: { reactive }, '@/utils/id-search': { createIdSearchValue: () => '' },
    '@/utils/update-user': { createUpdateUserCondition: () => ({ key: 'update_user', type: 'select', value: [] }), updateUserColumn: () => ({ key:'update_user',width:110 }) },
    '@/utils/search-condition': { enableMultiSelectSearch }, '@/hooks/table': { useTableIndexColumn: () => ({ key:'index',width:100 }), useTableColumn: columns => columns },
  }
  new Function('exports','require',ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText)(exports,id=>{
    if (!(id in modules)) { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error('Unexpected UI config dependency '+id) }
    return modules[id]
  })
  return { ...exports, conditionItems: exports.createConditionItems() }
}

test('UI search configurations belong to each page instance and reset without leaking selections', () => {
  const config=loadConfig('uitest'),first=config.createConditionItems(),second=config.createConditionItems()
  first.find(item=>item.key==='name').value='Example';first.find(item=>item.key==='test_env').value.push(0)
  assert.equal(second.find(item=>item.key==='name').value,'');assert.deepEqual(second.find(item=>item.key==='test_env').value,[])
  first.forEach(item=>item.reset?.());assert.equal(first.find(item=>item.key==='name').value,'');assert.deepEqual(first.find(item=>item.key==='test_env').value,[])
})

test('API and UI both place readable authorization names before environment', () => {
  for (const kind of ['apitest', 'uitest']) {
    const { tableColumns, tableScrollX } = loadConfig(kind)
    assert.deepEqual(tableColumns.slice(0, 3).map(column => column.key), ['index', 'name', 'test_env'])
    assert.equal(tableColumns[1].width, 240)
    assert.equal(tableColumns[1].tooltip, true)
    assert.ok(tableScrollX >= tableColumns.reduce((total, column) => total + column.width, 0))
  }
})

test('UI search supports the API filter set with multi-select and retains name search', () => {
  const { conditionItems } = loadConfig('uitest')
  assert.deepEqual(conditionItems.slice(0, 2).map(item => item.key), ['id', 'name'])
  for (const key of ['test_env', 'auth_type', 'refresh_mode', 'last_refresh_status', 'update_user']) {
    const item = conditionItems.find(item => item.key === key)
    assert.equal(item.multiple, true, key)
    item.value = [0, 1]
    assert.equal(getFormItems(conditionItems)[`${key}__in`], '0,1')
    item.reset()
    assert.deepEqual(item.value, [])
  }
  assert.ok(conditionItems.some(item => item.key === 'id'))
  assert.ok(conditionItems.some(item => item.key === 'name'))
  assert.match(uiSource, /<ApiResourceSearchFilters/)
  assert.match(uiSource, /auth_type: enumStore.ui_auth_type/)
  assert.match(uiSource, /refresh_mode: enumStore.ui_auth_refresh_mode/)
  assert.match(uiSource, /last_refresh_status: enumStore.ui_auth_refresh_status/)
})

test('shared search options can use UI enums without changing API defaults', () => {
  const source = readFileSync('src/components/business/ApiResourceSearchFilters.vue', 'utf8')
  const ast = ts.createSourceFile('search.ts', parse(source).descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
  const method = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name.text === 'selectOptions')
  const code = ts.transpileModule(method.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const apiOptions = [{ key: 1, title: 'API example' }]
  const uiOptions = [{ key: 1, title: 'UI example' }]
  const props = { enumStore: { api_auth_type: apiOptions }, userList: [] }
  const select = new Function('props', code + ';return selectOptions')(props)
  assert.equal(select({ key: 'auth_type' }), apiOptions)
  props.optionOverrides = { auth_type: uiOptions }
  assert.equal(select({ key: 'auth_type' }), uiOptions)
})

test('UI query omits empty filters, preserves zero and resets pagination with search state', () => {
  const { conditionItems } = loadConfig('uitest')
  const ast = ts.createSourceFile('ui.ts', parse(uiSource).descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
  const names = new Set(['normalizeQuery', 'clearEmptyFilter', 'onReset'])
  const methods = ast.statements.filter(node => ts.isFunctionDeclaration(node) && names.has(node.name.text))
    .map(node => node.getText(ast)).join('\n')
  const code = ts.transpileModule(methods, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const query = { project_product: null }
  const pagination = { page: 4, pageSize: 20 }
  const json = { cloneLosslessJson: value => JSON.parse(JSON.stringify(value)) }
  const editor = loadUtils('src/views/uitest/auth-config/auth-editor-records.ts', { '@/utils/lossless-json': json })
  const dto = loadUtils('src/views/uitest/auth-config/auth-list-records.ts', { '@/utils/lossless-json': json, './auth-editor-records': editor })
  const functions = new Function('conditionItems', 'getFormItems', 'query', 'uiAuthListQuery', 'pagination', 'sidebarResetKey', 'doRefresh', 'closeConfirmations',
    code + ';return {normalizeQuery,onReset}')(conditionItems, getFormItems, query, dto.uiAuthListQuery,
      pagination, { value: 0 }, () => {}, () => {})
  assert.deepEqual(functions.normalizeQuery(), {page:4,pageSize:20})
  conditionItems.find(item => item.key === 'test_env').value = [0, 3]
  conditionItems.find(item => item.key === 'auth_type').value = [0]
  assert.deepEqual(functions.normalizeQuery(), { page:4,pageSize:20,test_env__in: '0,3', auth_type__in: '0' })
  functions.onReset()
  assert.equal(pagination.page, 1)
  assert.deepEqual(functions.normalizeQuery(), {page:1,pageSize:20})
})
