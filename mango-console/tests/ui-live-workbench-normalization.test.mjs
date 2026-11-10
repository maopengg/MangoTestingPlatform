import assert from 'node:assert/strict'
import test from 'node:test'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { liveHarness, models, lossless } from './helpers/ui-live-workbench-harness.mjs'

test('route adapter rejects repeated/object query parameters and preserves zero and long IDs', () => {
  const { liveWorkbenchRoute } = loadModule('src/views/uitest/live-workbench/config.ts', { '@/components/business/ui-live-workbench': models })
  assert.deepEqual(liveWorkbenchRoute({ pageId: ['1', '2'], testEnv: {}, category: ['x'] }), { mode: 'element', pageId: undefined, pageStepId: undefined, testEnv: undefined, category: undefined })
  assert.equal(liveWorkbenchRoute({ pageId: 0 }).pageId, '0'); assert.equal(liveWorkbenchRoute({ mode: 'step', pageStepId: '900719925474099399' }).pageStepId, '900719925474099399')
})
test('zero ID creates one workspace; late create is released after identity switch before next allocation', async t => {
  const pending = deferred(), close = deferred(); let calls = 0
  const h = liveHarness({ api: { createUiLiveWorkspace: () => ++calls === 1 ? pending.promise : Promise.resolve({ data: { status: 'select_actuator', actuators: [] } }), closeUiLiveWorkspace: () => close.promise } }); t.after(h.cleanup)
  const opening = h.openWorkspace(); await flush(); await h.openWorkspace(); assert.equal(calls, 1)
  assert.equal(h.writes[0][1].resource_id, '0'); assert.equal(h.writes[0][1].test_env, 0)
  h.mount(); h.user.roleId++; pending.resolve({ data: { workspace_id: 'old' } }); await flush(); assert.equal(calls, 1); assert.equal(h.workspace.workspaceId, ''); assert.equal(h.workspaceOpening.value, true)
  close.resolve({ code: 200 }); await opening; await flush(); assert.equal(calls, 2); assert.equal(h.workspaceOpening.value, false)
})
test('ready status response cannot update replacement workspace or restart polling after unmount', async t => {
  const pending = deferred(), h = liveHarness({ api: { getUiLiveWorkspaceStatus: () => pending.promise } }); t.after(h.cleanup)
  h.workspace.workspaceId = 'old'; const ready = h.waitForWorkspaceReady(); const polling = h.tick(500); await flush()
  h.callbacks.unmount.forEach(fn => fn()); pending.resolve({ data: { status: 'ready' } }); await polling; assert.equal(await ready, false); assert.equal(h.workspace.ready, false); assert.equal(h.timers.size, 0)
})
test('element options ignore out-of-order responses and expose retryable local error', async t => {
  const first = deferred(); let count = 0
  const h = liveHarness({ api: { getUiUiElementName: () => ++count === 1 ? first.promise : Promise.resolve({ data: [{ id: 0, name: 'new' }] }) } }); t.after(h.cleanup)
  const old = h.loadElements(); await h.loadElements(); first.resolve({ data: [{ id: 1, name: 'old' }] }); await old
  assert.equal(h.elementOptions.value[0].name, 'new'); assert.equal(h.elementsLoading.value, false)
})
test('scan dispatch is physically locked across environment changes and stale response does not install task', async t => {
  const pending = deferred(), h = liveHarness({ api: { postUiElementScan: () => pending.promise } }); t.after(h.cleanup); h.ready()
  const scanning = h.scanPageElements(); await h.scanPageElements(); h.props.testEnv = 1; h.ready('next'); await h.scanPageElements(); assert.equal(h.writes.filter(([name]) => name === 'postUiElementScan').length, 1)
  pending.resolve({ data: { task_id: 'old' } }); await scanning; assert.equal(h.scanTaskId.value, ''); assert.equal(h.scanLoading.value, false); assert.equal(h.observations.size, 0)
})
test('scan poll retries failure at local interval and ignores terminal results from previous context', async t => {
  const pending = deferred(), h = liveHarness({ api: { getExecutorTask: () => pending.promise } }); t.after(h.cleanup); h.ready(); h.scanLoading.value = true; h.scanTaskId.value = 'old'
  const poll = h.pollScanTask(); h.props.pageId = 2; pending.resolve({ data: { terminal: true, status: 'success', result: { elements: [{ text: 'old' }] } } }); await poll
  assert.equal(h.scannedElements.value.length, 0); assert.equal(h.scanLoading.value, false); assert.equal([...h.timers.values()].some(item => item.delay === 1000), false)
})
test('AI close during HTTP request retains lock and rejects late candidates', async t => {
  const pending = deferred(), h = liveHarness({ api: { postUiElementAiLocatorRecommend: () => pending.promise } }); t.after(h.cleanup); h.ready()
  const record = { text: 'Example', locators: [{ exp: 0, loc: '//button', sub: '' }] }, request = h.openAiLocatorRecommendation(record, 'scan'); await flush(); h.aiLocator.visible = false
  await h.openAiLocatorRecommendation({ text: 'other' }, 'scan'); assert.equal(h.writes.filter(([name]) => name === 'postUiElementAiLocatorRecommend').length, 1)
  pending.resolve({ data: { candidates: [{ exp: 0, loc: '//old' }] } }); await request; assert.deepEqual(h.aiLocator.candidates, []); assert.equal(h.aiLocator.loading, false); assert.equal(record._aiLoading, false)
})
test('deep check writes executor task ID, locks duplicates and cannot mark replacement result applied', async t => {
  const pending = deferred(), h = liveHarness({ api: { putUiElementDeepCheckApply: () => pending.promise } }); t.after(h.cleanup)
  h.elementCheckDetail.visible = true; h.elementCheckDetail.data = { element_id: 0, check_id: 'not-task', executor_task_id: '900719925474099399' }
  const apply = h.applyDeepCheckUpdates(); await h.applyDeepCheckUpdates(); assert.deepEqual(h.writes[0][1], { element_id: 0, task_id: '900719925474099399' })
  h.elementCheckDetail.data = { element_id: 1, executor_task_id: 'next' }; pending.resolve({ data: { applied_slots: [1] } }); await apply; assert.equal(h.deepCheckApplied.value, false); assert.equal(h.deepCheckApplyLoading.value, false)
})
test('background and KeepAlive clear subscriptions/timers/owned windows and resume only in current route', async t => {
  const h = liveHarness(); t.after(h.cleanup); h.mount(); await flush(); h.ready(); h.elementCheckDetail.visible = true; const version = h.contextVersion.value
  h.visibility('hidden'); assert.equal(h.workspace.workspaceId, ''); assert.equal(h.elementCheckDetail.visible, false); assert.ok(h.contextVersion.value > version)
  const count = h.writes.length; h.callbacks.deactivate.forEach(fn => fn()); h.visibility('visible'); await flush(); assert.equal(h.writes.length, count)
  h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(h.writes.filter(([name]) => name === 'createUiLiveWorkspace').length, 2)
})
test('recording snapshot isolates nested false/zero/null/lossless values and strips local check flags', () => {
  const action = { client_id: 'one', action: 'manual', name: 'Example', category: '', status: 'ready', detail: { type: 3, custom: [{ key: 'x', value: { a: false, b: 0, c: null, n: new lossless.LosslessJsonNumber('900719925474099399') } }] }, _checking: true }
  const snapshot = models.recordingSnapshot([action]); action.detail.custom[0].value.b = 2
  assert.equal(snapshot[0]._checking, undefined); assert.equal(snapshot[0].detail.custom[0].value.b, 0); assert.equal(String(snapshot[0].detail.custom[0].value.n), '900719925474099399')
})
test('successful recording removes saved nodes but preserves nodes recorded while request was pending', async t => {
  const h = liveHarness(); t.after(h.cleanup); h.recordedActions.value = [{ client_id: 'saved' }, { client_id: 'new' }]; h.handleRecordingSaved({ id: 0 }, ['saved'])
  assert.deepEqual(h.recordedActions.value.map(item => item.client_id), ['new'])
})
test('workspace cleanup blocks recreation until the remote close actually settles', async t => {
  const pending = deferred(), h = liveHarness({ api: { closeUiLiveWorkspace: () => pending.promise } }); t.after(h.cleanup); h.ready()
  h.mount(); h.props.testEnv = 2; await h.openWorkspace(); assert.equal(h.writes.filter(([name]) => name === 'createUiLiveWorkspace').length, 0)
  pending.resolve({ code: 200 }); await flush(); assert.equal(h.writes.filter(([name]) => name === 'createUiLiveWorkspace').length, 1)
})
test('all identity boundaries invalidate A-B-A requests, windows and workspace state', async () => {
  const changes = [h => { h.props.pageId = 2; h.props.pageId = 0 }, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-next', h => h.permission.permissionKeys.push('example:read'), h => h.route.fullPath += '&category=Example', h => { h.props.testEnv = 2; h.props.testEnv = 0 }]
  for (const change of changes) {
    const pending = deferred(), h = liveHarness({ api: { getUiUiElementName: () => pending.promise } })
    try { h.ready(); h.elementCheckDetail.visible = true; const read = h.loadElements(); change(h); pending.resolve({ data: [{ id: 0, name: 'Late' }] }); await read; assert.equal(h.elementOptions.value.length, 0); assert.equal(h.elementCheckDetail.visible, false); assert.equal(h.workspace.workspaceId, '') } finally { h.cleanup() }
  }
})
test('late locator command result cannot overwrite a newer result or cancel HTTP page scanning', async t => {
  const h = liveHarness(); t.after(h.cleanup); h.ready(); h.scanLoading.value = true; h.scanTaskId.value = 'current-task'; h.latestElementResult.value = { name: 'Current' }
  h.scannedElements.value = [{ _rowKey: 'one', _checkKey: 'new-check', _checking: true }]
  h.handleLiveCommandResult({ success: false, data: { row_key: 'old-check' } }); assert.equal(h.scanLoading.value, true); assert.equal(h.scannedElements.value[0]._checking, true)
  h.handleLiveCommandResult({ data: { row_key: 'old-check', scan_check_result: { name: 'Old', status: 1 } } }); assert.equal(h.latestElementResult.value.name, 'Current')
  h.handleLiveCommandResult({ data: { row_key: 'new-check', scan_check_result: { name: 'New', status: 1 } } }); assert.equal(h.latestElementResult.value.name, 'New'); assert.equal(h.scannedElements.value[0]._checking, false)
})
test('scan failure continues local task polling and finishes with a matching result', async t => {
  let fail = true; const h = liveHarness({ api: { getExecutorTask: async () => { if (fail) throw Error('Example unavailable'); return { data: { terminal: true, status: 'success', result: { elements: [{ text: 'Example', locators: [{ exp: 0, loc: '//button', sub: 0 }] }] } } } } } }); t.after(h.cleanup); h.ready(); h.scanLoading.value = true; h.scanTaskId.value = 'current'
  await h.pollScanTask(); assert.ok([...h.timers.values()].some(item => item.delay === 1500)); fail = false; await h.tick(1500); assert.equal(h.scanLoading.value, false); assert.equal(h.scannedElements.value[0].locators[0].sub, 0)
})
test('recording session storage is scoped by user, role and environment and preserves lossless numbers', async t => {
  const h = liveHarness(); t.after(h.cleanup); h.recordingPaused.value = false
  h.appendRecordedAction({ action: 'manual', name: 'Example', detail: { type: 3, custom: [{ key: 'x', value: new lossless.LosslessJsonNumber('900719925474099399') }] } }); h.persistRecordedActions(); h.recordedActions.value = []; h.restoreRecordedActions()
  assert.equal(String(h.recordedActions.value[0].detail.custom[0].value), '900719925474099399'); const originalKey = h.recordingStorageKey.value; h.user.roleId++; h.restoreRecordedActions(); assert.notEqual(h.recordingStorageKey.value, originalKey); assert.equal(h.recordedActions.value.length, 0)
})
test('element check dispatch cannot register a task or release another context after environment replacement', async t => {
  const pending = deferred(), h = liveHarness({ api: { postUiElementCheck: () => pending.promise } }); t.after(h.cleanup); h.ready(); h.selectedElementId.value = 0
  const check = h.checkSelectedElement('deep', { example: 'before' }); await h.checkSelectedElement(); assert.equal(h.writes.filter(([name]) => name === 'postUiElementCheck').length, 1)
  h.props.testEnv = 2; pending.resolve({ data: { task_id: 'old', check_id: 'old' } }); assert.equal(await check, false); assert.equal(h.elementChecking.value, false); assert.equal(h.observations.size, 0)
})
test('step execution captures zero ID, environment and control before awaits and stays locked until matching final result', async t => {
  const h = liveHarness({ props: { mode: 'step', pageStepId: 0, stepControl: { example: 'before' } } }); t.after(h.cleanup); h.ready(); h.livePanelRef.value = { suspendControlForAutomation: async () => true, resumeControlAfterAutomation() {} }
  const debugging = h.debugStep(0); h.props.stepControl.example = 'after'; assert.equal(await debugging, true); await h.debugStep(0)
  const calls = h.reads.filter(([name]) => name === 'getUiStepsTest'); assert.equal(calls.length, 1); assert.deepEqual(calls[0].slice(1), [0, 0, 'example-workspace', { example: 'before' }, 0, true]); assert.equal(h.stepDebugging.value, true)
  h.mount(); window.dispatchEvent(Object.assign(new Event('mango:websocket-message'), { detail: { data: { func_name: 'u_page_steps', func_args: { workspace_id: 'other', is_final: true } } } })); assert.equal(h.stepDebugging.value, true)
  window.dispatchEvent(Object.assign(new Event('mango:websocket-message'), { detail: { data: { func_name: 'u_page_steps', func_args: { workspace_id: 'example-workspace', is_final: true } } } })); assert.equal(h.stepDebugging.value, false)
})
test('late control release cannot dispatch a step in a replacement workbench', async t => {
  const pending = deferred(), h = liveHarness({ props: { mode: 'step', pageStepId: 0 } }); t.after(h.cleanup); h.ready(); h.livePanelRef.value = { suspendControlForAutomation: () => pending.promise }
  const debugging = h.debugStep(); await flush(); h.user.roleId++; pending.resolve(true); assert.equal(await debugging, false); assert.equal(h.reads.some(([name]) => name === 'getUiStepsTest'), false)
})
test('AI validation continuation cannot schedule a timer after closing the recommendation window', async t => {
  const pending = deferred(), h = liveHarness({ api: { postUiElementAiLocatorRecommend: async () => ({ data: { candidates: [{ exp: 0, loc: '//button' }] } }) } }); t.after(h.cleanup); h.ready(); h.livePanelRef.value = { sendWorkspaceCommand: () => pending.promise }
  const opening = h.openAiLocatorRecommendation({ name: 'Example', locators: [] }, 'scan'); await flush(); assert.equal(h.aiLocator.validating, true); h.aiLocator.visible = false; pending.resolve(true); await opening
  assert.equal(h.aiLocator.validating, false); assert.equal([...h.timers.values()].some(item => item.delay === 30000), false)
})
test('saved flat locator fields remain usable after finite element-option normalization', async t => {
  const h = liveHarness({ bindings: 'loadElements,recordedElementLocators', api: { getUiUiElementName: async () => ({ data: [{ id: 0, name: 'Example', exp: 0, loc: '//button', sub: 0 }] }) } }); t.after(h.cleanup)
  await h.loadElements(); assert.deepEqual(h.recordedElementLocators({ element_id: 0 }), [{ exp: 0, loc: '//button', sub: 0 }])
})
