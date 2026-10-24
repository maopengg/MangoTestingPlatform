import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import postcss from 'postcss'
import less from 'less'

const filename = new URL('../../../src/views/timing/tasks/index.vue', import.meta.url).pathname
const source = readFileSync(filename, 'utf8')
const { descriptor } = parse(source, { filename })
const css = postcss.parse((await less.render(descriptor.styles[0].content)).css)
function properties(selector) {
  const values = {}
  css.walkRules(selector, rule => rule.walkDecls(decl => { values[decl.prop] = decl.value }))
  return values
}

test('shared create/edit form retains horizontal labels at one-column and two-column widths', () => {
  assert.match(descriptor.template.content, /:model="formModel" layout="horizontal" class="mango-task-form"/)
  const item = properties('.mango-task-form-group__fields :deep(.arco-form-item)')
  const label = properties('.mango-task-form-group__fields :deep(.arco-form-item-label-col)')
  const control = properties('.mango-task-form-group__fields :deep(.arco-form-item-wrapper-col)')
  assert.equal(item['flex-wrap'], 'nowrap')
  assert.equal(label.flex, '0 0 88px')
  assert.equal(label.width, '88px')
  assert.equal(control.flex, '1 1 0')
  assert.equal(control.width, '0')
  assert.equal(control['max-width'], 'none')
  assert.equal(control['min-width'], '0')
})

test('grouping, product linkage and form bindings remain intact and compile', () => {
  assert.match(source, /基础信息/)
  assert.match(source, /执行规则/)
  assert.match(source, /责任与通知/)
  assert.match(source, /@change="onFormProjectChange\(item.value\)"/)
  const script = compileScript(descriptor, { id: 'task-horizontal-form' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'task-horizontal-form', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})
