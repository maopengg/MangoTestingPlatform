import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const path = 'src/views/report/execution-efficiency/'
test('efficiency page compiles and preserves the shared page shell', () => {
  const filename = path + 'index.vue'
  const source = readFileSync(filename, 'utf8')
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'execution-efficiency' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'execution-efficiency',
    compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  assert.match(source, /ProjectProductNavigationWorkbench[\s\S]*?contained-body/)
  assert.match(source, /version !== requestVersion/)
  assert.doesNotMatch(source, /setInterval|autoRefresh|IconRefresh|每15秒刷新|>刷新</)
  assert.match(source, /onBeforeUnmount[\s\S]*?clearOptions\(\)/)
  assert.doesNotMatch(source, /v-permission|hasPermission\(/)
})

test('efficiency layout separates live results, scopes date filters and uses container breakpoints', () => {
  const source = readFileSync(path + 'index.vue', 'utf8')
  assert.match(source, /v-if="section === 'timing'" label="统计时间"/)
  assert.match(source, /mango-efficiency-section mango-efficiency-live/)
  assert.match(source, /@container mango-efficiency \(max-width: 64rem\)/)
  assert.match(source, /:loading="!initialLoading && loading"/)
  assert.doesNotMatch(source, /观察当前等待与执行状态|API并发显示配置值|mango-efficiency-caption/)
  const config = readFileSync(path + 'config.ts', 'utf8')
  assert.equal((config.match(/col\('操作', 'actions', 160\)/g) || []).length, 4)
  assert.match(config, /export const efficiencyScrollWidths/)
})

test('missing timing remains a dash and subsecond requests remain visible', () => {
  const exports = {}
  const compiled = ts.transpileModule(readFileSync(path + 'config.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
  new Function('exports', 'require', compiled)(exports, () => ({ enableMultiSelectSearch() {} }))
  assert.equal(exports.duration(null), '—')
  assert.equal(exports.duration(undefined), '—')
  assert.equal(exports.duration(0), '0 ms')
  assert.equal(exports.duration(85), '85 ms')
  assert.equal(exports.duration(262000), '4分22秒')
  assert.deepEqual(exports.sectionOptions.map(item => item.value), ['queue', 'timing', 'anomalies'])
  assert.deepEqual(exports.rankingOptions.map(item => item.value), ['cases', 'reports'])
  assert.equal(exports.diagnosisTone('未检测到在线 API Worker'), 'danger')
  assert.equal(exports.diagnosisTone('报告并发限制'), 'warning')
  assert.equal(exports.diagnosisTone('正常执行'), 'neutral')
})

test('operational hierarchy uses shared tokens and keeps verbose rules out of the table', () => {
  const source = readFileSync(path + 'index.vue', 'utf8')
  assert.match(source, /a-popover title="统计口径"/)
  assert.match(source, /v-if="ranking === 'cases'"/)
  assert.match(source, /mango-efficiency-case-context/)
  assert.match(source, /var\(--m-warning\)/)
  assert.doesNotMatch(source, /#[a-f0-9]{3,8}\b|font-family:|transform:\s*scale|zoom:/i)
})
