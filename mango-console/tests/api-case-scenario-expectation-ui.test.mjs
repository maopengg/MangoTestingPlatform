import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {harness, step, scenario} from './helpers/case-details-harness.mjs'

test('scenario dialogs have no protocol fields and new scenarios inherit by omission', async () => {
  const writes = []
  const h = harness('ApiCaseScenarioEditor', 'draft,formParameterItems,save', {api: {postApiCaseDetailedParameter: async value => {writes.push(value); return {msg: 'ok'}}}})
  h.exposed.open(step)
  h.draft.name = 'new'
  assert.equal(h.formParameterItems.some(item => String(item.key).startsWith('protocol_')), false)
  await h.save()
  assert.equal('protocol_expectation' in writes[0], false)
  assert.doesNotMatch(readFileSync('src/views/apitest/case/details/components/ApiCaseScenarioEditor.vue', 'utf8'), /高级配置|protocolFormItems/)
  h.close()
})

test('renaming an old scenario never overwrites its explicit protocol configuration', async () => {
  const writes = []
  const h = harness('ApiCaseScenarioEditor', 'draft,save', {api: {putApiCaseDetailedParameter: async value => {writes.push(value); return {msg: 'ok'}}}})
  const original = scenario({body_config: {protocol_expectation: {mode: 'codes', status_codes: [400, 422]}}})
  h.exposed.open(step, 'edit', original)
  h.draft.name = 'renamed'
  await h.save()
  assert.equal('protocol_expectation' in writes[0], false)
  assert.equal('body_config' in writes[0], false)
  assert.deepEqual(original.body_config.protocol_expectation.status_codes, [400, 422])
  h.close()
})
