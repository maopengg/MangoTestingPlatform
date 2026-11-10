import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {parse, compileScript, compileTemplate} from '@vue/compiler-sfc'
import {harness, flush} from './helpers/case-details-harness.mjs'

function panel(value) {
  return harness('ApiCaseProtocolAssertions', 'form,leave,popupChange,changed,sourceOptions,checkOptions', {
    props: {scenarioId: 1, value, editLocked: false, saving: false},
    modules: {'@/store/modules/get-enum': {useEnum: () => ({api_default_assertion_check: [
      {key: 'http_status', title: 'HTTP / SSE 等 · 状态码为 2xx'},
      {key: 'mcp_result', title: 'MCP · isError 不为 true'},
    ]})}},
  })
}
test('default inherits; custom saves selected leaves only without a separate save button', () => {
  const h = panel()
  assert.equal(h.form.source, 'system')
  h.leave()
  assert.equal(h.events.length, 0)
  h.form.source = 'custom'
  h.form.checks = ['http_status']
  h.leave()
  assert.deepEqual(h.events, [['save', {mode: 'auto', status_codes: [], inherit_system: false, checks: ['http_status']}]])
  assert.equal(h.checkOptions.value[0].children[0].value, 'http_status')
  h.close()
})
test('mouseleave while popup is open waits until selection finishes', async () => {
  const h = panel()
  h.form.source = 'custom'
  await h.popupChange(true)
  h.leave()
  h.form.checks = ['mcp_result']
  assert.equal(h.events.length, 0)
  await h.popupChange(false)
  assert.equal(h.events[0][1].checks[0], 'mcp_result')
  h.close()
})
test('empty custom selection persists; readonly/loading prevent saves; failure leaves draft retryable', () => {
  const h = panel()
  h.form.source = 'custom'
  h.props.saving = true
  h.leave()
  assert.equal(h.events.length, 0)
  h.props.saving = false
  h.leave()
  assert.deepEqual(h.events[0][1].checks, [])
  h.props.editLocked = true
  h.form.checks = ['http_status']
  h.leave()
  assert.equal(h.events.length, 1)
  h.close()
})
test('switching scenarios drops unsaved source and selection; saved values make leave a no-op', async () => {
  const h = panel({inherit_system: false, checks: ['http_status']})
  h.leave()
  assert.equal(h.events.length, 0)
  h.form.checks = ['mcp_result']
  h.props.scenarioId = 2
  h.props.value = undefined
  await flush()
  assert.equal(h.form.source, 'system')
  assert.deepEqual(h.form.checks, [])
  h.leave()
  assert.equal(h.events.length, 0)
  h.close()
})
test('legacy explicit HTTP codes remain until user deliberately chooses a replacement', () => {
  const h = panel({mode: 'codes', status_codes: [400]})
  assert.equal(h.form.source, 'legacy')
  h.leave()
  assert.equal(h.events.length, 0)
  h.form.source = 'system'
  h.leave()
  assert.deepEqual(h.events[0][1], {mode: 'auto', status_codes: [], inherit_system: true, checks: []})
  h.close()
})
test('protocol assertion UI compiles and uses the shared settings cascade builder', () => {
  const filename = 'src/views/apitest/case/details/components/ApiCaseProtocolAssertions.vue'
  const source = fs.readFileSync(filename, 'utf8')
  assert.doesNotMatch(source, /保存协议断言|未选择任何检查项/)
  assert.match(source, /buildDefaultAssertionOptions/)
  const {descriptor} = parse(source, {filename})
  const script = compileScript(descriptor, {id: 'protocol-assertions'})
  assert.deepEqual(compileTemplate({source: descriptor.template.content, filename, id: 'protocol-assertions', compilerOptions: {bindingMetadata: script.bindings}}).errors, [])
})
