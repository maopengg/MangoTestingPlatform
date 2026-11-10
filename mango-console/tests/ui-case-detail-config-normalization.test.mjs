import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { loadModule } from './helpers/auth-config-harness.mjs'

const config = loadModule('src/views/uitest/case/details/config.ts', { '@/setting': { fieldNames: { label: 'title', value: 'key' } } })
test('variable configuration is per-instance and retains field names, environment semantics and input contracts', () => {
  const calls = [], environments = [{ key: '__common__', title: 'Common' }, { key: 0, title: 'Test' }]
  const first = config.createUiCaseVariableFields(environments, item => item.test_envs, (value, item) => { item.test_envs = value; calls.push(value) })
  const other = config.createUiCaseVariableFields([], () => [], () => {})
  assert.deepEqual(first.map(field => field.field), ['test_envs', 'key', 'value']); assert.equal(first[0].multiple, true); assert.equal(first[0].options[1].key, 0)
  assert.deepEqual(first[0].fieldNames, { label: 'title', value: 'key' }); first[1].label = 'Modified'; assert.equal(other[1].label, 'Key')
  const draft = { test_envs: [] }; first[0].setValue([0], draft); assert.deepEqual(first[0].getValue(draft), [0]); assert.deepEqual(calls, [[0]])
  assert.equal(first[1].type, 'input'); assert.equal(first[2].showTitle, true)
})
test('execution socket event configuration retains exactly existing UI result protocol events', () => {
  assert.deepEqual([...config.UI_CASE_RESULT_SOCKET_EVENTS], ['u_page_steps', 'u_page_step_node_progress', 'u_test_case', 'u_test_suite_details'])
})
test('parent retains actual step editor/create/history/cache/live entries while removing only unreachable legacy sections', () => {
  const source = readFileSync('src/views/uitest/case/details/index.vue', 'utf8')
  for (const entry of ['PageStepsDetails', 'case-input-mode', 'UiCaseStepCreateDialog', 'ExecutionResultHistoryDrawer', 'UiLiveStreamPanel', 'DataFactoryCaseConfigPanel', 'UiCaseStepRetryEditor', 'UiCaseStepUrlSwitch']) assert.ok(source.includes(entry), entry)
  assert.doesNotMatch(source, /v-if="false"|<ModalDialog|<UiElementEditPanel|const stepAsset|function doAppend|function onUpdate1|function onDataForm|function appendCaseStepFromAsset/)
  assert.match(source, /:field-config="caseVariableFields"/)
  assert.match(readFileSync('src/views/uitest/case/details/composables/useCaseRuntimeResults.ts', 'utf8'), /new Set<string>\(UI_CASE_RESULT_SOCKET_EVENTS\)/)
})
