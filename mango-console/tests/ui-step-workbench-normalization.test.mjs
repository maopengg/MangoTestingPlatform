import test from 'node:test'
import assert from 'node:assert/strict'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { stepHarness, step, flow, detail, healing, methodDefinition } from './helpers/ui-step-workbench-harness.mjs'
import path from 'node:path'
import { liveHarness } from './helpers/ui-live-workbench-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'

test('step APIs preserve zero and long detail IDs without Number conversion', () => {
  const requests = [], api = loadModule('src/api/uitest/page-steps.ts', { '@/api/http': { get: value => { requests.push(value); return value } } })
  for (const id of [0, '9007199254740993123']) {
    api.getUiStepsTest(0, 0, undefined, {}, id, true)
    const request = requests.at(-1); assert.equal(request.data().page_step_detail_id, id); assert.equal(request.silentError, true)
  }
})
test('field validation preserves false and zero but rejects an empty selector array', () => {
  const { isEmptyStepField } = loadModule('src/views/uitest/page-steps/details/config.ts', { '@arco-design/web-vue': {} })
  assert.equal(isEmptyStepField(false), false); assert.equal(isEmptyStepField(0), false); assert.equal(isEmptyStepField([]), true)
})

test('shared node fields emit owned copies and keep inherited or disabled fields unchanged', t => {
  const item = { key: 'example', value: ['before'], type: 'input' }
  const h = liveHarness({ filename: path.resolve('src/components/business/UiStepNodeConfigForm.vue'), bindings: 'setValue', props: { items: [item], isItemDisabled: () => false, isItemInherited: () => false } }); t.after(h.cleanup)
  const next = ['after']; h.setValue(item, next); next.push('mutation')
  assert.deepEqual(item.value, ['before']); assert.deepEqual(h.events[0], ['update-field', 'example', ['after']])
  h.props.isItemDisabled = () => true; h.setValue(item, 'ignored'); assert.equal(h.events.length, 2)
})
test('SQL test confirmation retains the original payload and is invalidated by an environment change', async t => {
  const pending = deferred(), confirms = [], notifications = []; let count = 0
  const h = liveHarness({ filename: path.resolve('src/components/forms/DataSourceOperationList.vue'), bindings: 'executeTest,testingRows',
    props: { projectProductId: 0, testEnv: 0, dataList: [{ id: 0, datasource_alias: 0, value: 'UPDATE example SET value = 1' }], datasourceOptions: [{ value: 0, label: 'Example', dbType: 0 }] },
    api: { postDataSourceExecution: async () => { count++; if (count === 1) return pending.promise; return { code: 200, data: {} } } },
    modules: { '@arco-design/web-vue': { Message: { error() {}, warning() {} }, Notification: { success: value => notifications.push(value) }, Modal: { confirm: options => { const result = { ...options, close() {} }; confirms.push(result); return result } } } },
  }); t.after(h.cleanup)
  const row = h.props.dataList[0], writing = h.executeTest(row, 0); await h.executeTest(row, 0); assert.equal(count, 1)
  row.value = 'UPDATE example SET value = 2'; pending.reject(Error('包含写入行为')); await writing
  await confirms[0].onBeforeOk(); assert.equal(h.writes[1][1].operation_config, 'UPDATE example SET value = 1')
  h.props.testEnv = 2; assert.equal(await confirms[0].onBeforeOk(), false); assert.equal(count, 2)
})

test('flow writes freeze their payload, keep the physical lock through invalidation, and reject stale completion', async t => {
  const pending = deferred(), h = stepHarness({ api: { putUiSteps: () => pending.promise } }); t.after(h.cleanup)
  h.flowData.value = flow(); h.flowRevision.value++
  const saving = h.flowSave.persist(); await flush(); h.flowData.value.nodes[0].label = 'Changed'
  assert.equal(h.writes[0][1].flow_data.nodes[0].label, 'Example node')
  h.flowSave.invalidate(); assert.equal(h.flowSaving.value, true)
  pending.resolve({ code: 200 }); await saving
  assert.equal(h.flowSaving.value, false); assert.equal(h.flowSave.savedRevision.value, 0)
})
test('failed flow writes require a retry and never claim the dirty revision was saved', async t => {
  let fail = true
  const h = stepHarness({ api: { putUiSteps: async () => { if (fail) throw Error('Example failure'); return { code: 200 } } } }); t.after(h.cleanup)
  h.flowRevision.value = 2; await h.flowSave.persist(); assert.equal(h.flowSaveStatus.value, 'error'); assert.equal(h.flowSave.savedRevision.value, 0)
  fail = false; await h.flowSave.persist(); assert.equal(h.flowSaveStatus.value, 'saved'); assert.equal(h.flowSave.savedRevision.value, 2)
})
test('debug polling ignores unrelated tasks, retries quietly, and accepts a matching terminal result', async t => {
  let mode = 'foreign'
  const h = stepHarness({ api: { getExecutorTask: async () => ({ code: 200, data: { task_id: mode === 'foreign' ? 'foreign' : 'example-task', business_id: 0, business_type: 'u_page_step', terminal: mode === 'done', result: { status: 0, element_result_list: [] } } }) } }); t.after(h.cleanup)
  await h.initializeStep(); await h.stepDebug.run(); await h.stepDebug.poll()
  assert.equal(h.stepDebug.running.value, true); assert.match(h.stepDebug.error.value, /重试/)
  assert.equal(h.reads.find(([name]) => name === 'getExecutorTask')[2], true)
  mode = 'done'; await h.stepDebug.poll(); assert.equal(h.stepDebug.running.value, false); assert.equal(h.stepDebug.completed.value, true)
})
test('debug result reads cannot update a replacement environment and backgrounding stops observation', async t => {
  const pending = deferred(), h = stepHarness({ api: { getExecutionResultLatestResolved: () => pending.promise } }); t.after(h.cleanup)
  const loading = h.stepDebug.latest(true); h.user.selected_environment = 3
  pending.resolve({ code: 200, data: { id: 0, result_data: { status: 0, element_result_list: [] } } }); assert.equal(await loading, null)
  h.mount(); h.stepDebug.running.value = true; h.visibility('hidden'); assert.equal(h.stepDebug.running.value, false)
})
test('healing resources load independently and retrying a failed read does not replay an accepted action', async t => {
  let fail = false, count = 0
  const h = stepHarness({ component: 'UiPageStepHealingPanel', api: { getUiPageStepHealRecords: async () => { if (fail) throw Error('Example read failure'); return { code: 200, data: { items: [healing()] } } }, postUiPageStepHealApply: async () => { count++; fail = true; return { code: 200 } } } }); t.after(h.cleanup)
  await h.reloadHealing(); assert.equal(h.versions.value.length, 1)
  await h.applyRecord(healing()); assert.match(h.resourceErrors.records, /失败/)
  await h.applyRecord(healing()); assert.equal(count, 1)
  fail = false; await h.loadResource('records'); assert.equal(h.resourceErrors.records, ''); assert.equal(count, 1)
})
test('healing write lock survives closing and reopening the same asset', async () => {
  const pending = deferred(); let count = 0
  const a = stepHarness({ component: 'UiPageStepHealingPanel', api: { putUiSteps: () => { count++; return pending.promise } } })
  let b
  try {
    await a.reloadHealing(); const saving = a.save(); await flush(); a.cleanup()
    b = stepHarness({ component: 'UiPageStepHealingPanel' }); await b.reloadHealing(); assert.equal(b.saving.value, true); assert.equal(await b.save(), false)
    pending.resolve({ code: 200 }); await saving; assert.equal(count, 1); assert.equal(b.saving.value, false); assert.equal(a.events.some(([name]) => name === 'changed'), false)
  } finally { b?.cleanup() }
})
test('healing checkpoint partial success is retained when the subsequent configuration write fails', async t => {
  let writes = 0, configurations = 0
  const h = stepHarness({ component: 'UiPageStepHealingPanel', api: { postUiPageStepsDetailed: async () => { writes++; return { code: 200 } }, putUiSteps: async () => { configurations++; if (configurations === 1) throw Error('Example write failure'); return { code: 200 } } } }); t.after(h.cleanup)
  await h.reloadHealing(); h.draft.healing_enabled = true; h.draft.goal = 'Example goal'
  h.draft.success_criteria.conditions = [{ type: 'page_title', matcher: 'equals', expected: 'Example' }]
  h.nodeCheckpoints.value[0].precondition.conditions = [{ type: 'element_state', matcher: 'visible', element_id: 0 }]
  assert.equal(await h.save(), false); assert.equal(writes, 1)
  await h.save(); assert.equal(writes, 1); assert.equal(configurations, 2)
})
test('healing detail rejects a response for the wrong record and stale selection', async t => {
  const pending = deferred(), h = stepHarness({ component: 'UiPageStepHealingPanel', api: { getUiPageStepHealRecord: () => pending.promise } }); t.after(h.cleanup)
  const loading = h.showDetail(healing()); h.user.roleId++
  pending.resolve({ code: 200, data: healing() }); await loading; assert.equal(h.selectedDetail.value, null)
})

test('standalone and case-embedded workbenches retain zero IDs and independent resources', async t => {
  const pending = deferred(), h = stepHarness({ api: { getDataFactoryDatasourceAlias: () => pending.promise } }); t.after(h.cleanup)
  const initializing = h.initializeStep(); await flush(); assert.equal(h.currentPageStepsId.value, 0); assert.equal(h.currentPageId.value, 0); assert.equal(h.currentStepRecord.value.id, 0)
  assert.equal(h.stepResources.loading.aliases, true); assert.equal(h.stepResources.loading.details, false); assert.equal(h.nodeDetails.value[0].id, 0)
  pending.resolve({ code: 200, data: [] }); await initializing; assert.match(h.stepsTitle.value, /0/)
})
test('explicit invalid route ID never falls back to another cached or embedded asset', t => {
  const h = stepHarness({ props: { pageStepsId: '', pageId: '' } }); t.after(h.cleanup); h.route.query.id = {}; assert.equal(h.currentPageStepsId.value, '')
})
test('independent instances own fresh form definitions and metadata parameters are not mutated by serialization', async () => {
  const a = stepHarness(), b = stepHarness()
  try {
    a.changeStatus(0); b.changeStatus(0); a.nodeFields.value[0].value = 'click'; assert.equal(b.nodeFields.value[0].value, '')
    const before = structuredClone(methodDefinition.parameter), input = { ope_key: 'click', ele_name: ['Example', 0] }
    const result = a.processOptionData(input); assert.equal(result.ele_name, 0); assert.deepEqual(methodDefinition.parameter, before)
  } finally { b.cleanup(); a.cleanup() }
})
test('standalone identity and route A-B-A invalidate old resources and owned windows', async t => {
  const pending = deferred(), h = stepHarness({ api: { getUiSteps: () => pending.promise } }); t.after(h.cleanup)
  const loading = h.doRefreshSteps(0); h.stepCachePanel.visible = h.pageElementsPanel.visible = true; h.user.roleId++; assert.equal(h.stepCachePanel.visible, false); assert.equal(h.pageElementsPanel.visible, false)
  pending.resolve({ code: 200, data: [step()] }); await loading; assert.equal(h.currentStepRecord.value, null); assert.equal(h.stepResources.loading.steps, false)
})
test('canvas deletion retains its node when the backend rejects and accepts exactly once when it succeeds', async t => {
  const pending = deferred(); let allow = false, count = 0
  const h = stepHarness({ component: 'canvas', props: { beforeNodeDelete: async () => { count++; if (count === 1) return pending.promise; return allow } } }); t.after(h.cleanup); await flush()
  const deleting = h.deleteNodeById('node-0'); await h.deleteNodeById('node-0'); assert.equal(count, 1); assert.equal(h.flowNodes.value.length, 1)
  pending.resolve(false); await deleting; assert.equal(h.flowNodes.value.length, 1); allow = true; await h.deleteNodeById('node-0'); assert.equal(h.flowNodes.value.length, 0)
})
test('canvas owns node/config positions and does not mutate the incoming flow', async t => {
  const input = flow(), h = stepHarness({ component: 'canvas', props: { flowData: input } }); t.after(h.cleanup); await flush()
  h.flowNodes.value[0].position.x = 50; h.flowNodes.value[0].data.config.id = 2; assert.equal(input.nodes[0].position.x, 0); assert.equal(input.nodes[0].config.id, 0)
})
test('canvas context replacement invalidates an outstanding deletion and old selection', async t => {
  const pending = deferred(), h = stepHarness({ component: 'canvas', props: { contextKey: 'A', beforeNodeDelete: () => pending.promise } }); t.after(h.cleanup); await flush()
  const deleting = h.deleteNodeById('node-0'); h.props.contextKey = 'B'; h.props.contextKey = 'A'; pending.resolve(true); await deleting; assert.equal(h.flowNodes.value.length, 1); assert.equal(h.events.some(([name]) => name === 'nodeDelete'), false)
})
test('node deletion freezes the parent ID and physical lock survives context replacement', async t => {
  const pending = deferred(), h = stepHarness({ api: { deleteUiPageStepsDetailed: () => pending.promise } }); t.after(h.cleanup)
  const deleting = h.onNodeDelete(flow().nodes[0]); await flush(); h.user.roleId++; assert.equal(h.nodeDeleting.value, true); assert.equal(await h.onNodeDelete(flow().nodes[0]), false)
  pending.resolve({ code: 200 }); assert.equal(await deleting, false); assert.deepEqual(h.writes[0].slice(1), [0, 0]); assert.equal(h.nodeDeleting.value, false)
})
test('node save freezes input before waiting on a prior canvas write', async t => {
  const pending = deferred(), h = stepHarness(); t.after(h.cleanup)
  await h.initializeStep()
  h.selectedNode.value = flow().nodes[0]; h.onNodeClick(h.selectedNode.value); h.configEditing.value = true
  h.flowSave.wait = () => pending.promise
  const saving = h.saveFormData(); await flush(); h.nodeFields.value.find(item => item.key === 'ope_key').value = 'after'
  pending.resolve(); await saving; assert.equal(h.writes.find(([name]) => name === 'postUiPageStepsDetailed')[1].ope_key, 'click')
})
test('debug submission locks before asynchronous preparation and freezes zero IDs/environment', async t => {
  const pending = deferred(), h = stepHarness({ api: { getUiStepsTest: () => pending.promise } }); t.after(h.cleanup)
  await h.initializeStep(); const writing = h.onRunCase(); await flush(); await h.onRunCase(); assert.equal(h.reads.filter(([name]) => name === 'getUiStepsTest').length, 1)
  h.user.selected_environment = 2; pending.resolve({ code: 200, data: { task_id: 'example-old', slot_id: 'old' } }); assert.equal(await writing, false); assert.equal(h.stepDebug.running.value, false)
})
test('unknown active tasks never bind an arbitrary result or environment and block duplicate debugging', async t => {
  const h = stepHarness({ api: { getActiveExecutorTasks: async () => ({ code: 200, data: [{ task_id: 'foreign-task', business_id: 0, business_type: 'u_page_step', terminal: false }] }) } }); t.after(h.cleanup)
  await h.stepDebug.recover(); assert.equal(h.stepDebug.uncertain.value, true); assert.equal(h.stepDebug.taskId.value, ''); assert.equal(await h.stepDebug.run(), false)
})
