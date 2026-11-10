import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/timing/tasks')
const exports = {}
new Function('exports', ts.transpileModule(readFileSync(path.join(base, 'task-editor-records.ts'), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText)(exports)
const dto = exports
const row = (override = {}) => ({ id: 0, name: 'Example task', project_product: { id: 0, name: 'Product' }, module: { id: 0 },
  timing_strategies: [{ id: 0, name: 'Example timing' }], test_envs: [0], case_types: [1], execution_scenes: ['regression_test'],
  execution_scope: 'manual', case_people: { id: 0, name: 'Example owner' }, notice_group: { id: 0, name: 'Example notice' },
  api_concurrency_limit: null, report_retention_policy: 'all', ...override })
function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, writes = [], reads = [], messages = []
  const route = vue.reactive({ path: '/timing/tasks/index', fullPath: '/timing/tasks/index' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['timing.tasks:change'] })
  const enumStore = vue.reactive({
    environment_type: [{ key: 0, title: 'Test' }, { key: 2, title: 'Production' }], test_case_type: [{ key: 1, title: 'API' }, { key: 3, title: 'Disabled' }],
    automation_execution_scope: ['manual','module','full_product'].map(key => ({ key, title: key })),
    automation_execution_scene: ['unclassified','effectiveness_test','regression_test','stability_monitoring','production_regression'].map(key => ({ key, title: key })),
    api_case_scenario_tag: [{ key: 'regression_test', title: 'Regression' }], report_retention_policy: [{ key: 'all', title: 'All' }],
    getEnum: overrides.getEnum || (async () => {}),
  })
  const api = {
    getUserName: () => (overrides.getUserName || (async () => ({ code: 200, data: [{ key: '0', title: 'Current owner' }] })))(),
    getSystemTimingList: overrides.getSystemTimingList || (async () => ({ code: 200, data: [] })),
    getSystemTaskExecutionOptions: overrides.getSystemTaskExecutionOptions || (async () => ({ code: 200, data: { api_platform_limit: 8 } })),
    getSystemNoticeName: product => { reads.push(product); return (overrides.getSystemNoticeName || (async () => ({ code: 200, data: [{ value: 0, label: 'Notice option' }] })))(product) },
    postSystemTasks: payload => { writes.push(['post', payload]); return (overrides.save || (async () => ({ code: 200 })))(payload) },
    putSystemTasks: payload => { writes.push(['put', payload]); return (overrides.save || (async () => ({ code: 200 })))(payload) },
  }
  const h = harness('TaskEditorDialog', 'dialog,form,recordId,opened,saving,saveError,metadataErrors,metadataLoading,usersLoading,timingsLoading,noticesLoading,capacityLoading,platformLimit,availableUsers,availableTimings,availableNotices,productSelection,productChanged,scopeOptions,sceneOptions,supportsApi,classificationSummary,openCreate,openEdit,save,retryMetadata,closeEditor:close', { base, api,
    modules: {
      vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@/store/modules/get-enum': { useEnum: () => enumStore },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success','error'].map(key => [key, value => messages.push([key,value])])) },
    },
  })
  const shell = { visible: false, loading: false, show() { this.visible = true; return Promise.resolve(true) }, close() { this.visible = false; this.loading = false; return Promise.resolve(false) }, setConfirmLoading(value) { this.loading = value } }
  h.dialog.value = shell
  return { ...h, shell, writes, reads, messages, route, user, permission, callbacks, enumStore,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous },
  }
}

test('typed task drafts and payloads whitelist fields, copy arrays and preserve zero and long IDs', () => {
  const source = row({ id: '90071992547409939999', extra: true }), first = dto.readTaskEditorDraft(source), second = dto.createTaskEditorDraft()
  first.case_types.push(2); assert.deepEqual(source.case_types, [1]); assert.deepEqual(second.case_types, [])
  assert.equal(first.project_product, 0); assert.equal(first.module, 0); assert.equal(first.case_people, 0)
  const payload = dto.taskEditorPayload(first, source.id); assert.equal(payload.id, source.id); assert.equal('extra' in payload, false); assert.equal('status' in payload, false)
  first.case_types.push(3); assert.deepEqual(payload.case_types, [1,2])
  assert.equal(dto.taskEditorId([1,0]), 0); assert.throws(() => dto.taskEditorId(Number.MAX_SAFE_INTEGER + 1))
  for (const value of [null, [], { test_envs: {} }, { api_concurrency_limit: '2' }]) assert.throws(() => dto.readTaskEditorDraft(value))
})
test('normalizes legacy option protocols and keeps selected ID types without changing metadata', () => {
  const options = dto.readTaskEditorOptions([{ value: 0, label: 'Notice' }])
  assert.deepEqual(options, [{ key: 0, title: 'Notice' }])
  assert.deepEqual(dto.taskEditorSelectedOptions(options, ['0', 2], [{ key: 2, title: 'Old owner' }]), [{ key: '0', title: 'Notice' }, { key: 2, title: 'Old owner' }])
  assert.equal(options[0].key, 0)
  for (const value of [{ api_platform_limit: 0 }, { api_platform_limit: '8' }]) assert.throws(() => dto.readTaskEditorCapacity(value))
  assert.throws(() => dto.taskEditorResponse({ code: 403 })); assert.throws(() => dto.readTaskEditorOptions({}))
})
test('open/edit/cancel/reopen isolate draft, retain unavailable selected labels, normalize product path', async t => {
  const h = setup(); t.after(h.close); const source = row()
  await h.openEdit(source); assert.equal(h.opened.value, true); assert.equal(h.recordId.value, 0)
  assert.equal(h.availableUsers.value[0].key, 0); assert.equal(h.availableTimings.value[0].title, 'Example timing')
  assert.equal(h.availableNotices.value[0].title, 'Notice option'); assert.equal(h.classificationSummary.value.includes('Regression'), true)
  h.form.name = 'Draft'; h.form.timing_strategies.push(1); assert.equal(source.name, 'Example task'); assert.equal(source.timing_strategies.length, 1)
  h.closeEditor(); assert.equal(h.opened.value, false); assert.equal(h.form.case_people, null)
  await h.openCreate({ projectProduct: 0, module: 0 }); assert.equal(h.recordId.value, null); assert.equal(h.form.module, 0); assert.equal(h.form.execution_scope, 'manual'); assert.equal(h.form.name, '')
  h.productSelection.value = [5,6]; h.productChanged(); assert.equal(h.form.project_product, 6); assert.equal(h.form.module, null); assert.equal(h.form.notice_group, null)
  await flush(); assert.deepEqual(h.reads, [0,0,6])
})
test('create and edit use distinct fixed payload snapshots and reject double save', async t => {
  const pending = deferred(), h = setup({ save: () => pending.promise }); t.after(h.close)
  await h.openCreate({ projectProduct: 0, module: 0 }); Object.assign(h.form, dto.readTaskEditorDraft(row()))
  const saving = h.save(); assert.equal(h.saving.value, true); await h.save(); assert.equal(h.writes.length, 1)
  assert.equal(h.writes[0][0], 'post'); assert.equal(h.writes[0][1].status, 0); assert.equal(h.writes[0][1].is_notice, 0); assert.equal('id' in h.writes[0][1], false)
  h.form.test_envs.push(2); assert.deepEqual(h.writes[0][1].test_envs, [0]); pending.resolve({ code: 200 }); assert.equal(await saving, true)
  assert.equal(h.shell.visible, false); assert.deepEqual(h.events, [['saved']])
  await h.openEdit(row()); await h.save(); assert.equal(h.writes[1][0], 'put'); assert.equal(h.writes[1][1].id, 0); assert.equal('status' in h.writes[1][1], false)
})
test('required fields and concurrency validate locally and release confirm loading', async t => {
  const h = setup(); t.after(h.close); await h.openEdit(row()); h.form.timing_strategies = []; h.shell.loading = true
  assert.equal(await h.save(), false); assert.match(h.saveError.value, /策略/); assert.equal(h.shell.loading, false); assert.equal(h.writes.length, 0)
  h.form.timing_strategies = [0]; h.form.api_concurrency_limit = 9; await h.save(); assert.match(h.saveError.value, /1 到 8/)
  h.form.api_concurrency_limit = 1.5; await h.save(); assert.equal(h.writes.length, 0)
  h.form.api_concurrency_limit = null; h.form.execution_scope = 'module'; h.form.module = null; await h.save(); assert.match(h.saveError.value, /必须选择模块/)
})
test('cleared single selects normalize empty and undefined before validating required owners', async t => {
  const h = setup(); t.after(h.close); await h.openEdit(row())
  for (const empty of ['', undefined, null]) {
    h.form.case_people = empty; assert.equal(await h.save(), false); assert.match(h.saveError.value, /负责人/)
    assert.equal(h.availableUsers.value.some(option => option.title === 'ID undefined'), false)
  }
  h.form.case_people = 0; h.form.notice_group = ''; assert.equal(await h.save(), true); assert.equal(h.writes[0][1].notice_group, null)
})
test('preserves scene/scope business restrictions and does not erase initially hydrated scenes', async t => {
  const h = setup(); t.after(h.close); await h.openEdit(row({ test_envs: [2], execution_scenes: ['production_regression'] }))
  assert.deepEqual(h.form.execution_scenes, ['production_regression']); assert.equal(h.sceneOptions.value.some(option => option.key === 'stability_monitoring'), true)
  assert.equal(h.scopeOptions.value.find(option => option.key === 'module').disabled, true)
  h.form.test_envs = [0]; await flush(); assert.equal(h.sceneOptions.value.some(option => option.key === 'stability_monitoring'), false)
  h.form.case_types = [0]; await flush(); assert.equal(h.supportsApi.value, false); assert.equal(h.form.api_concurrency_limit, null)
  const options = h.enumStore.automation_execution_scene
  assert.deepEqual(dto.taskEditorScenes(options, { execution_scope: 'full_product', test_envs: [2] }).map(option => option.key), ['stability_monitoring','production_regression'])
  assert.equal(dto.taskEditorScopes(h.enumStore.automation_execution_scope, { test_envs: [2], execution_scenes: ['regression_test'] }).find(option => option.key === 'full_product').disabled, true)
})
test('network/business failures keep draft and retry with loading released', async t => {
  let attempts = 0
  const h = setup({ save: async () => { attempts++; if (attempts === 1) throw Error('network'); return { code: attempts === 2 ? 403 : 200 } } }); t.after(h.close)
  await h.openEdit(row()); h.form.name = 'Saved draft'
  for (let i = 0; i < 2; i++) { assert.equal(await h.save(), false); assert.equal(h.opened.value, true); assert.equal(h.form.name, 'Saved draft'); assert.equal(h.saving.value, false); assert.match(h.saveError.value, /失败/); assert.equal(h.events.length, 0) }
  assert.equal(await h.save(), true); assert.equal(h.writes.length, 3)
})
test('metadata failures are local, retryable, independent and cannot bypass missing capacity', async t => {
  const capacity = deferred(), users = deferred(); let attempts = 0
  const h = setup({ getUserName: () => users.promise, getSystemTaskExecutionOptions: () => ++attempts === 1 ? capacity.promise : Promise.resolve({ code: 200, data: { api_platform_limit: 4 } }) }); t.after(h.close)
  const opening = h.openEdit(row()); await flush()
  assert.equal(h.usersLoading.value, true); assert.equal(h.capacityLoading.value, true); assert.equal(h.timingsLoading.value, false); assert.equal(h.noticesLoading.value, false)
  assert.equal(await h.save(), false); assert.equal(h.writes.length, 0)
  users.resolve({ code: 200, data: [] }); capacity.resolve({ code: 403 }); await opening
  assert.equal(h.metadataLoading.value, false); assert.match(h.metadataErrors.value.join(), /执行容量/)
  await h.retryMetadata(); assert.equal(h.platformLimit.value, 4); assert.deepEqual(h.metadataErrors.value, []); assert.equal(await h.save(), true)
})
test('an optional notice failure does not prevent saving a valid task without notice', async t => {
  const h = setup({ getSystemNoticeName: async () => { throw Error('network') } }); t.after(h.close)
  await h.openEdit(row({ notice_group: null })); assert.match(h.metadataErrors.value.join(), /通知组/); assert.equal(await h.save(), true)
})
test('failed metadata retries cannot reuse stale execution capacity or enum readiness', async () => {
  for (const failure of ['capacity','enums']) {
    let failed = false
    const h = setup({ getEnum: async () => { if (failed && failure === 'enums') throw Error('network') },
      getSystemTaskExecutionOptions: async () => ({ code: failed && failure === 'capacity' ? 403 : 200, data: { api_platform_limit: 8 } }) })
    try { await h.openEdit(row()); failed = true; await h.retryMetadata(); assert.equal(await h.save(), false); assert.equal(h.writes.length, 0); failed = false; await h.retryMetadata(); assert.equal(await h.save(), true) }
    finally { h.close() }
  }
})
test('late metadata from replaced record/product cannot overwrite the current selection', async t => {
  const first = deferred(), second = deferred(), h = setup({ getSystemNoticeName: product => product === 0 ? first.promise : second.promise }); t.after(h.close)
  const old = h.openEdit(row()); await flush(); const fresh = h.openEdit(row({ id: 1, project_product: { id: 2 }, notice_group: null })); await flush()
  second.resolve({ code: 200, data: [{ value: 2, label: 'New notice' }] }); await fresh
  first.resolve({ code: 200, data: [{ value: 0, label: 'Old notice' }] }); await old
  assert.equal(h.recordId.value, 1); assert.deepEqual(h.availableNotices.value, [{ key: 2, title: 'New notice' }]); assert.equal(h.noticesLoading.value, false)
})
test('cancel during save retains physical lock and suppresses stale window feedback', async t => {
  const pending = deferred(), h = setup({ save: () => pending.promise }); t.after(h.close)
  await h.openEdit(row()); const saving = h.save(); h.closeEditor(); await h.openCreate(); assert.equal(h.opened.value, false); assert.equal(h.saving.value, true)
  pending.resolve({ code: 200 }); await saving; assert.equal(h.shell.visible, false); assert.deepEqual(h.events, [['saved']]); assert.deepEqual(h.messages, [])
  await h.openCreate(); assert.equal(h.opened.value, true)
})
test('all identity dimensions invalidate the window and suppress prior write results', async t => {
  for (const change of [h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/elsewhere', h => h.route.fullPath += '?id=2']) {
    const pending = deferred(), h = setup({ save: () => pending.promise })
    try { await h.openEdit(row()); const saving = h.save(); change(h); assert.equal(h.opened.value, false); pending.resolve({ code: 200 }); await saving; assert.equal(h.events.length, 0); assert.deepEqual(h.messages, []) }
    finally { h.close() }
  }
})
test('background, KeepAlive deactivation and unmount invalidate pending reads and block reopening until active', async () => {
  for (const mode of ['background','deactivate','unmount']) {
    const pending = deferred(), h = setup({ getUserName: () => pending.promise })
    try {
      h.mount(); const opening = h.openEdit(row()); await flush()
      if (mode === 'background') h.visibility('hidden')
      else h.callbacks[mode].forEach(fn => fn())
      assert.equal(h.opened.value, false); await h.openCreate(); assert.equal(h.opened.value, false)
      pending.resolve({ code: 200, data: [{ key: 99, title: 'Late owner' }] }); await opening
      assert.deepEqual(h.availableUsers.value, []); assert.equal(h.usersLoading.value, false)
      if (mode === 'background') h.visibility('visible')
      if (mode === 'deactivate') h.callbacks.activate.forEach(fn => fn())
      if (mode !== 'unmount') { await h.openCreate(); assert.equal(h.opened.value, true) }
    } finally { h.close() }
  }
})
test('background, KeepAlive and unmount during a write do not replay success after returning', async () => {
  for (const mode of ['background','deactivate','unmount']) {
    const pending = deferred(), h = setup({ save: () => pending.promise })
    try {
      h.mount(); await h.openEdit(row()); const saving = h.save()
      if (mode === 'background') h.visibility('hidden')
      else h.callbacks[mode].forEach(fn => fn())
      assert.equal(h.saving.value, true); pending.resolve({ code: 200 }); await saving
      assert.deepEqual(h.events, []); assert.deepEqual(h.messages, []); assert.equal(h.opened.value, false)
      if (mode === 'background') h.visibility('visible')
      if (mode === 'deactivate') h.callbacks.activate.forEach(fn => fn())
      await flush(); assert.deepEqual(h.events, []); assert.equal(h.saving.value, false)
    } finally { h.close() }
  }
})
test('malformed edit record is not silently converted into creation', async t => {
  const h = setup(); t.after(h.close)
  for (const value of [undefined, null, {}, { id: Number.MAX_SAFE_INTEGER + 1 }]) { await h.openEdit(value); assert.equal(h.opened.value, false) }
  assert.equal(h.writes.length, 0); assert.equal(h.messages.length, 4)
})
test('parent delegates editor boundary and all affected SFC blocks compile', async () => {
  const source = readFileSync(path.join(base, 'index.vue'), 'utf8')
  assert.match(source, /<TaskEditorDialog ref="taskEditorRef" @saved="doRefresh"/)
  assert.doesNotMatch(source, /createFormItems|prefillNavigationFormItems|data\.isAdd|data\.updateId|onDataForm/)
  for (const relative of ['index.vue','components/TaskEditorDialog.vue']) {
    const filename = path.join(base, relative), { descriptor, errors } = parse(readFileSync(filename,'utf8'), { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: relative })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: relative, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: relative, scoped: true })).errors, [])
  }
})
