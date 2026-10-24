import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../../../../src/views/data-factory/entity/index.vue', import.meta.url).pathname
const source = readFileSync(filename, 'utf8')
const start = source.indexOf('v-model:visible="entityVisible"')
const dialog = source.slice(start, source.indexOf('</a-modal>', start))

test('entity creation and editing share a grouped horizontal form', () => {
  assert.match(dialog, /entityForm.id \? '编辑实体' : '新增实体'/)
  assert.match(dialog, /layout="horizontal"/)
  assert.doesNotMatch(dialog, /layout="vertical"/)
  assert.equal((dialog.match(/class="mango-entity-form-section"/g) || []).length, 3)
  for (const heading of ['基础信息', '字段与操作', '清理与同步']) {
    assert.match(dialog, new RegExp(`>${heading}</h3>`))
  }
  for (const field of ['project_product', 'module', 'datasource_alias', 'table_name', 'name',
    'primary_key', 'unique_key', 'create_type', 'delete_type', 'cleanup_order', 'description']) {
    assert.equal((dialog.match(new RegExp(`v-model="entityForm.${field}"`, 'g')) || []).length, 1)
  }
})

test('dialog keeps asynchronous controls, standard switch and full-width long fields', () => {
  assert.match(dialog, /:on-before-ok="saveEntity"/)
  assert.match(dialog, /:ok-loading="entitySaving"/)
  assert.match(dialog, /:loading="entityTableLoading"/)
  assert.match(dialog, /:loading="entityTableRefreshLoading"/)
  assert.match(dialog, /<div class="mango-entity-form-full">\s*<a-form-item label="表名"/)
  assert.match(dialog, /<div class="mango-entity-form-full">\s*<a-form-item label="描述"/)
  assert.match(dialog, /<a-switch v-model="syncFieldsAfterSave" checked-text=/)
  assert.match(source, /repeat\(auto-fit, minmax\(min\(100%, 300px\), 1fr\)\)/)
})

test('entity dialog compiles with script bindings', () => {
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'entity-dialog' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'entity-dialog', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})
