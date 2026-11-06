import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const page = readFileSync(new URL('../src/views/system/sql-execution/index.vue', import.meta.url), 'utf8')
const config = readFileSync(new URL('../src/views/system/sql-execution/config.ts', import.meta.url), 'utf8')
const factory = readFileSync(new URL('../src/views/data-factory/execution/index.vue', import.meta.url), 'utf8')
const template = readFileSync(new URL('../src/views/data-factory/template/preview/index.vue', import.meta.url), 'utf8')
const previewConfig = readFileSync(new URL('../src/views/data-factory/template/preview/config.ts', import.meta.url), 'utf8')

test('统一记录页保留路由并展示跨数据源语义', () => {
  assert.match(page, /title="数据源执行记录"/)
  assert.match(page, /<h4>执行内容<\/h4>/)
  assert.match(page, /detail\.record\.datasource_type_name/)
  assert.match(config, /key: 'datasource_type'/)
  assert.match(config, /key: 'database_id'/)
})

test('类型筛选复用多选协议并保留截断提示', () => {
  assert.match(config, /enableMultiSelectSearch\(conditionItems\)/)
  assert.match(page, /:multiple="item\.multiple"/)
  assert.match(page, /item\.multiple \? \[\] : ''/)
  assert.match(page, /仅保留前 1000 个字符/)
})

test('工厂详情复用关联记录而非前端新增审计', () => {
  assert.match(factory, /title="数据源执行记录"/)
  assert.match(factory, /detail\.sql_executions/)
  assert.doesNotMatch(page, /v-permission/)
})

test('ES规则复用模板更新接口并在执行详情显示结果', () => {
  assert.match(template, /title="关联ES清理规则"/)
  assert.match(template, /cleanup_resources: rules/)
  assert.match(template, /仅对后续执行生效/)
  assert.match(factory, /title="关联资源清理"/)
  assert.match(factory, /state\.sql_cleaned/)
  assert.match(previewConfig, /document_id_field: 'id'/)
  assert.match(previewConfig, /不传\/null才用SQL主键/)
})
