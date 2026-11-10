import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/monitoring/task')
const record = (id = 1, product = 2) => ({ id, project_product: { id: product, name: 'Example product' }, name: 'Example task', description: null, test_env: 0, is_notice: 0, notice_group: { id: 0, name: 'Example notices' }, script_content: 'must-not-copy-from-row', audit: 'must-not-copy' })
function setup(overrides = {}) {
  const hooks = { activated: [], deactivated: [], unmounted: [] }, calls = [], messages = []
  const route = vue.reactive({ path: '/monitoring/task/index', fullPath: '/monitoring/task/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-token', selected_environment: 0 })
  const api = {
    getSystemNoticeName: async id => { calls.push(['options', id]); return { code: 200, data: [{ value: 0, label: 'Example notices' }] } },
    postMonitoringTask: async value => { calls.push(['create', value]); return { code: 200, msg: 'created' } },
    putMonitoringTask: async value => { calls.push(['update', value]); return { code: 200, msg: 'updated' } },
    ...overrides,
  }
  const h = harness('MonitoringTaskEditor', 'visible,recordId,saving,draft,title,noticeOptions,noticeLoading,noticeFailed,openCreate,openEdit,onProductChange,loadNotices,cancel,save,onEnter', {
    base,
    modules: {
      vue: { ...vue, onActivated: fn => hooks.activated.push(fn), onDeactivated: fn => hooks.deactivated.push(fn), onBeforeUnmount: fn => hooks.unmounted.push(fn) },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ environment_type: [{ key: 0, title: 'Example' }] }) },
      '@/api/system/notice_group': api,
      '@/api/monitoring/task': api,
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error'].map(key => [key, value => messages.push([key, value])])) },
    },
  })
  return { ...h, hooks, user, route, calls, messages }
}
function dispose(h) { h.hooks.unmounted.forEach(fn => fn()); h.close() }

test('create owns defaults, preserves product zero and edit/cancel/reopen do not share drafts', async () => {
  const h = setup(); h.openCreate(['project', 0]); await flush()
  assert.equal(h.draft.project_product, 0); assert.equal(h.draft.is_notice, 0); assert.equal(h.title.value, '新增')
  h.draft.name = 'old'; h.draft.script_content = 'old'; h.cancel(); h.openCreate(2)
  assert.equal(h.draft.name, ''); assert.equal(h.draft.script_content, '')
  h.openEdit(record()); assert.equal(h.recordId.value, 1); assert.equal(h.title.value, '编辑')
  assert.equal(h.draft.test_env, 0); assert.equal(h.draft.notice_group, 0); assert.equal(h.draft.description, null); assert.equal(h.draft.script_content, '')
  assert.equal('audit' in h.draft, false); h.cancel(); h.openCreate(); assert.equal(h.draft.notice_group, null); dispose(h)
})
test('separate editor instances have independent forms and options', async () => {
  const a = setup(), b = setup(); a.openEdit(record()); b.openCreate()
  a.draft.name = 'changed'; await flush(); assert.equal(b.draft.name, ''); assert.deepEqual(b.noticeOptions.value, []); dispose(a); dispose(b)
})
test('create validation preserves existing required fields and only submits whitelisted leaf IDs', async () => {
  const h = setup(); h.openCreate(); assert.equal(await h.save(), false); assert.equal(h.calls.length, 0)
  h.draft.project_product = [1, 2]; assert.equal(await h.save(), false)
  h.draft.name = ' Example '; assert.equal(await h.save(), false)
  h.draft.script_content = 'print("example")'; h.draft.test_env = 0; h.draft.notice_group = 0
  assert.equal(await h.save(), true)
  assert.deepEqual(h.calls.at(-1), ['create', { project_product: 2, name: ' Example ', description: '', test_env: 0, is_notice: 0, notice_group: 0, script_content: 'print("example")' }])
  assert.equal(h.visible.value, false); assert.deepEqual(h.events.at(-2), ['saved']); dispose(h)
})
test('edit leaves script untouched, preserves nullable fields and sends no row metadata', async () => {
  const h = setup(); const original = record(); h.openEdit(original); await flush(); h.draft.name = 'Changed'; h.draft.script_content = 'must-not-submit'
  assert.equal(await h.save(), true); const payload = h.calls.at(-1)[1]
  assert.deepEqual(payload, { id: 1, project_product: 2, name: 'Changed', description: null, test_env: 0, is_notice: 0, notice_group: 0 })
  assert.equal(original.name, 'Example task'); dispose(h)
})
test('cleared optional selects map to null, never to zero', async () => {
  const h = setup(); h.openEdit(record()); h.draft.test_env = ''; h.draft.notice_group = ''; await h.save()
  assert.equal(h.calls.at(-1)[1].test_env, null); assert.equal(h.calls.at(-1)[1].notice_group, null); dispose(h)
})
test('valid product change clears old notification selection and options; cleared product cannot request stale options', async () => {
  const h = setup(); h.openEdit(record()); await flush(); await h.onProductChange(3)
  assert.equal(h.draft.notice_group, null); assert.deepEqual(h.calls.at(-1), ['options', 3])
  const count = h.calls.length; await h.onProductChange(null)
  assert.equal(h.calls.length, count); assert.deepEqual(h.noticeOptions.value, []); dispose(h)
})
test('out-of-order options and previous finally cannot replace current product or loading', async () => {
  const jobs = [deferred(), deferred()]; let count = 0
  const h = setup({ getSystemNoticeName: () => jobs[count++].promise }); h.openCreate(2); const next = h.onProductChange(3)
  jobs[0].resolve({ code: 200, data: [{ value: 2, label: 'old' }] }); await flush()
  assert.equal(h.noticeLoading.value, true); assert.deepEqual(h.noticeOptions.value, [])
  jobs[1].resolve({ code: 200, data: [{ value: 3, label: 'new' }] }); await next
  assert.equal(h.noticeOptions.value[0].value, 3); assert.equal(h.noticeLoading.value, false); dispose(h)
})
test('product A-B-A uses request generations rather than only matching final product', async () => {
  const pending = deferred(); let count = 0
  const h = setup({ getSystemNoticeName: async () => ++count === 1 ? pending.promise : { code: 200, data: [{ value: 4, label: 'current' }] } })
  h.openCreate(2); void h.onProductChange(3); await h.onProductChange(2)
  pending.resolve({ code: 200, data: [{ value: 2, label: 'stale' }] }); await flush()
  assert.equal(h.noticeOptions.value[0].label, 'current'); dispose(h)
})
test('option failure preserves edit label and retry; malformed responses are errors', async () => {
  for (const bad of [null, { code: 300, data: [] }, { code: 200, data: [{ value: 'bad', label: 'bad' }] }]) {
    let failed = true; const h = setup({ getSystemNoticeName: async () => failed ? bad : { code: 200, data: [] } })
    h.openEdit(record()); await flush(); assert.equal(h.noticeFailed.value, true)
    assert.deepEqual(h.noticeOptions.value, [{ value: 0, label: 'Example notices' }])
    failed = false; await h.loadNotices(); assert.equal(h.noticeFailed.value, false)
    assert.equal(h.draft.notice_group, 0); assert.equal(h.noticeOptions.value[0].label, 'Example notices'); dispose(h)
  }
})
test('save failure keeps window and draft, unlocks retry; non-success code never closes', async () => {
  for (const reject of [true, false]) {
    let failed = true; const h = setup({ putMonitoringTask: async () => { if (failed && reject) throw new Error('offline'); return { code: failed ? 300 : 200, msg: 'ok' } } })
    h.openEdit(record()); assert.equal(await h.save(), false)
    assert.equal(h.visible.value, true); assert.equal(h.draft.name, 'Example task'); assert.equal(h.saving.value, false)
    failed = false; assert.equal(await h.save(), true); assert.equal(h.visible.value, false); dispose(h)
  }
})
test('physical save lock blocks double submit, cancel and reopen until network settles', async () => {
  const pending = deferred(); let count = 0
  const h = setup({ putMonitoringTask: () => { ++count; return pending.promise } }); h.openEdit(record()); const job = h.save()
  assert.equal(h.cancel(), false); assert.equal(await h.save(), false); h.openCreate(); assert.equal(h.recordId.value, 1)
  h.exposed.close(); h.openEdit(record(9)); assert.equal(h.visible.value, false); assert.equal(h.saving.value, true)
  pending.resolve({ code: 200, msg: 'ok' }); assert.equal(await job, false)
  assert.equal(count, 1); assert.equal(h.events.some(event => event[0] === 'saved'), false)
  assert.deepEqual(h.events, [['saving-change', true, 1], ['saving-change', false, 1]])
  h.openEdit(record(9)); assert.equal(h.recordId.value, 9); dispose(h)
})
test('identity/environment/route A-B-A close editor and invalidate late success and notices', async () => {
  for (const change of [h => { h.user.token = 'other'; h.user.token = 'fixture-token' }, h => { h.user.selected_environment = 2; h.user.selected_environment = 0 }, h => { h.route.fullPath = '/elsewhere'; h.route.fullPath = '/monitoring/task/index' }]) {
    const write = deferred(), options = deferred(); const h = setup({ putMonitoringTask: () => write.promise, getSystemNoticeName: () => options.promise })
    h.openEdit(record()); const job = h.save(); change(h)
    write.resolve({ code: 200, msg: 'must-not-show' }); options.resolve({ code: 200, data: [{ value: 1, label: 'stale' }] }); await job; await flush()
    assert.equal(h.visible.value, false); assert.deepEqual(h.noticeOptions.value, []); assert.equal(h.messages.length, 0)
    assert.equal(h.events.some(event => event[0] === 'saved'), false); dispose(h)
  }
})
test('KeepAlive and unmount close editor and ignore pending responses without resetting physical save early', async () => {
  for (const hook of ['deactivated', 'unmounted']) {
    const pending = deferred(); const h = setup({ putMonitoringTask: () => pending.promise }); h.openEdit(record()); const job = h.save()
    h.hooks[hook].forEach(fn => fn()); assert.equal(h.visible.value, false); assert.equal(h.saving.value, true)
    h.hooks.activated.forEach(fn => fn()); h.openCreate(); assert.equal(h.visible.value, false)
    pending.reject(new Error('offline')); await job; assert.equal(h.saving.value, false); assert.equal(h.messages.length, 0); dispose(h)
  }
})
test('invalid edit payload never opens a stale record', () => {
  const h = setup(); h.openEdit(record()); h.openEdit({ id: 1 }); assert.equal(h.visible.value, false); assert.equal(h.recordId.value, null); assert.equal(h.messages[0][0], 'error'); dispose(h)
})
test('Enter keeps submit behavior while IME composition, script newlines and tag editing are ignored', async () => {
  const h = setup(); h.openEdit(record()); let prevented = 0
  const event = { isComposing: false, keyCode: 13, target: { tagName: 'INPUT', closest: () => null }, preventDefault: () => prevented++ }
  h.onEnter({ ...event, isComposing: true }); h.onEnter({ ...event, keyCode: 229 })
  h.onEnter({ ...event, target: { tagName: 'TEXTAREA' } })
  h.onEnter({ ...event, target: { tagName: 'INPUT', closest: () => ({}) } })
  assert.equal(prevented, 0); assert.equal(h.calls.some(([type]) => type === 'update'), false)
  h.onEnter(event); await flush(); assert.equal(prevented, 1); assert.equal(h.calls.some(([type]) => type === 'update'), true); dispose(h)
})
test('parent and editor script/templates compile with narrow exposed operations', () => {
  for (const filename of [path.join(base, 'index.vue'), path.join(base, 'components/MonitoringTaskEditor.vue')]) {
    const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename }), script = compileScript(descriptor, { id: filename })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  }
})
