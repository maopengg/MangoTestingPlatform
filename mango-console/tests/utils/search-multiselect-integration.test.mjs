import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { reactive, ref } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { baseParse, NodeTypes } from '@vue/compiler-dom'

function loadUtils(filename) {
  const exports = {}
  new Function('exports', ts.transpileModule(readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText)(exports)
  return exports
}
const { enableMultiSelectSearch, normalizeMultiSelectSearchParams } = loadUtils('src/utils/search-condition.ts')
const { getFormItems } = loadUtils('src/utils/datacleaning.ts')

test('actual API Case search component honors all six screenshot fields', () => {
  const config = readFileSync('src/views/apitest/case/config.ts', 'utf8')
  const start = config.indexOf('export const conditionItems')
  const end = config.indexOf('export const formItems', start)
  const code = config.slice(start, end).replace('export ', '')
  const items = new Function('reactive', 'ref', 'createIdSearchValue', 'createUpdateUserCondition', 'enableMultiSelectSearch',
    ts.transpileModule(code, { compilerOptions: { target: ts.ScriptTarget.ES2020 } }).outputText + '; return conditionItems')(
    reactive, ref, () => ref(''), () => ({ key: 'update_user', type: 'select', value: [] }), enableMultiSelectSearch
  )
  for (const key of ['publication_status', 'level', 'scenario_layer', 'scenario_type', 'case_people', 'status']) {
    const item = items.find(item => item.key === key)
    assert.equal(item.multiple, true, key)
    item.value = key === 'publication_status' ? ['published', 'draft_changed'] : [0, 1]
    assert.equal(getFormItems(items)[`${key}__in`], item.value.join(','), key)
    item.reset()
    assert.deepEqual(item.value, [], key)
  }
  const component = readFileSync('src/views/apitest/case/ApiCaseSearchFilters.vue', 'utf8')
  assert.match(component, /:multiple="item.multiple \|\| item.key === 'scenario_tags'"/)
  assert.match(component, /:max-tag-count=/)
})

test('handwritten filter normalization preserves zero, false, pagination and source state', () => {
  const params = { status: [0, 1, 1, null, ''], verdict: [], enabled: [false, true], name: 'example', page: 2, pageSize: 20 }
  assert.deepEqual(normalizeMultiSelectSearchParams(params, ['status', 'verdict', 'enabled']), {
    status__in: '0,1', enabled__in: 'false,true', name: 'example', page: 2, pageSize: 20,
  })
  assert.deepEqual(params.status, [0, 1, 1, null, ''])
  assert.deepEqual(normalizeMultiSelectSearchParams({ status: [] }, ['status']), {})
})

test('API public default-enabled filter supports both states, zero and reset', () => {
  const config = readFileSync('src/views/apitest/public/config.ts', 'utf8')
  const code = config.slice(config.indexOf('export const conditionItems'), config.indexOf('export const formItems')).replace('export ', '')
  const items = new Function('reactive', 'ref', 'createIdSearchValue', 'createUpdateUserCondition', 'enableMultiSelectSearch',
    ts.transpileModule(code, { compilerOptions: { target: ts.ScriptTarget.ES2020 } }).outputText + '; return conditionItems')(
    reactive, ref, () => ref(''), () => ({ key: 'update_user', type: 'select', value: [] }), enableMultiSelectSearch
  )
  const item = items.find(item => item.key === 'status')
  assert.equal(item.label, '默认开启')
  assert.equal(item.multiple, true)
  assert.deepEqual(item.optionItems, [{ key: 1, title: '开启' }, { key: 0, title: '关闭' }])
  for (const values of [[1], [0], [0, 1]]) {
    item.value = values
    assert.equal(getFormItems(items).status__in, values.join(','))
  }
  item.reset()
  assert.deepEqual(item.value, [])
  assert.equal(getFormItems(items).status__in, null)
  const component = readFileSync('src/components/business/ApiResourceSearchFilters.vue', 'utf8')
  assert.match(component, /return options\[item.key\] \?\? item.optionItems/)
})

test('task switches and task group search use collection queries and array resets', () => {
  const config = readFileSync('src/views/timing/tasks/config.ts', 'utf8')
  const code = config.slice(config.indexOf('export const conditionItems'), config.indexOf('export const formItems')).replace('export ', '')
  const items = new Function('reactive', 'ref', 'createIdSearchValue', 'enableMultiSelectSearch',
    ts.transpileModule(code, { compilerOptions: { target: ts.ScriptTarget.ES2020 } }).outputText + ';return conditionItems')(
    reactive, ref, () => ref(''), enableMultiSelectSearch
  )
  for (const key of ['status', 'is_notice', 'task_group']) {
    const item = items.find(item => item.key === key)
    assert.equal(item.multiple, true, key)
    item.value = [0, 1]
    assert.equal(getFormItems(items)[`${key}__in`], '0,1')
    item.reset()
    assert.deepEqual(item.value, [])
  }
})

test('audit ignores disabled search markup and detects a broken live child component', () => {
  const script = readFileSync('scripts/search-multiselect-audit.mjs', 'utf8')
  const ast = ts.createSourceFile('audit.js', script, ts.ScriptTarget.Latest, true, ts.ScriptKind.JS)
  const node = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name.text === 'findSingleSelectSearchModels')
  const find = new Function('parseSfc', 'baseParse', 'NodeTypes', node.getText(ast) + ';return findSingleSelectSearchModels')(parse, baseParse, NodeTypes)
  const source = `<template><template v-if="false" #search-content><a-select v-model="item.value" :multiple="item.multiple"/></template>
    <a-select v-model="item.value" :multiple="item.key === 'scenario_tags'"/></template>`
  assert.deepEqual(find(source, 'ApiCaseSearchFilters.vue'), ['item.value'])
  assert.deepEqual(find(source.replace(":multiple=\"item.key === 'scenario_tags'\"", ':multiple="item.multiple"'), 'ApiCaseSearchFilters.vue'), [])
  assert.match(script, /entry.name.endsWith\('\.vue'\)/)
  assert.doesNotMatch(script.slice(0, script.indexOf('const exactQueryAllowlist')), /'publication_status'/)
})

test('changed search components and pages compile', () => {
  for (const filename of [
    'src/components/business/ApiResourceSearchFilters.vue', 'src/views/apitest/public/index.vue',
    'src/views/apitest/case/ApiCaseSearchFilters.vue', 'src/views/apitest/case/index.vue',
    'src/views/uitest/public/index.vue', 'src/views/system/user/index.vue',
    'src/views/gray/repository/index.vue', 'src/views/gray/execution-log/index.vue', 'src/views/perf/run/index.vue',
    'src/views/timing/tasks/index.vue',
  ]) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [], filename)
    const script = compileScript(descriptor, { id: 'search-multi' })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'search-multi',
      compilerOptions: { bindingMetadata: script.bindings } }).errors, [], filename)
  }
})
