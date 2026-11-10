import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, scenario } from './helpers/case-details-harness.mjs'

test('JSON assertion drawer skips unchanged saves and supports validation and clearing', () => {
  const h = harness('ApiCaseAssertionPanel', 'openJsonAssertion,saveJsonAssertion,jsonEditVisible,jsonEditText,draft', {
    props: {item: scenario({ass_json_all: '{"code":0}'}), editLocked: false},
    modules: {'@/utils/lossless-json': {
      cloneLosslessJson: value => value == null ? value : JSON.parse(JSON.stringify(value)),
      parseLosslessJson: JSON.parse,
      stringifyLosslessJson: JSON.stringify,
    }},
  })
  h.openJsonAssertion()
  assert.equal(h.jsonEditVisible.value, true)
  h.saveJsonAssertion(h.jsonEditText.value)
  assert.equal(h.events.length, 0)
  h.openJsonAssertion()
  h.saveJsonAssertion('{bad')
  assert.equal(h.jsonEditVisible.value, true)
  assert.equal(h.events.length, 0)
  h.saveJsonAssertion('{"code":1}')
  assert.equal(h.events.at(-1)[0], 'save')
  assert.equal(h.events.at(-1)[1], 'ass_json_all')
  assert.equal(h.events.at(-1)[2], '{"code":1}')
  h.openJsonAssertion()
  h.saveJsonAssertion('')
  assert.equal(h.events.at(-1)[2], '')
  h.close()
})
test('schema JSON uses the same drawer and preserves its save target and generation action', () => {
  const h = harness('ApiCaseAssertionPanel', 'openJsonAssertion,saveJsonAssertion,jsonEditVisible,jsonEditText,draft', {
    props: {item: scenario({ass_json_all: '{"code":0}', ass_schema: '{"type":"object"}'}), editLocked: false, schemaLoading: false},
    modules: {'@/utils/lossless-json': {
      cloneLosslessJson: value => value == null ? value : JSON.parse(JSON.stringify(value)),
      parseLosslessJson: JSON.parse,
      stringifyLosslessJson: JSON.stringify,
    }},
  })
  h.openJsonAssertion('ass_schema')
  assert.equal(h.jsonEditText.value, '{"type":"object"}')
  h.saveJsonAssertion(h.jsonEditText.value)
  assert.equal(h.events.length, 0)
  h.openJsonAssertion('ass_schema')
  h.saveJsonAssertion('{bad')
  assert.equal(h.jsonEditVisible.value, true)
  h.saveJsonAssertion('{"type":"array"}')
  assert.equal(h.events.at(-1)[1], 'ass_schema')
  assert.equal(h.draft.value.ass_json_all, '{"code":0}')
  h.openJsonAssertion('ass_schema')
  h.saveJsonAssertion('')
  assert.equal(h.events.at(-1)[2], '')
  h.props.editLocked = true
  h.saveJsonAssertion('{}')
  assert.equal(h.events.length, 2)
  h.close()
})
test('schema display and generation compile with shared JSON components', () => {
  const filename = 'src/views/apitest/case/details/components/ApiCaseAssertionPanel.vue'
  const source = fs.readFileSync(filename, 'utf8')
  assert.match(source, /:data="draft.ass_schema \?\? ''"/)
  assert.match(source, /@click="emit\('generate-schema'\)"/)
  const {descriptor} = parse(source, {filename})
  const script = compileScript(descriptor, {id: 'schema-json'})
  assert.deepEqual(compileTemplate({source: descriptor.template.content, filename, id: 'schema-json', compilerOptions: {bindingMetadata: script.bindings}}).errors, [])
})
