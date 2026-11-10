import test from 'node:test'
import assert from 'node:assert/strict'
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
