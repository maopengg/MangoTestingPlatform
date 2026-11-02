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
