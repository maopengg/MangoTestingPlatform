import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import * as jsonc from 'jsonc-parser'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const assets = loadModule('src/components/business/ui-case-step-create.ts')
const lossless = loadModule('src/utils/lossless-json.ts', { 'jsonc-parser': jsonc })
const dto = loadModule('src/views/uitest/case/details/case-node-inputs.ts', { '@/components/business/ui-case-step-create': assets, '@/utils/lossless-json': lossless })
const long = '90071992547409930000'
const node = (type = 0) => ({ page_step_details_id: 0, type, page_step_details_data: [{ f: 'example', v: 'before' }, { f: 'locating', v: 'inherited' }], extra_metadata: { preserve: true } })
function setup(write = async () => ({ code: 200 })) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, writes = [], saved = [], messages = []
  const state = vue.reactive({ enabled: true, caseId: long, caseStepId: 0, pageStepId: 0, nodeId: 0, selection: 'canvas-0', data: [node()] }), user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const module = loadModule('src/views/uitest/case/details/composables/useCaseNodeInputs.ts', {
    vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@/components/business/ui-case-step-create': assets, '../case-node-inputs': dto,
    '@arco-design/web-vue': { Message: { success: value => messages.push(value) } }, '@/api/uitest/case-steps-detailed': { putUiCaseStepsDetailed: (...args) => { writes.push(args); return write(...args) } },
  })
  const scopes = []
  function instance() { const scope = vue.effectScope(); scopes.push(scope); return scope.run(() => module.useCaseNodeInputs({ ...Object.fromEntries(['enabled', 'caseId', 'caseStepId', 'pageStepId', 'nodeId', 'selection', 'data'].map(key => [key, () => state[key]])), saved: (...args) => saved.push(args) })) }
  const h = instance(); callbacks.mount.forEach(fn => fn())
  return { ...h, instance, state, user, permission, route, callbacks, writes, saved, messages, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) }, cleanup() { callbacks.unmount.forEach(fn => fn()); scopes.forEach(scope => scope.stop()); globalThis.document = previous } }
}
test('node inputs retain opaque metadata, inherited selectors and lossless numbers in a private snapshot', () => {
  const previous = [node()], number = lossless.parseLosslessJson('90071992547409930000')
  const result = dto.buildCaseNodeInputs(previous, 0, { 'example-ope_value': number, locating: 'changed', condition_value: false })
  assert.equal(lossless.stringifyLosslessJson(result[0].page_step_details_data[0].v), long); assert.equal(previous[0].page_step_details_data[0].v, 'before'); assert.equal(result[0].page_step_details_data[1].v, 'inherited'); assert.deepEqual(result[0].condition_value, { expect: false }); assert.deepEqual(result[0].extra_metadata, { preserve: true })
  assert.throws(() => dto.buildCaseNodeInputs([node(), node()], 0, {})); assert.throws(() => dto.buildCaseNodeInputs([], 0, {})); assert.throws(() => dto.buildCaseNodeInputs([node(9)], 0, {}))
})
test('all seven node types retain their existing request protocol and zero values', () => {
  for (const type of [0, 1, 4, 6]) assert.equal(dto.buildCaseNodeInputs([node(type)], 0, { 'example-ope_value': 0 })[0].page_step_details_data[0].v, 0)
  assert.deepEqual(dto.buildCaseNodeInputs([node(2)], 0, { sql_execute: [{ sql: 'select 1', key_list: 'example' }] })[0].page_step_details_data, [{ sql: 'select 1', key_list: 'example' }])
  assert.deepEqual(dto.buildCaseNodeInputs([node(3)], 0, { key: 'example', value: false })[0].page_step_details_data, [{ key: 'example', value: false }])
  assert.deepEqual(dto.buildCaseNodeInputs([node(5)], 0, { func: 'return 0' })[0].page_step_details_data, [{ func: 'return 0' }])
})
test('saving uses fixed zero/long IDs and values and emits original case/step provenance only after acceptance', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.cleanup)
  const draft = { 'example-ope_value': { value: 'before' } }, saving = h.save(draft); draft['example-ope_value'].value = 'after'; await flush()
  assert.equal(h.saving.value, true); assert.equal(await h.save({}), false); assert.equal(h.writes[0][1], long); assert.equal(h.writes[0][0].id, 0); assert.equal(h.writes[0][0].case_data[0].page_step_details_data[0].v.value, 'before'); assert.equal(h.saved.length, 0)
  pending.resolve({ code: 200 }); assert.equal(await saving, true); assert.deepEqual(h.saved[0][1], { caseId: long, caseStepId: 0, pageStepId: 0 }); assert.equal(h.saving.value, false)
})
test('physical lock survives node change, A-B-A and replacement component while old success cannot affect new selection', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.cleanup); const saving = h.save({}); await flush(); h.callbacks.unmount[0](); const replacement = h.instance(); h.state.nodeId = 2; h.state.nodeId = 0
  assert.equal(replacement.saving.value, true); assert.equal(await replacement.save({}), false); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.equal(h.saved.length, 0); assert.equal(h.messages.length, 0); assert.equal(replacement.saving.value, false); assert.equal(h.writes.length, 1)
})
test('identity/background/KeepAlive and selection changes reject old responses without clearing physical pending early', async () => {
  for (const change of [h => h.user.roleId++, h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.state.selection = 'other', h => { h.state.caseId = 2; h.state.caseId = long }, h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn())]) {
    const pending = deferred(), h = setup(() => pending.promise)
    try { const saving = h.save({}); await flush(); change(h); assert.equal(h.saving.value, true); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.equal(h.saved.length, 0); assert.equal(h.messages.length, 0) } finally { h.cleanup() }
  }
})
test('rejected writes preserve draft, expose local retry and release the physical lock', async t => {
  let fail = true; const h = setup(async () => ({ code: fail ? 403 : 200 })); t.after(h.cleanup)
  assert.equal(await h.save({ 'example-ope_value': 'after' }), false); assert.match(h.error.value, /草稿已保留/); assert.equal(h.state.data[0].page_step_details_data[0].v, 'before'); assert.equal(h.saving.value, false); fail = false; assert.equal(await h.save({ 'example-ope_value': 'after' }), true); assert.equal(h.error.value, '')
})
