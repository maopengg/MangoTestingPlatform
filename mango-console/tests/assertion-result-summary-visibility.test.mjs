import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import ts from 'typescript'
import { computed, ref } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = 'src/components/feedback/AssertionResult.vue'
const source = fs.readFileSync(filename, 'utf8')
const page = fs.readFileSync('src/views/apitest/case/details/index.vue', 'utf8')
const rows = [
  {source_type: 'jsonpath', status: 0, group_name: 'or', group_logic: 'OR', group_result: true},
  {source_type: 'jsonpath', status: 1, group_name: 'or', group_logic: 'OR', group_result: true},
  {source_type: 'assertion_group', status: 1, group_name: 'or'},
]
test('display and failure filter omit synthetic summaries without mutating archived results', () => {
  const code = source.slice(source.indexOf('  const assertionData ='), source.indexOf('  watch(failedCount'))
  const state = new Function('props', 'computed', 'ref', ts.transpileModule(code, {}).outputText + '; return {assertionData, onlyFailed, visibleAssertions}')({data: rows}, computed, ref)
  assert.equal(state.assertionData.value.length, 2)
  state.onlyFailed.value = true
  assert.deepEqual(state.visibleAssertions.value, [rows[0]])
  assert.equal(rows.length, 3)
  assert.equal(rows[0].group_result, true)
})
test('scenario badge counts exclude summaries for archived and one-click verification results', () => {
  const code = page.slice(page.indexOf('  function getAssertionResultData('), page.indexOf('  function getCallbackAssertionResults('))
  const read = new Function(ts.transpileModule(code, {}).outputText + '; return getAssertionResultData')()
  assert.equal(read({result_data: {ass: rows}}).length, 2)
  assert.equal(read({__assertion_verify_result: rows}).length, 2)
  assert.deepEqual(read({}), [])
})
test('group colors stay identical across pass/fail rows and failure filtering', () => {
  const code = source.slice(source.indexOf('  const assertionData ='), source.indexOf('  watch(failedCount'))
  const data = [...rows, {source_type: 'jsonpath', status: 1, group_name: 'other'}]
  const state = new Function('props', 'computed', 'ref', ts.transpileModule(code, {}).outputText + '; return {groupTones, onlyFailed}')({data}, computed, ref)
  assert.equal(state.groupTones.value.get('or'), 0)
  assert.equal(state.groupTones.value.get('other'), 1)
  state.onlyFailed.value = true
  assert.equal(state.groupTones.value.get('other'), 1)
  assert.equal((source.match(/:data-group-tone=/g) || []).length, 2)
  assert.match(source, /item--pass \{ background: color-mix\(in srgb, var\(--m-success\)/)
  assert.match(source, /item--fail \{ background: color-mix\(in srgb, var\(--m-danger\)/)
})
test('assertion result component compiles', () => {
  const {descriptor} = parse(source, {filename})
  const script = compileScript(descriptor, {id: 'assertion-summary'})
  assert.deepEqual(compileTemplate({source: descriptor.template.content, filename, id: 'assertion-summary', compilerOptions: {bindingMetadata: script.bindings}}).errors, [])
})
