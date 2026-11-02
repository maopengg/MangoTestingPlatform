import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { reactive, ref } from 'vue'
import { parse } from '@vue/compiler-sfc'

function loadUtils(filename) {
  const exports = {}
  new Function('exports', ts.transpileModule(readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText)(exports)
  return exports
}
const { enableMultiSelectSearch } = loadUtils('src/utils/search-condition.ts')
const { getFormItems } = loadUtils('src/utils/datacleaning.ts')
const uiSource = readFileSync('src/views/uitest/auth-config/index.vue', 'utf8')

test('API authorization name search serializes and resets with the existing search controls', () => {
  const source = readFileSync('src/views/apitest/auth-config/config.ts', 'utf8')
  const start = source.indexOf('export const conditionItems')
  const end = source.indexOf('export const formItems')
  const code = ts.transpileModule(source.slice(start, end).replaceAll('export ', ''), {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
  const conditions = new Function('reactive', 'ref', 'createIdSearchValue', 'createUpdateUserCondition', 'enableMultiSelectSearch', code + ';return conditionItems')(
    reactive, ref, () => '', () => ({ key: 'update_user', type: 'select', value: [] }), enableMultiSelectSearch,
  )
  assert.deepEqual(conditions.slice(0, 2).map(item => item.key), ['id', 'name'])
  const name = conditions.find(item => item.key === 'name')
  assert.equal(name.label, '授权名称')
  assert.equal(name.type, 'input')
  name.value = '演示授权'
  assert.equal(getFormItems(conditions).name, '演示授权')
  name.reset()
  assert.equal(name.value, '')
  const page = readFileSync('src/views/apitest/auth-config/index.vue', 'utf8')
  assert.match(page, /clearEmptyFilter\(value, 'name'\)/)
  assert.match(page, /function onSearchRefresh\(\)\s*\{\s*pagination.page = 1/)
  assert.match(page, /function onResetSearch\(\)[\s\S]*?pagination.page = 1[\s\S]*?doRefresh\(true\)/)
})

function loadConfig(kind) {
  const source = readFileSync(`src/views/${kind}/auth-config/config.ts`, 'utf8')
  const start = source.indexOf(`export const ${kind === 'uitest' ? 'conditionItems' : 'tableColumns'}`)
  const code = ts.transpileModule(source.slice(start).replaceAll('export ', ''), {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
  return new Function('reactive', 'createIdSearchValue', 'createUpdateUserCondition', 'enableMultiSelectSearch',
    'useTableColumn', 'table', 'updateUserColumn', code +
    `;return {tableColumns, tableScrollX${kind === 'uitest' ? ', conditionItems' : ''}}`)(
      reactive, () => '', () => ({ key: 'update_user', type: 'select', value: [] }), enableMultiSelectSearch,
      columns => columns, { indexColumn: { key: 'index', width: 100 } }, () => ({ width: 110 }),
    )
}

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
  const query = { project_product: '' }
  const pagination = { page: 4 }
  const functions = new Function('conditionItems', 'getFormItems', 'query', 'getOptionId', 'pagination', 'sidebarResetKey', 'doRefresh',
    code + ';return {normalizeQuery,onReset}')(conditionItems, getFormItems, query, value => value,
      pagination, { value: 0 }, () => {})
  assert.deepEqual(functions.normalizeQuery(), {})
  conditionItems.find(item => item.key === 'test_env').value = [0, 3]
  conditionItems.find(item => item.key === 'auth_type').value = [0]
  assert.deepEqual(functions.normalizeQuery(), { test_env__in: '0,3', auth_type__in: '0' })
  functions.onReset()
  assert.equal(pagination.page, 1)
  assert.deepEqual(functions.normalizeQuery(), {})
})
