import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'

const source = readFileSync(new URL('../../../src/components/DataFactory/fieldTags.ts', import.meta.url), 'utf8')
const exports = {}
new Function('exports', ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText)(exports)
const { getFieldTag } = exports

test('boolean metadata uses numeric classification keys and preserves missing values', () => {
  for (const [field, no, yes] of [
    ['nullable', '必填', '可空'],
    ['primary_key', '普通', '主键'],
    ['autoincrement', '非自增', '自增'],
  ]) {
    const off = getFieldTag({ [field]: false }, field)
    const on = getFieldTag({ [field]: true }, field)
    assert.equal(off.label, no)
    assert.equal(off.key, 0)
    assert.equal(on.label, yes)
    assert.equal(on.key, 1)
    assert.ok(on.options.some(option => option.key === on.key))
    assert.equal(getFieldTag({}, field).label, '-')
    assert.equal(getFieldTag({}, field).key, null)
  }
})

test('database and platform types share stable category keys and full original labels', () => {
  const record = { db_type: 'VARCHAR(1024)', platform_type: 'string' }
  const db = getFieldTag(record, 'db_type')
  const platform = getFieldTag(record, 'platform_type')
  assert.equal(db.label, 'VARCHAR(1024)')
  assert.equal(platform.label, 'string')
  assert.equal(db.key, platform.key)
  assert.ok(db.options.some(option => option.key === db.key))
  assert.equal(getFieldTag({ platform_type: 'future_type' }, 'platform_type').options
    .some(option => option.key === 'future_type'), false)
  assert.equal(getFieldTag({}, 'db_type').key, null)
})

test('field tags reuse global colors and small size without overriding tag colors or dimensions', () => {
  const filename = new URL('../../../src/components/display/DataFactoryFieldTag.vue', import.meta.url).pathname
  const content = readFileSync(filename, 'utf8')
  const { descriptor, errors } = parse(content, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'field-tag' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'field-tag', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  assert.deepEqual(compileStyle({ source: descriptor.styles[0].content, filename,
    id: 'field-tag', scoped: true }).errors, [])
  assert.match(content, /getEnumTagColor\(tag.value.options, tag.value.key, enumStore.colors\)/)
  assert.match(content, /size="small"/)
  assert.match(content, /a-tooltip :content="tag.label"/)
  assert.doesNotMatch(descriptor.styles[0].content, /(?:background|color|height|font-size):/)
})

test('both field-rule dialogs use the shared tag for all five metadata columns', () => {
  for (const path of ['entity/index.vue', 'template/preview/index.vue']) {
    const page = readFileSync(new URL('../../../src/views/data-factory/' + path, import.meta.url), 'utf8')
    assert.match(page, /\['nullable', 'primary_key', 'autoincrement', 'db_type', 'platform_type'\].includes\(item.key\)/)
    assert.match(page, /<DataFactoryFieldTag :record="record" :field="item.key"/)
    assert.doesNotMatch(page, /enumStore.colors\[record\.(nullable|primary_key|autoincrement|platform_type)\]/)
  }
})
