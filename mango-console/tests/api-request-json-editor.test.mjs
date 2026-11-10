import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
const filename = 'src/views/apitest/components/ApiRequestBodyEditor.vue'
const source = fs.readFileSync(filename, 'utf8')
test('JSON reuses display and edit drawer; template keeps textarea', () => {
  assert.match(source, /<a-textarea\s+v-if="local.body_config.source_type === 'template'"\s+v-model="local.body_config.body_text"/)
  assert.match(source, /<JsonDisplay\s+:data="jsonValueText"/)
  assert.match(source, /show-edit-button/)
  assert.match(source, /:show-drawer-button="false"/)
  assert.match(source, /@edit="jsonEditVisible = true"/)
  assert.match(source, /<MangoJsonEditDrawer/)
  assert.doesNotMatch(source, /show-toolbar|<MangoJsonEditor/)
  const {descriptor} = parse(source, {filename})
  const script = compileScript(descriptor, {id: 'request-json'})
  assert.deepEqual(compileTemplate({source: descriptor.template.content, filename, id: 'request-json', compilerOptions: {bindingMetadata: script.bindings}}).errors, [])
})
test('drawer validates before changing JSON and respects read-only mode', () => {
  const code = source.slice(source.indexOf('  function saveJsonValue('), source.indexOf('  function buildBodyConfig('))
  let saves = 0, errors = 0
  const readonly = {value: false}, jsonValueText = {value: '{}'}, jsonEditVisible = {value: true}
  const save = new Function('readonly', 'props', 'parseLosslessJson', 'Message', 'jsonValueText', 'jsonEditVisible', 'save', ts.transpileModule(code, {}).outputText + ';return saveJsonValue')(readonly, {}, JSON.parse, {error: () => errors++}, jsonValueText, jsonEditVisible, () => saves++)
  save('{bad')
  assert.equal(errors, 1)
  assert.equal(jsonEditVisible.value, true)
  assert.equal(jsonValueText.value, '{}')
  save('{"taskRef":"${{task_ref}}"}')
  assert.equal(saves, 1)
  assert.equal(jsonEditVisible.value, false)
  readonly.value = true
  save('{"changed":true}')
  assert.equal(saves, 1)
  assert.match(jsonValueText.value, /taskRef/)
})
test('display defaults preserve view-only consumers; edit is emitted from the shared toolbar', () => {
  const filename = 'src/components/display/JsonDisplay.vue'
  const display = fs.readFileSync(filename, 'utf8')
  assert.match(display, /showDrawerButton:\s*\{\s*type: Boolean,\s*default: true/)
  assert.match(display, /showEditButton:\s*\{\s*type: Boolean,\s*default: false/)
  assert.match(display, /v-if="showEditButton"[^>]+:disabled="editDisabled"[^>]+@click="emit\('edit'\)"/)
  const {descriptor} = parse(display, {filename})
  const script = compileScript(descriptor, {id: 'json-display-actions'})
  assert.deepEqual(compileTemplate({source: descriptor.template.content, filename, id: 'json-display-actions', compilerOptions: {bindingMetadata: script.bindings}}).errors, [])
})
