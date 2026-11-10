import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/system/settings')
const row = (id = 'profile-1') => ({ id, name: 'Example', provider_type: 'openai_compatible', base_url: 'https://example.com/v1', model: 'example-model', api_key: '__KEEP_SECRET__', timeout: 120, enabled: true })
function setup(modelValue = [row()]) {
  const warnings = []
  return { ...harness('EvaluationAiProfilesEditor', 'draft,modelError,add,remove,save', { base, props: { modelValue, loading: false }, modules: { '@arco-design/web-vue': { Message: { warning: value => warnings.push(value) } } } }), warnings }
}
test('AI profile boundary copies finite fields, preserves masked key and rejects invalid identifiers', t => {
  const h = setup(); t.after(h.close); const m = h.load('evaluation-profiles.ts')
  assert.deepEqual(m.copyEvaluationAiProfiles([{ ...row(), audit: 'omit' }]), [row()])
  for (const value of [null, {}, [row(), row()], [{ ...row(), id: '__system_default__' }], [{ ...row(), id: '' }], [{ ...row(), enabled: 'false' }]]) assert.throws(() => m.copyEvaluationAiProfiles(value))
  assert.deepEqual(m.evaluationAiProfilePayload([{ ...row(), enabled: false, api_key: '' }]), [{ ...row(), enabled: false, api_key: '' }])
})
test('AI payload validates existing backend endpoint, time and count constraints', t => {
  const h = setup(); t.after(h.close); const m = h.load('evaluation-profiles.ts')
  for (const value of [undefined, 0, 3601, 1.5, NaN]) assert.throws(() => m.evaluationAiProfilePayload([{ ...row(), timeout: value }]))
  for (const base_url of ['javascript:alert(1)', 'https://user:password@example.com', 'https://example.com#fragment', 'invalid']) assert.throws(() => m.evaluationAiProfilePayload([{ ...row(), base_url }]))
  for (const patch of [{ name: '' }, { model: '' }, { api_key: '' }, { name: 'x'.repeat(101) }, { provider_type: 'unknown' }]) assert.throws(() => m.evaluationAiProfilePayload([{ ...row(), ...patch }]))
  assert.throws(() => m.copyEvaluationAiProfiles(Array.from({ length: 51 }, (_, i) => row(`profile-${i}`))))
})
test('AI drafts and emitted snapshots are independent from props; external rollback replaces draft', async t => {
  const h = setup(); t.after(h.close); h.draft.value[0].name = 'Edited'; assert.equal(h.props.modelValue[0].name, 'Example')
  h.save(); const payload = h.events[0][1]; assert.equal(payload[0].name, 'Edited'); assert.deepEqual(Object.keys(payload[0]).sort(), Object.keys(row()).sort())
  h.draft.value[0].name = 'Later'; assert.equal(payload[0].name, 'Edited')
  h.props.modelValue = payload; await flush(); assert.equal(h.draft.value[0].name, 'Later')
  h.props.modelValue = [row('other')]; await flush(); assert.equal(h.draft.value[0].id, 'other'); assert.equal(h.draft.value[0].api_key, '__KEEP_SECRET__')
})
test('broken incoming list cannot be silently saved as empty and corrected props recover', async t => {
  const h = setup(null); t.after(h.close); assert.ok(h.modelError.value); h.save(); h.add(); assert.equal(h.events.length, 0); assert.equal(h.draft.value.length, 0)
  h.props.modelValue = []; await flush(); assert.equal(h.modelError.value, ''); h.save(); assert.deepEqual(h.events[0], ['update:modelValue', []])
})
test('loading blocks add, removal and save; validation failure retains local draft', t => {
  const h = setup(); t.after(h.close); h.props.loading = true; h.remove(0); h.add(); h.save(); assert.equal(h.draft.value.length, 1); assert.equal(h.events.length, 0)
  h.props.loading = false; h.draft.value[0].timeout = undefined; h.save(); assert.equal(h.events.length, 0); assert.equal(h.draft.value[0].timeout, undefined); assert.ok(h.warnings.length)
  h.draft.value[0].timeout = 1; h.save(); assert.equal(h.events[0][1][0].timeout, 1)
})
test('AI removal is local until explicit save and 50 profiles is the existing limit', t => {
  const h = setup(Array.from({ length: 50 }, (_, i) => row(`profile-${i}`))); t.after(h.close)
  h.add(); assert.equal(h.draft.value.length, 50); h.remove(-1); assert.equal(h.draft.value.length, 50)
  h.remove(0); assert.equal(h.props.modelValue.length, 50); assert.equal(h.events.length, 0); h.add(); assert.equal(h.draft.value.length, 50); assert.ok(h.draft.value[49].id)
})
test('AI editor script, template and styles compile', async () => {
  const filename = path.join(base, 'components/EvaluationAiProfilesEditor.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'evaluation-settings' })
  assert.deepEqual(compileTemplate({ filename, id: 'evaluation-settings', source: descriptor.template.content, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ filename, id: 'evaluation-settings', source: style.content, scoped: style.scoped })).errors, [])
})
