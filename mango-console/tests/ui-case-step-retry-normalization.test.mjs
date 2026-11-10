import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'

const base = path.resolve('src/views/uitest/case/details'), filename = path.join(base, 'components/UiCaseStepRetryEditor.vue')
function setup(write = async () => ({ code: 200 }), switchMode = false) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, writes = [], messages = []
  const route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const h = harness(switchMode ? 'UiCaseStepUrlSwitch' : 'UiCaseStepRetryEditor', switchMode ? 'saving,error,enabled,save' : 'visible,saving,error,draft,changeVisible,save,closeEditor:close', {
    base, props: { caseId: 0, recordId: '90071992547409930000', retryCount: 2, value: 0 },
    api: { putUiCaseStepsDetailed: (...args) => { writes.push(args); return write(...args) } },
    modules: {
      vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/components/business/ui-case-step-create': loadModule('src/components/business/ui-case-step-create.ts'),
      '@arco-design/web-vue': { Message: { success: msg => messages.push(msg) } },
    },
  })
  return { ...h, writes, messages, callbacks, route, user, permission,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous },
  }
}
test('open/cancel/reopen owns draft, preserves zero and accepts latest server retry count', t => {
  const h = setup(); t.after(h.close); h.changeVisible(true); assert.equal(h.draft.value, 2); h.draft.value = 5
  assert.equal(h.props.retryCount, 2); h.closeEditor(); assert.equal(h.visible.value, false)
  h.props.retryCount = 0; h.changeVisible(true); assert.equal(h.draft.value, 0)
  h.props.retryCount = 3; assert.equal(h.draft.value, 0); h.closeEditor(); h.changeVisible(true); assert.equal(h.draft.value, 3)
})
test('invalid count and malformed IDs never issue writes', async t => {
  const h = setup(); t.after(h.close)
  for (const value of [-1, 0.5, undefined, NaN, Number.MAX_SAFE_INTEGER + 1]) {
    h.changeVisible(true); h.draft.value = value; assert.equal(await h.save(), false); assert.match(h.error.value, /整数/)
  }
  h.draft.value = 0; h.props.caseId = 'bad'; h.changeVisible(true); assert.equal(await h.save(), false); assert.match(h.error.value, /ID/)
  assert.deepEqual(h.writes, [])
})
test('invalid server count is visible and can be corrected without coercing false into zero', t => {
  const h = setup(); t.after(h.close)
  for (const value of [false, {}, '', -1]) {
    h.closeEditor(); h.props.retryCount = value; h.changeVisible(true); assert.match(h.error.value, /异常/); assert.equal(h.draft.value, undefined)
  }
})
test('save uses fixed IDs/count and physical lock, then emits finite result without editing props', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close); h.changeVisible(true); h.draft.value = 0
  const saving = h.save(); h.draft.value = 8; assert.equal(await h.save(), false); assert.equal(h.saving.value, true)
  assert.deepEqual(h.writes, [[{ id: '90071992547409930000', error_retry: 0 }, 0]])
  pending.resolve({ code: 200 }); assert.equal(await saving, true); assert.equal(h.saving.value, false)
  assert.deepEqual(h.events, [['saved', { caseId: 0, recordId: '90071992547409930000', retryCount: 0 }]])
  assert.equal(h.props.retryCount, 2); assert.equal(h.visible.value, false); assert.equal(h.messages.length, 1)
})
test('network and non-success responses retain editable draft and allow retry with local errors', async t => {
  let failure = 'network'; const h = setup(async () => { if (failure === 'network') throw Error('network'); return { code: failure ? 403 : 200 } }); t.after(h.close)
  h.changeVisible(true); h.draft.value = 4
  for (const next of ['network', 'response']) { failure = next; assert.equal(await h.save(), false); assert.equal(h.saving.value, false); assert.equal(h.draft.value, 4); assert.equal(h.visible.value, true); assert.match(h.error.value, /失败/); assert.deepEqual(h.events, []) }
  failure = ''; assert.equal(await h.save(), true); assert.equal(h.writes.length, 3)
})
test('cancel during save keeps lock until settlement and updates parent without reopening or toast', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close); h.changeVisible(true)
  const saving = h.save(); h.changeVisible(false); h.changeVisible(true); assert.equal(h.visible.value, false); assert.equal(await h.save(), false); assert.equal(h.saving.value, true)
  pending.resolve({ code: 200 }); assert.equal(await saving, true); assert.equal(h.events.length, 1); assert.deepEqual(h.messages, [])
  h.changeVisible(true); assert.equal(h.visible.value, true)
})
test('case/record/identity changes and A-B-A invalidate late success without releasing physical lock early', async () => {
  for (const change of [h => h.props.caseId = 2, h => h.props.recordId = 3, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1', h => { h.props.caseId = 2; h.props.caseId = 0 }]) {
    const pending = deferred(), h = setup(() => pending.promise)
    try {
      h.changeVisible(true); const saving = h.save(); change(h); assert.equal(h.visible.value, false); h.changeVisible(true); assert.equal(h.visible.value, false); assert.equal(h.saving.value, true)
      pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.equal(h.saving.value, false); assert.deepEqual(h.events, []); assert.deepEqual(h.messages, [])
    } finally { h.close() }
  }
})
test('background/KeepAlive/unmount invalidate success even after returning before settlement', async () => {
  for (const leave of [h => { h.visibility('hidden'); h.visibility('visible') }, h => { h.callbacks.deactivate.forEach(fn => fn()); h.callbacks.activate.forEach(fn => fn()) }, h => h.callbacks.unmount.forEach(fn => fn())]) {
    const pending = deferred(), h = setup(() => pending.promise)
    try { h.mount(); h.changeVisible(true); const saving = h.save(); leave(h); await flush(); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.deepEqual(h.events, []); assert.deepEqual(h.messages, []); assert.equal(h.visible.value, false) } finally { h.close() }
  }
})
test('parent applies emitted retry immutably to current rows/selection, retaining all other fields', () => {
  const first = { id: 0, name: 'Example step', error_retry: 1, case_data: [{ value: 'keep' }] }, other = { id: 1, error_retry: 8 }
  const caseSteps = { value: [first, other] }, uiCaseId = { value: 0 }
  const apply = method('applyCaseStepRetry', { caseSteps, uiCaseId, replaceCaseSteps: rows => caseSteps.value = rows }, path.join(base, 'index.vue'))
  apply({ caseId: 2, recordId: 0, retryCount: 3 }); assert.equal(caseSteps.value[0], first)
  apply({ caseId: 0, recordId: 0, retryCount: 3 }); assert.equal(first.error_retry, 1); assert.equal(caseSteps.value[0].error_retry, 3); assert.equal(caseSteps.value[1], other); assert.equal(caseSteps.value[0].case_data, first.case_data)
  apply({ caseId: 0, recordId: 0, retryCount: 4 }); assert.equal(caseSteps.value[1], other)
})
test('URL switch stays controlled until backend success, snapshots IDs and blocks duplicate requests', async t => {
  const pending = deferred(), h = setup(() => pending.promise, true); t.after(h.close)
  const saving = h.save(true); assert.equal(h.enabled.value, false); assert.equal(h.saving.value, true); assert.equal(await h.save(false), false)
  assert.deepEqual(h.writes, [[{ id: '90071992547409930000', switch_step_open_url: 1 }, 0]])
  pending.resolve({ code: 200 }); assert.equal(await saving, true)
  assert.deepEqual(h.events, [['saved', { caseId: 0, recordId: '90071992547409930000', value: 1 }]])
  h.props.value = 1; assert.equal(h.enabled.value, true); h.props.value = 0; assert.equal(h.enabled.value, false)
})
test('URL switch errors preserve server state, release loading and permit retry', async t => {
  let fail = true; const h = setup(async () => ({ code: fail ? 403 : 200 }), true); t.after(h.close)
  assert.equal(await h.save(true), false); assert.equal(h.enabled.value, false); assert.equal(h.saving.value, false); assert.match(h.error.value, /失败/); assert.deepEqual(h.events, [])
  fail = false; assert.equal(await h.save(true), true); assert.equal(h.error.value, '')
})
test('URL switch ignores malformed events and IDs without issuing writes', async t => {
  const h = setup(undefined, true); t.after(h.close)
  for (const next of [0, 1, '1', null, {}]) assert.equal(await h.save(next), false)
  h.props.recordId = 'bad'; assert.equal(await h.save(true), false); assert.match(h.error.value, /ID/); assert.deepEqual(h.writes, [])
})
test('URL switch late completion cannot update a replacement identity, record, background or cached page', async () => {
  for (const leave of [h => h.props.caseId = 2, h => h.props.recordId = 3, h => { h.user.userId++; h.user.userId-- }, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.fullPath += '&other=1', h => h.route.path = '/other', h => { h.visibility('hidden'); h.visibility('visible') }, h => { h.callbacks.deactivate.forEach(fn => fn()); h.callbacks.activate.forEach(fn => fn()) }, h => h.callbacks.unmount.forEach(fn => fn())]) {
    const pending = deferred(), h = setup(() => pending.promise, true)
    try { h.mount(); const saving = h.save(true); leave(h); assert.equal(h.saving.value, true); assert.equal(await h.save(true), false); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.equal(h.saving.value, false); assert.deepEqual(h.events, []); assert.deepEqual(h.messages, []) } finally { h.close() }
  }
})
test('parent URL update is immutable and scoped to current case and matching selection', () => {
  const row = { id: 0, switch_step_open_url: 0, name: 'Example' }, other = { id: 1, switch_step_open_url: 0 }, caseSteps = { value: [row, other] }, uiCaseId = { value: 0 }
  const apply = method('applyCaseStepUrl', { caseSteps, uiCaseId, replaceCaseSteps: rows => caseSteps.value = rows }, path.join(base, 'index.vue'))
  apply({ caseId: 1, recordId: 0, value: 1 }); assert.equal(caseSteps.value[0], row)
  apply({ caseId: 0, recordId: 0, value: 1 }); assert.equal(row.switch_step_open_url, 0); assert.equal(caseSteps.value[0].switch_step_open_url, 1); assert.equal(caseSteps.value[1], other)
})
test('retry component and integrating parent SFC compile, with local loading/errors and no old shared editor', async () => {
  for (const file of [filename, path.join(base, 'components/UiCaseStepUrlSwitch.vue'), path.join(base, 'index.vue')]) {
    const { descriptor, errors } = parse(readFileSync(file, 'utf8')); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: 'ui-case-retry' }), template = compileTemplate({ source: descriptor.template.content, filename: file, id: 'ui-case-retry', compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename: file, id: 'ui-case-retry', scoped: style.scoped, preprocessLang: style.lang })).errors, [])
  }
  const text = readFileSync(filename, 'utf8'); assert.match(text, /:loading="saving"/); assert.match(text, /role="alert"/)
  const parent = readFileSync(path.join(base, 'index.vue'), 'utf8'); assert.match(parent, /@saved="applyCaseStepRetry"/); assert.doesNotMatch(parent, /retryEditor|saveCaseStepRetry/)
})
