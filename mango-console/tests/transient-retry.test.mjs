import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { parse, compileTemplate } from '@vue/compiler-sfc'

function load(path) {
  const exports = {}
  const source = readFileSync(new URL('../src/' + path, import.meta.url), 'utf8')
  new Function('exports', ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText)(exports)
  return exports
}

test('empty selections stay empty and list/string settings normalize without losing values', () => {
  const { normalizeRetryConditions } = load('views/system/settings/config.ts')
  assert.deepEqual(normalizeRetryConditions([]), [])
  assert.deepEqual(normalizeRetryConditions('["http_500","assertion_failed"]'), ['http_500', 'assertion_failed'])
  assert.deepEqual(normalizeRetryConditions(['timeout', 'timeout']), ['timeout'])
  assert.deepEqual(normalizeRetryConditions('invalid'), [])
})

test('settings use registered multi-select options, direct save and the existing boolean switch', () => {
  const path = new URL('../src/views/system/settings/index.vue', import.meta.url)
  const source = readFileSync(path, 'utf8')
  const template = parse(source).descriptor.template.content
  assert.deepEqual(compileTemplate({ source: template, filename: path.pathname, id: 'settings' }).errors, [])
  assert.match(template, /v-else-if="item.key === API_TRANSIENT_RETRY_CONDITIONS_KEY"[\s\S]*?multiple[\s\S]*?enumStore.api_transient_retry_condition[\s\S]*?@change="saveItem\(group, item\)"/)
  assert.match(source, /if \(item.key === API_TRANSIENT_RETRY_CONDITIONS_KEY\) return normalizeRetryConditions\(item.value\)/)
  assert.match(source, /API_TRANSIENT_RETRY_HELP/)
})

test('default assertions use registered protocol checks and preserve empty selection', () => {
  const source = readFileSync(new URL('../src/views/system/settings/index.vue', import.meta.url), 'utf8')
  const template = parse(source).descriptor.template.content
  assert.match(template, /<a-cascader\s+v-else-if="item.key === API_DEFAULT_ASSERTION_CHECKS_KEY"[\s\S]*?multiple[\s\S]*?:options="defaultAssertionOptions"[\s\S]*?@change="saveItem\(group, item\)"/)
  assert.match(template, /:path-mode="false"/)
  assert.match(template, /:check-strictly="false"/)
  assert.equal((source.match(/if \(item.key === API_DEFAULT_ASSERTION_CHECKS_KEY\) return normalizeRetryConditions\(item.value\)/g) || []).length, 2)
  const { API_DEFAULT_ASSERTION_HELP } = load('views/system/settings/config.ts')
  assert.match(API_DEFAULT_ASSERTION_HELP, /默认关闭/)
  assert.match(API_DEFAULT_ASSERTION_HELP, /无断言的有效响应可能直接通过/)
  const store = readFileSync(new URL('../src/store/modules/get-enum.ts', import.meta.url), 'utf8')
  assert.match(store, /'api_default_assertion_check'/)
  assert.match(store, /this.api_default_assertion_check.length > 0/)
})

test('protocol cascader groups options without changing saved leaf keys', () => {
  const { buildDefaultAssertionOptions } = load('views/system/settings/config.ts')
  const input = [
    { key: 'http_status', title: 'HTTP / SSE 等 · 状态码为 2xx' },
    { key: 'websocket_close', title: 'WebSocket · 正常关闭（1000 / 1001）' },
    { key: 'websocket_handshake', title: 'WebSocket · 握手及协议状态正常' },
  ]
  const options = buildDefaultAssertionOptions(input)
  assert.deepEqual(options.map(option => option.label), ['HTTP / SSE 等', 'WebSocket'])
  assert.deepEqual(options[1].children, [
    { value: 'websocket_close', label: '正常关闭（1000 / 1001）' },
    { value: 'websocket_handshake', label: '握手及协议状态正常' },
  ])
  assert.deepEqual(options.flatMap(option => option.children.map(child => child.value)), input.map(option => option.key))
  assert.deepEqual(buildDefaultAssertionOptions([]), [])
  assert.deepEqual(buildDefaultAssertionOptions([{ key: 'future_check', title: '新增检查' }])[0].children,
    [{ value: 'future_check', label: '新增检查' }])
})

test('last retry decides each scenario without hiding failures in different scenarios', () => {
  const { latestScenarioAttempts } = load('views/apitest/case/details/execution-results.ts')
  const first = { id: 1, parameter_id: 2, retry_index: 1, status: 0 }
  const retry = { id: 1, parameter_id: 2, retry_index: 2, status: 1, automatic_retry_condition: 'http_503' }
  const other = { id: 1, parameter_id: 3, retry_index: 1, status: 0 }
  const input = [first, retry, other]
  assert.deepEqual(latestScenarioAttempts(input), [retry, other])
  assert.equal(input.length, 3)
  assert.deepEqual(latestScenarioAttempts([retry, first]), [retry])
  assert.equal(latestScenarioAttempts([{ id: 1, status: 0 }, { id: 1, status: 1 }]).length, 2)
  const page = readFileSync(new URL('../src/views/apitest/case/details/index.vue', import.meta.url), 'utf8')
  assert.match(page, /const steps = latestScenarioAttempts\(normalizeExecutionResultSteps\(resultData\)\)/)
  assert.match(page, /const stepResults = latestScenarioAttempts/)
  const header = readFileSync(new URL('../src/views/apitest/case/details/components/ApiCaseScenarioHeader.vue', import.meta.url), 'utf8')
  assert.match(header, /automatic_retry_condition/)
  assert.match(header, /自动重试后/)
})
