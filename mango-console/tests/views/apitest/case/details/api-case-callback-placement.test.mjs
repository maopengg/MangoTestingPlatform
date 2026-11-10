import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse } from '@vue/compiler-sfc'

const base = new URL('../../../../../src/views/apitest/case/details/', import.meta.url)
const read = path => readFileSync(new URL(path, base), 'utf8')
const panel = read('components/ApiCaseCallbackPanel.vue')
const script = parse(panel).descriptor.scriptSetup.content
const ast = ts.createSourceFile('callback.ts', script, ts.ScriptTarget.Latest, true)
const pageAst = ts.createSourceFile('details.ts', parse(read('index.vue')).descriptor.scriptSetup.content,
  ts.ScriptTarget.Latest, true)
const configModule = { exports: {} }
new Function('exports', ts.transpileModule(read('components/callback-config.ts'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText)(configModule.exports)
const { callbackRulesForStep, callbackConfigurationBlock, callbackRuleName,
  hasCustomCallbackSettings, callbackCheckSummary, checkColumns, callbackRequiredConfigError } = configModule.exports

function loadFunction(name, dependencies, tree = ast) {
  const declaration = tree.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === name)
  assert.ok(declaration, `${name} must exist`)
  const code = ts.transpileModule(declaration.getText(tree), {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
  const injected = { callbackRequiredConfigError, editorSession: 0, createCallbackRuleDraft: configModule.exports.createCallbackRuleDraft, ...(dependencies.pageData ? { caseRecord: { value: dependencies.pageData.record } } : {}), ...dependencies }
  return new Function(...Object.keys(injected), `${code}; return ${name}`)(...Object.values(injected))
}

test('callback entry belongs to scenario assertion tabs, without a duplicate Case tab', () => {
  assert.match(read('components/ApiCaseAssertionPanel.vue'), /key="36" title="回调"/)
  assert.match(read('components/ApiCaseAssertionPanel.vue'), /name="callback"/)
  assert.match(read('components/ApiCaseAssertionPanel.vue'), /v-if="activeKey !== '36'"/)
  assert.doesNotMatch(read('components/ApiCaseOrchestrationPanel.vue'), /回调验证|name="callbacks"/)
  assert.match(read('index.vue'), /:trigger-step="selectedStep"/)
  assert.doesNotMatch(panel, /v-model="form.trigger_step_key"/)
})

test('callback and normal assertions reuse the same editor and method catalogue', () => {
  assert.match(panel, /import GeneralAssertionEditor/)
  assert.match(read('components/ApiCaseAssertionPanel.vue'), /<GeneralAssertionEditor/)
  assert.match(read('index.vue'), /<ApiCaseCallbackPanel\s+:general-methods="optionLists.ass"/)
  assert.match(panel, /callback-actual/)
})

test('shared editor updates all members of a relation group and respects read-only mode', () => {
  const source = readFileSync(new URL('../../../../../src/components/forms/GeneralAssertionEditor.vue', import.meta.url), 'utf8')
  const tree = ts.createSourceFile('editor.ts', parse(source).descriptor.scriptSetup.content,
    ts.ScriptTarget.Latest, true)
  const props = { editLocked: false }
  let saved = 0
  const update = loadFunction('updateGroup', { props, save: () => saved++ }, tree)
  const list = [{ group_name: 'one', group_logic: 'OR' }, { group_name: 'one', group_logic: 'OR' },
    { group_name: '', group_logic: 'AND' }]
  update('AND', list, 0)
  assert.deepEqual(list.map(item => item.group_logic), ['AND', 'AND', 'AND'])
  assert.equal(saved, 1)
  props.editLocked = true
  update('OR', list, 0)
  assert.equal(saved, 1)
  assert.equal(list[0].group_logic, 'AND')
})

test('new field checks use general assertions; legacy checks are not silently converted', () => {
  const form = { value: { checks: [] } }
  const expandedCheckKeys = { value: [] }
  loadFunction('addCheck', { form, newKey: () => 'check', expandedCheckKeys,
    canConfigure: { value: true }, saving: { value: false }, props: { savePending: false } })()
  assert.equal(form.value.checks[0].general_editor, true)
  assert.equal(form.value.checks[0].assertions.length, 1)
  assert.deepEqual(expandedCheckKeys.value, ['check'])
  assert.match(panel, /改用通用断言/)
  assert.match(panel, /check.general_editor = Boolean\(check.assertions\?\.length\)/)
})

test('callback checks use a compact table with shared expandable editing', () => {
  assert.match(panel, /:columns="checkColumns"/)
  assert.match(panel, /#expand-row="\{ record: check \}"/)
  assert.match(panel, /v-model:expanded-keys="expandedCheckKeys"/)
  assert.doesNotMatch(panel, /v-for="\(check, index\) in form.checks"/)
  assert.equal(checkColumns.at(-1).fixed, 'right')
  assert.equal(checkColumns.at(-1).width, 160)
  assert.deepEqual(checkColumns.map(column => column.title),
    ['序号', '检查类型', '检查来源', '回调字段', '断言要求', '操作'])
})

test('callback configuration reuses the shared drawer, spacing tokens, compact grid and contained table scroll', () => {
  assert.match(panel, /<BaseSidePanel\s+v-model:visible="editorVisible"/)
  assert.match(panel, /#footer-buttons/)
  assert.match(panel, /mango-config-form-grid mango-callback-form-fields/)
  assert.match(panel, /class="mango-native-scroll-table"/)
  assert.match(panel, /:scroll="\{ x: 1100, y: '100%' \}"/)
  assert.doesNotMatch(panel, /:scrollbar=/)
  assert.match(panel, /\.mango-callback-check-table\s*\{\s*height: 480px;/)
  assert.match(panel, /<template #extra>/)
  assert.doesNotMatch(panel, /<template #help/)
  assert.match(panel, /padding: var\(--m-card-padding\)/)
  assert.match(panel, /color: var\(--m-muted\)/)
})

test('summaries retain variable expressions, zero, false, structured values, and relation groups', () => {
  const assertions = [{ method: 'equal', group_name: '任选', group_logic: 'OR', value: {
    label: '等于', parameter: [{ f: 'actual', v: '${{__callback_actual__}}' },
      { f: 'expect', n: '预期值', v: '${{callback_run_id}}' }] } }]
  const summary = callbackCheckSummary({ type: 'field', assertions })
  assert.match(summary, /任选（或）/)
  assert.ok(summary.includes('${{callback_run_id}}'))
  assert.ok(!summary.includes('__callback_actual__'))
  for (const value of [0, false, null, { a: [1, true] }]) {
    assertions[0].value.parameter[1].v = value
    assert.ok(callbackCheckSummary({ type: 'field', assertions }).includes(JSON.stringify(value)))
  }
  assert.equal(callbackCheckSummary({ type: 'field', operator: 'exists' }), '字段存在')
  assert.equal(callbackCheckSummary({ type: 'field', general_editor: true }), '待配置断言')
  assert.match(callbackCheckSummary({ type: 'lark_compact_signature_simulation' }), /仅诊断/)
})

test('removing a check preserves other rows and readonly or pending forms cannot mutate', () => {
  const form = { value: { checks: [{ key: 'one' }, { key: 'two' }] } }
  const expandedCheckKeys = { value: ['one'] }
  const canConfigure = { value: false }, saving = { value: false }, props = { savePending: false }
  const dependencies = { form, expandedCheckKeys, canConfigure, saving, props }
  const remove = loadFunction('removeCheck', dependencies)
  remove('one')
  assert.equal(form.value.checks.length, 2)
  canConfigure.value = true
  props.savePending = true
  remove('one')
  assert.equal(form.value.checks.length, 2)
  props.savePending = false
  remove('one')
  assert.deepEqual(form.value.checks, [{ key: 'two' }])
  assert.deepEqual(expandedCheckKeys.value, [])
})

test('general callback checks save without parsing expected variables as JSON', async () => {
  let saved
  const form = { value: {
    key: 'rule', name: 'Callback', mock_config_id: 1,
    correlation: { source: 'business_json', field: '$.id', expected: { cache_key: 'callback_run_id' } },
    event_id_source: 'business_json', event_id_field: '$.header.event_id', checks: [{ type: 'field', general_editor: true,
      expected_text: 'not-json', assertions: [{ value: { value: 'p_is_equal_to',
        parameter: [{ f: 'actual', v: '' }, { f: 'expect', v: '${{expected}}' }] } }] }],
  } }
  const warnings = []
  const save = loadFunction('saveRule', {
    form, canConfigure: { value: true }, configurationBlock: { value: '' },
    props: { rules: [] }, stepKey: { value: 'step-1' }, triggerLabel: { value: 'API' },
    scopedRules: { value: [] }, callbackRuleName, Message: { warning: message => warnings.push(message) },
    persist: async rules => { saved = rules; return true }, editorVisible: { value: true },
  })
  await save()
  assert.equal(warnings.length, 0)
  assert.equal(saved[0].checks[0].assertions[0].value.parameter[1].v, '${{expected}}')
  assert.equal('general_editor' in saved[0].checks[0], false)
  form.value.checks[0].assertions = []
  saved = undefined
  await save()
  assert.equal(saved, undefined)
  assert.equal(warnings.length, 1)
})

test('Case-level saving serializes submissions and survives switching the active trigger', async () => {
  let complete
  let requests = 0
  const pending = { value: false }
  const pageData = { record: { callback_checks: [] } }
  const save = loadFunction('saveCallbackRules', {
    callbackSavePending: pending, ensureCaseEditable: () => true, apiCaseId: { value: 1 },
    selectedCaseVersionDetail: { value: null }, caseEditLocked: { value: false }, pageData,
    saveCase: () => { requests++; return new Promise(resolve => { complete = resolve }) },
  }, pageAst)
  const first = save([{ key: 'first' }])
  assert.equal(await save([{ key: 'second' }]), false)
  complete({ data: { callback_checks: [{ key: 'server-normalized' }] } })
  assert.equal(await first, true)
  assert.equal(requests, 1)
  assert.equal(pending.value, false)
  assert.deepEqual(pageData.record.callback_checks, [{ key: 'server-normalized' }])
})

test('late saves do not overwrite another version snapshot', async () => {
  let complete
  const version = { value: null }
  const pending = { value: false }
  const pageData = { record: { callback_checks: [{ key: 'snapshot' }] } }
  const save = loadFunction('saveCallbackRules', {
    callbackSavePending: pending, ensureCaseEditable: () => true, apiCaseId: { value: 1 },
    selectedCaseVersionDetail: version, caseEditLocked: { value: false }, pageData,
    saveCase: () => new Promise(resolve => { complete = resolve }),
  }, pageAst)
  const request = save([])
  version.value = { id: 2 }
  complete({ data: { callback_checks: [] } })
  assert.equal(await request, false)
  assert.equal(pending.value, false)
  assert.deepEqual(pageData.record.callback_checks, [{ key: 'snapshot' }])
})

test('rules remain isolated to the current step and configuration constraints match execution', () => {
  const rules = [{ key: 'a', trigger_step_key: 'step-1' }, { key: 'b', trigger_step_key: 'step-2' }]
  assert.deepEqual(callbackRulesForStep(rules, 1), [rules[0]])
  assert.deepEqual(callbackRulesForStep(rules, undefined), [])
  assert.equal(callbackConfigurationBlock({ id: 1 }, 1, 0), '')
  assert.equal(callbackConfigurationBlock({ id: 1 }, 1, 1), '')
  assert.match(callbackConfigurationBlock({ id: 1 }, 2, 1), /多个场景/)
  assert.match(callbackConfigurationBlock({ id: 1 }, 1, 2), /关闭失败重试/)
  assert.match(callbackConfigurationBlock({ id: 1, execution_config: { is_recovery: true } }, 1, 1), /最终恢复/)
})

test('saving automatically binds the step and preserves rules from other steps', async () => {
  const other = { key: 'other', trigger_step_key: 'step-2' }
  const rules = [{ key: 'edited', trigger_step_key: 'step-1' }, other]
  let saved
  const editorVisible = { value: true }
  await loadFunction('saveRule', {
    canConfigure: { value: true }, configurationBlock: { value: '' },
    form: { value: { key: 'edited', name: '回调检查', trigger_step_key: 'step-999', mock_config_id: 1,
      correlation: { source: 'business_json', field: '$.header.event_id', expected: { cache_key: 'callback_run_id' } },
      event_id_source: 'business_json', event_id_field: '$.header.event_id',
      checks: [{ key: 'field', type: 'field', operator: 'equals', expected_text: '200' }] } },
    stepKey: { value: 'step-1' }, props: { rules }, editorVisible,
    persist: async value => { saved = value; return true },
    Message: { warning: message => assert.fail(message) },
  })()
  assert.equal(saved[0].trigger_step_key, 'step-1')
  assert.equal(saved[0].checks[0].expected, 200)
  assert.equal(saved[1], other)
  assert.equal(editorVisible.value, false)
})

test('invalid trigger cannot save and removing an unseen rule cannot affect another step', async () => {
  const persist = () => assert.fail('must not write')
  let message
  await loadFunction('saveRule', {
    canConfigure: { value: false }, configurationBlock: { value: '请关闭失败重试' },
    Message: { warning: value => { message = value } }, persist,
  })()
  assert.match(message, /失败重试/)
  await loadFunction('removeRule', {
    scopedRules: { value: [{ key: 'current' }] }, persist,
  })('another-step')
})

test('configuration has no duplicate result tabs and archived checks are displayed in assertion results', () => {
  assert.doesNotMatch(panel, /title="验证规则"|title="回调结果"|default-active-key="config"/)
  assert.match(panel, /<ApiCaseCallbackAssertions/)
  assert.match(panel, /:runs="archivedResults \|\| \[\]"/)
  assert.match(read('index.vue'), /view="results"/)
  assert.match(read('index.vue'), /callback_results: callbackResultsForScenario/)
})

test('basic callback form has no name, enabled, or trigger inputs and advanced fields are collapsed', () => {
  const { descriptor } = parse(panel)
  const template = descriptor.template.content
  assert.doesNotMatch(template, /v-model="form\.(enabled|name|trigger_step_key)"/)
  const basic = template.slice(template.search(/<a-form\s+:model="form"/), template.search(/<a-collapse\s+v-model:active-key="advancedKeys"/))
  for (const label of ['Mock 接口', '关联字段', '等待超时（秒）', '断言内容'])
    assert.ok(basic.includes(label))
  for (const field of ['form.correlation.source', 'form.correlation.expected.cache_key',
    'form.event_id_source', 'form.event_id_field']) {
    assert.ok(basic.includes(field), `${field} must remain visible`)
    assert.equal(template.split(`v-model="${field}"`).length - 1, 1)
  }
  for (const field of ['form.events.mode',
    'form.response_mode', 'form.observation_seconds', 'form.delivery_policy'])
    assert.ok(!basic.includes(field), `${field} belongs to advanced configuration`)
  assert.match(panel, /advancedKeys.value = \[\]/)
  assert.match(panel, /保存并启用/)
  assert.match(panel, /旧规则未启用/)
})

test('required matching and event fields cannot be saved empty; basic values do not mark advanced settings custom', () => {
  const valid = { mock_config_id: 1, correlation: { source: 'business_json', field: '$.event.run',
    expected: { cache_key: 'custom_run' } }, event_id_source: 'envelope_json', event_id_field: '$.id' }
  assert.equal(callbackRequiredConfigError(valid), '')
  assert.equal(hasCustomCallbackSettings(valid), false)
  const paths = ['mock_config_id', 'correlation.source', 'correlation.field',
    'correlation.expected.cache_key', 'event_id_source', 'event_id_field']
  for (const path of paths) {
    const copy = structuredClone(valid), parts = path.split('.')
    const key = parts.pop()
    const parent = parts.reduce((value, part) => value[part], copy)
    parent[key] = ''
    assert.notEqual(callbackRequiredConfigError(copy), '', `${path} is required`)
  }
  assert.match(panel, /默认 callback_run_id\s+由平台每次执行自动生成/)
})

test('automatic names are readable, unique, and stay within the schema limit', () => {
  assert.equal(callbackRuleName('写入状态', []), '写入状态回调断言')
  assert.equal(callbackRuleName('写入状态', [{ name: '写入状态回调断言' }]), '写入状态回调断言（2）')
  const long = '接口'.repeat(100)
  const first = callbackRuleName(long, [])
  const second = callbackRuleName(long, [{ name: first }])
  assert.equal(Array.from(first).length, 128)
  assert.ok(Array.from(second).length <= 128)
  assert.notEqual(first, second)
})

test('editing preserves advanced settings and existing names, while explicitly enabling legacy rules', async () => {
  const original = { key: 'legacy', name: '已有自定义名称', enabled: false, trigger_step_key: 'step-1',
    mock_config_id: 1, correlation: { source: 'header', field: 'X-Run', expected: { cache_key: 'custom_id' } },
    event_id_source: 'envelope_json', event_id_field: '$.id', timeout_seconds: 60,
    observation_seconds: 10, events: { mode: 'exact', count: 2 }, min_deliveries: 2,
    max_deliveries: 4, min_retry_interval_ms: 100, max_retry_interval_ms: 2000,
    delivery_policy: 'eventual_success', response_mode: 'strict', failure_status: 422,
    checks: [{ key: 'compact', type: 'json_compact', source: 'business_json' }] }
  let saved
  await loadFunction('saveRule', {
    canConfigure: { value: true }, configurationBlock: { value: '' }, form: { value: original },
    stepKey: { value: 'step-1' }, props: { rules: [original] }, editorVisible: { value: true },
    persist: async value => { saved = value[0]; return true },
    Message: { warning: message => assert.fail(message) },
  })()
  assert.equal(saved.enabled, true)
  assert.deepEqual(saved, { ...original, enabled: true })
  assert.equal(original.enabled, false)
  assert.equal(hasCustomCallbackSettings(original), true)
  assert.equal(hasCustomCallbackSettings({}), false)
})
