import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { parse, compileTemplate } from '@vue/compiler-sfc'
const base = new URL('../../../../../src/views/apitest/case/details/', import.meta.url)
const exports = {}
new Function('exports', ts.transpileModule(readFileSync(new URL('components/callback-results.ts', base), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText)(exports)
const { callbackResultsForScenario, callbackAssertionCount, callbackCheckRows, callbackResultsFromAssertions,
  callbackCheckPresentation, callbackNeedsDefinitions } = exports

test('human-readable checks use frozen type/source/field, never guess from internal keys', () => {
  const enums = { api_callback_check_type: [{ key: 'json_compact', title: '紧凑 JSON' },
    { key: 'field', title: '字段断言' }], api_callback_source: [{ key: 'business_json', title: '业务 JSON（解密后）' }] }
  assert.deepEqual(callbackCheckPresentation({ type: 'json_compact', source: 'business_json', key: 'business_compact' }, enums), {
    title: '紧凑 JSON', target: '业务 JSON（解密后）', source: '',
    requirement: 'JSON 不含格式化换行和多余空格', missingDefinition: false,
  })
  const field = callbackCheckPresentation({ type: 'field', source: 'business_json', field: '$.header.app_id',
    assertions: [{ method: '等于' }] }, enums)
  assert.equal(field.title, '字段断言')
  assert.equal(field.target, '$.header.app_id')
  assert.equal(field.requirement, '等于')
  const old = { delivery_results: [{ id: 1, checks: [{ key: 'raw_signature', passed: true, type: undefined }] }] }
  assert.equal(callbackNeedsDefinitions(old), true)
  assert.equal(callbackCheckPresentation(callbackCheckRows(old)[0], enums).title, '历史检查项')
  const hydrated = { ...old, check_definitions: [{ key: 'raw_signature', type: 'lark_signature', source: 'raw_body' }] }
  assert.equal(callbackNeedsDefinitions(hydrated), false)
  assert.match(callbackCheckPresentation(callbackCheckRows(hydrated)[0], enums).requirement, /原始正文/)
  assert.equal(callbackCheckRows(hydrated)[0].passed, true)
})

test('new archives read callback checks from ass only and preserve diagnostics and scenario isolation', () => {
  const ass = [
    { method: '响应断言', status: 1 },
    { group_name: '回调', status: 1, callback: { run_id: 1, rule_key: 'rule', run_status: 'passed', events: 1, deliveries: 1 } },
    { ass_msg: '诊断失败', status: 1, callback: { run_id: 1, check_key: 'diagnostic', delivery_id: 10,
      passed: false, diagnostic: true, check_type: 'lark_compact_signature_simulation' } },
  ]
  const runs = callbackResultsFromAssertions(ass, [{ id: 999 }])
  assert.equal(runs.length, 1)
  assert.equal(runs[0].id, 1)
  const rows = callbackCheckRows(runs[0])
  assert.equal(rows[0].passed, false)
  assert.equal(rows[0].diagnostic, true)
  assert.equal(callbackAssertionCount(runs), 1)
  assert.deepEqual(callbackResultsFromAssertions([], [{ id: 999 }]), [{ id: 999 }])
  assert.equal(callbackResultsFromAssertions([
    { status: 0, ass_msg: '等待回调超时', callback: { run_id: 2, run_status: 'timeout' } },
  ])[0].error_message, '等待回调超时')
})

test('new and archived callback results stay within the executed trigger step and scenario', () => {
  const old = { id: 1, rule_key: 'one' }
  const current = { id: 2, trigger_step_key: 'step-10' }
  const other = { id: 3, trigger_step_key: 'step-11', rule_key: 'one' }
  const result = { steps: [{ id: 10, parameter_id: 20 }], callback_results: [old, current, other] }
  const rules = [{ key: 'one', trigger_step_key: 'step-10' }]
  assert.deepEqual(callbackResultsForScenario(result, 10, 20, rules), [old, current])
  assert.deepEqual(callbackResultsForScenario(result, 10, 21, rules), [])
  assert.deepEqual(callbackResultsForScenario(result, 11, 20, rules), [])
  assert.deepEqual(callbackResultsForScenario(result, 10, 20, []), [current])
  assert.deepEqual(callbackResultsForScenario(null, 10, 20, rules), [])
})

test('counts every delivery check and represents a timed-out run without deliveries', () => {
  const runs = [{ id: 1, status: 'passed', delivery_results: [{ id: 101, event_id: 'a', checks: [
    { key: 'signature', passed: true }, { key: 'field', passed: false, assertions: [{ actual: 0, expect: false }] },
    { key: 'diagnostic', passed: false, diagnostic: true },
  ] }, { id: 102, checks: [{ key: 'signature', passed: true }] }] },
  { id: 2, status: 'failed', error_message: '回调超时', delivery_results: [] }]
  assert.equal(callbackAssertionCount(runs), 5)
  const rows = callbackCheckRows(runs[0])
  assert.equal(rows.length, 4)
  assert.equal(new Set(rows.map(row => row.rowKey)).size, 4)
  assert.deepEqual(rows[1].assertions[0], { actual: 0, expect: false })
  assert.equal(rows[2].diagnostic, true)
})

test('frozen definitions explain checks without replacing their recorded outcome', () => {
  const run = { check_definitions: [{ key: 'field', type: 'field', field: '$.id' }],
    delivery_results: [{ id: 1, checks: [{ key: 'field', passed: false, message: '不匹配' }] }] }
  assert.deepEqual(callbackCheckRows(run)[0], { key: 'field', type: 'field', field: '$.id', passed: false,
    message: '不匹配', rowKey: '1-0', deliveryId: 1, eventId: undefined, receivedAt: undefined })
})

test('callback result UI compiles, preserves failure and diagnostic states, and reuses assertion details', () => {
  const filename = 'components/ApiCaseCallbackAssertions.vue'
  const source = readFileSync(new URL(filename, base), 'utf8')
  const { descriptor } = parse(source)
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'callback' }).errors, [])
  assert.match(source, /<AssertionResult/)
  assert.match(source, /仅诊断/)
  assert.match(source, /run.error_message/)
  const page = readFileSync(new URL('index.vue', base), 'utf8')
  assert.match(page, /getAssertionResultData\(item\).length\s*\+\s*callbackAssertionCount/)
})

test('unified results read only the scenario snapshot and do not borrow another execution', () => {
  const page = readFileSync(new URL('index.vue', base), 'utf8')
  const tree = ts.createSourceFile('page.ts', parse(page).descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
  const declaration = tree.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === 'getCallbackAssertionResults')
  const code = ts.transpileModule(declaration.getText(tree), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const read = new Function('callbackResultsFromAssertions', code + ';return getCallbackAssertionResults')(callbackResultsFromAssertions)
  const item = { result_data: { callback_results: [{ id: 1 }] } }
  assert.deepEqual(read(item), [{ id: 1 }])
  assert.deepEqual(read({ result_data: null }), [])
  assert.deepEqual(read({ result_data: { callback_results: [{ id: 2 }] } }), [{ id: 2 }])
})
