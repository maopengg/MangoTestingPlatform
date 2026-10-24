import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const base = '../../../../../src/views/data-factory/template/preview/'
const source = readFileSync(new URL(base + 'generatorDisplay.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } })
const exports = {}
new Function('exports', compiled.outputText)(exports)
const display = (type, config, extra = {}) => exports.getGeneratorDisplay({
  generator_type: type, generator_config: config, ...extra,
})

test('literal values and test methods show their content without config JSON', () => {
  assert.equal(display(1, { value: 0 }).text, '0')
  assert.equal(display(1, { value: false }).text, 'false')
  assert.equal(display(1, { value: '' }).text, '空字符串')
  assert.equal(display(1, { value: null }).text, 'null')
  assert.equal(display(1, {}).text, '未配置')
  assert.equal(display(13, { value: '${{tenant_id}}' }).text, '${{tenant_id}}')
})

test('automatic generators show actual parameters and dependency references', () => {
  assert.equal(display(0, { reason: '使用数据库默认值' }).text, '使用数据库默认值')
  assert.equal(display(3, { min: 0, max: 9000000000000000 }).text, '范围：0～9000000000000000')
  assert.equal(display(4, { min: 1, max: 10, precision: 0 }).text, '范围：1～10；小数位 0')
  assert.equal(display(2, { prefix: 'test_', length: 8 }).text, '自动生成；长度 8；前缀 test_')
  assert.equal(display(5, {}).text, '自动生成当前时间')
  assert.equal(display(6, { days: -1, hours: 0 }).text, '当前时间偏移：-1天，0小时')
  assert.equal(display(7, { dash: false }).text, '自动生成 UUID（不带连字符）')
  assert.equal(display('11', { dependency_entity_id: 42, field: 'code' }).text, '依赖实体 ID 42，取 code 字段')
})

test('enum labels preserve zero and false without replacing the stored selection', () => {
  assert.equal(display(9, { options: [{ label: '停用', value: 0 }], value: 0 }).text, '停用（0）')
  assert.equal(display(9, { values: [false, true], value: false }).text, 'false')
  assert.equal(display(9, { mode: 'random' }, { enum_values: [1, 2] }).text, '随机选择（2 项）')
  assert.equal(display(9, { value: 3, values: [1, 2] }).text, '3')
})

test('view-only field controls do not bind edits or serialize the whole config', () => {
  const page = readFileSync(new URL(base + 'index.vue', import.meta.url), 'utf8')
  const dialog = page.slice(page.indexOf(':title="`${entityRuleRecord'), page.indexOf('</a-modal>', page.indexOf(':title="`${entityRuleRecord')))
  assert.match(dialog, /生成方式（只读）/)
  assert.match(dialog, /生成配置（只读）/)
  assert.match(dialog, /readonly/)
  assert.doesNotMatch(dialog, /v-model=|@change=|@input=|formatGeneratorConfig/)
  assert.match(dialog, /getGeneratorDisplay\(record\)\.enum/)
})
