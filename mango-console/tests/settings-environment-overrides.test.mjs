import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/system/settings')
const options = () => [{ key: 0, title: 'Zero' }, { key: 1, title: 'One' }]
function setup(props = {}) {
  return harness('EnvironmentNameOverrides', 'rows,modelError,addRow,removeRow,commit,optionsFor', { base, props: { modelValue: {}, options: options(), loading: false, ...props } })
}
test('environment zero remains valid and own updates preserve active local input', async t => {
  const h = setup(); t.after(h.close); h.addRow(); const row = h.rows.value[0]
  row.environment = 0; row.name = ' Display '; h.commit(); assert.deepEqual(h.events[0], ['update:modelValue', { 0: 'Display' }])
  h.props.modelValue = h.events[0][1]; await flush(); assert.equal(h.rows.value[0], row)
  h.props.modelValue = { 1: 'Saved' }; await flush(); assert.equal(h.rows.value[0].environment, 1); assert.equal(h.rows.value[0].name, 'Saved')
})
test('broken incoming values cannot be converted into an empty destructive save', async t => {
  const h = setup({ modelValue: null }); t.after(h.close); assert.ok(h.modelError.value); h.addRow(); h.commit(); assert.equal(h.events.length, 0)
  h.props.modelValue = { 0: null }; await flush(); assert.ok(h.modelError.value)
  h.props.modelValue = {}; await flush(); assert.equal(h.modelError.value, ''); h.addRow(); assert.equal(h.rows.value.length, 1)
})
test('cleared, unknown, duplicate and overlength rows do not publish', t => {
  const h = setup(); t.after(h.close); h.addRow(); const row = h.rows.value[0]; row.name = 'Name'
  for (const value of [undefined, null, '', 99]) { row.environment = value; h.commit(); assert.equal(h.events.length, 0) }
  row.environment = 0; row.name = 'x'.repeat(33); h.commit(); assert.equal(h.events.length, 0)
  row.name = 'Name'; h.addRow(); h.rows.value[1].environment = 0; h.rows.value[1].name = 'Duplicate'; h.commit(); assert.equal(h.events.length, 0)
  assert.equal(h.optionsFor(h.rows.value[1])[0].disabled, true)
})
test('deleting one saved override preserves incomplete drafts and unrelated saved values when options are unavailable', t => {
  const h = setup({ modelValue: { 0: 'Zero', 1: 'One' }, options: [] }); t.after(h.close)
  h.removeRow(h.rows.value[0].id); assert.deepEqual(h.events[0], ['update:modelValue', { 1: 'One' }])
  assert.deepEqual(h.props.modelValue, { 0: 'Zero', 1: 'One' })
})
test('option scalar types refresh without replacing local rows; loading blocks mutations', async t => {
  const h = setup({ modelValue: { 0: 'Zero' } }); t.after(h.close); const row = h.rows.value[0]
  h.props.options = options().map(option => ({ ...option, key: String(option.key) })); await flush(); assert.equal(h.rows.value[0], row); assert.equal(row.environment, '0')
  h.props.loading = true; h.removeRow(row.id); h.addRow(); h.commit(); assert.equal(h.rows.value.length, 1); assert.equal(h.events.length, 0)
})
test('environment editor script, template and styles compile', async () => {
  const filename = path.join(base, 'components/EnvironmentNameOverrides.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'environment-settings' })
  assert.deepEqual(compileTemplate({ filename, id: 'environment-settings', source: descriptor.template.content, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ filename, id: 'environment-settings', source: style.content, scoped: style.scoped })).errors, [])
})
