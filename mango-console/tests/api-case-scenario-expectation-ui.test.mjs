import test from 'node:test'
import assert from 'node:assert/strict'
import { harness, step, scenario } from './helpers/case-details-harness.mjs'

test('new scenarios inherit defaults with advanced expectations collapsed', () => {
  const h = harness('ApiCaseScenarioEditor', 'draft,advancedKeys,basicFormItems,protocolFormItems')
  h.exposed.open(step)
  assert.equal(h.draft.protocol_expectation_mode, 'auto')
  assert.deepEqual(h.advancedKeys.value, [])
  assert.equal(h.basicFormItems.some(item => String(item.key).startsWith('protocol_expectation_')), false)
  assert.equal(h.protocolFormItems.length, 2)
  h.close()
})

test('editing explicit expectations reveals them and reopening resets expansion', () => {
  const h = harness('ApiCaseScenarioEditor', 'draft,advancedKeys,supportsHttpExpectation')
  h.exposed.open(step, 'edit', scenario({body_config: {protocol_expectation: {mode: 'codes', status_codes: [400, 422]}}}))
  assert.deepEqual(h.advancedKeys.value, ['protocol'])
  assert.equal(h.draft.protocol_expectation_codes, '400,422')
  h.exposed.open(step)
  assert.deepEqual(h.advancedKeys.value, [])
  h.exposed.open({...step, api_info: {...step.api_info, protocol_type: 'grpc'}})
  assert.equal(h.supportsHttpExpectation.value, false)
  h.close()
})
