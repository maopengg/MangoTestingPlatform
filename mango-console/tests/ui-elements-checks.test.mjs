import assert from 'node:assert/strict'
import test from 'node:test'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { elementsHarness, elementRow, records } from './helpers/ui-elements-harness.mjs'

const terminal = (extra = {}) => ({ code: 200, data: { task_id: 'example-task', task_type: 'element_deep_check', business_type: 'u_element_check', business_id: 0, terminal: true, result: { element_id: 0, element_name: 'Example', check_id: 'example-check', check_status: 'valid', check_mode: 'deep', selected_result: { locator_engine: { locator_updates: [{ same_target: true, slot: 1, loc: '//button' }] } } }, ...extra } })
const launch = { code: 200, data: { task_id: 'example-task', check_id: 'example-check' } }
test('check dispatch preserves zero ID, environment and immutable temporary variables', async t => {
  const pending = deferred(), variables = { example: 'before' }, h = elementsHarness({ api: { postUiElementCheck: () => pending.promise } }); t.after(h.cleanup)
  h.deepCheckVariablesDialogRef.value = { open: async () => variables }; const checking = h.onCheck(elementRow()); await flush(); variables.example = 'after'; await h.onCheck(elementRow())
  assert.equal(h.writes.length, 1); assert.deepEqual(h.writes[0][1], { element_id: 0, test_env: 0, check_mode: 'deep', runtime_variables: { example: 'before' } }); pending.resolve(launch); assert.equal(await checking, true)
})
test('cancelled variable input and replaced environment cannot dispatch a check', async () => {
  for (const replace of [false, true]) {
    const pending = deferred(), h = elementsHarness()
    try { h.deepCheckVariablesDialogRef.value = { open: () => pending.promise }; const checking = h.onCheck(elementRow()); if (replace) h.user.selected_environment++; pending.resolve(replace ? {} : null); assert.equal(await checking, false); assert.equal(h.writes.length, 0); assert.equal(h.checks.busy.value, false) } finally { h.cleanup() }
  }
})
test('late check creation cannot install observations after resource replacement; physical lock survives', async t => {
  const pending = deferred(), h = elementsHarness({ api: { postUiElementCheck: () => pending.promise } }); t.after(h.cleanup)
  const checking = h.onCheck(elementRow(), 'normal'); h.props.pageId = 2; await h.onCheck(elementRow({ id: 1 }), 'normal'); assert.equal(h.writes.length, 1); assert.equal(h.checks.submitting.value, true)
  pending.resolve(launch); assert.equal(await checking, false); assert.equal(h.observations.size, 1); const observation = [...h.observations.values()][0]; assert.equal(observation.environment, 0); assert.equal(observation.meta.pageId, 0); assert.equal(h.checks.pending.loadingKey, ''); assert.equal(h.checks.submitting.value, false)
})
test('task polling validates ownership, retries transient failure silently and displays one terminal result', async t => {
  let fail = true; const h = elementsHarness({ api: { postUiElementCheck: async () => launch, getExecutorTask: async () => { if (fail) throw Error('Example unavailable'); return terminal() } } }); t.after(h.cleanup)
  await h.onCheck(elementRow(), 'normal'); await h.checks.poll(); assert.ok([...h.timers.values()].some(item => item.delay === 1500)); assert.equal(h.reads.find(([name]) => name === 'getExecutorTask')[2], true)
  fail = false; await h.tick(1500); assert.equal(h.checks.result.visible, true); assert.equal(h.checks.result.data.element_id, 0); assert.equal(h.checks.result.data.executor_task_id, 'example-task'); assert.equal(h.checks.pending.loadingKey, ''); assert.equal(h.observations.size, 0)
  assert.equal(h.checks.workbenchResult(terminal().data.result), false)
})
test('old poll response cannot alter a new environment or restore its timers', async t => {
  const pending = deferred(), h = elementsHarness({ api: { postUiElementCheck: async () => launch, getExecutorTask: () => pending.promise } }); t.after(h.cleanup)
  await h.onCheck(elementRow(), 'normal'); const polling = h.checks.poll(); h.user.selected_environment++; pending.resolve(terminal()); await polling; assert.equal(h.checks.result.visible, false); assert.equal(h.checks.result.data, null); assert.equal(h.checks.pending.loadingKey, ''); assert.equal([...h.timers.values()].some(item => item.delay === 1500), false)
})
test('workbench zero-ID and scanned row results are correlated; unrelated results are rejected', t => {
  const h = elementsHarness(); t.after(h.cleanup)
  h.checks.workbenchStarted({ element_id: 0 }); assert.equal(h.checks.pending.loadingKey, '0'); assert.equal(h.checks.workbenchResult({ element_id: 1, check_id: 'other' }), false); assert.equal(h.checks.workbenchResult({ element_id: 0, check_id: 'current' }), true)
  h.checks.workbenchStarted({ element_id: 0, scan_row_key: 'current-row' }); assert.equal(h.checks.workbenchResult({ element_id: 0, scan_row_key: 'old-row' }), false); assert.equal(h.checks.workbenchResult({ element_id: 0, scan_row_key: 'current-row' }), true)
})
test('deep update uses executor task ID and cannot mark a replacement result as applied', async t => {
  const pending = deferred(), h = elementsHarness({ api: { putUiElementDeepCheckApply: () => pending.promise } }); t.after(h.cleanup)
  h.checks.workbenchStarted({ element_id: 0 }); h.checks.workbenchResult({ ...terminal().data.result, executor_task_id: '900719925474099399' })
  const writing = h.checks.apply(); await h.checks.apply(); assert.deepEqual(h.writes[0][1], { element_id: 0, task_id: '900719925474099399' }); h.checks.workbenchStarted({ element_id: 2 }); h.checks.workbenchResult({ element_id: 2, check_id: 'new' }); pending.resolve({ code: 200 }); assert.equal(await writing, false); assert.equal(h.checks.applied.value, false); assert.equal(h.checks.applying.value, false)
})
test('recovery accepts exactly scoped local observation and does not attach an unscoped legacy task', async t => {
  const h = elementsHarness(); t.after(h.cleanup); h.elementRows.value = [records.readElementRow(elementRow())]
  const owner = JSON.stringify([h.user.userId, h.user.roleId, h.user.selected_environment]); h.observations.set(`ui-element-check:${owner}:0`, { taskId: 'example-task', businessType: 'u_element_check', owner, environment: 0, meta: { pageId: 0, checkId: 'example-check' } })
  await h.checks.recover(); assert.equal(h.checks.pending.taskId, 'example-task'); assert.equal(h.checks.pending.loadingKey, '0')
})
test('active tasks without environment evidence remain uncertain and are rechecked instead of showing foreign results', async t => {
  let active = true; const h = elementsHarness({ api: { getActiveExecutorTasks: async () => ({ code: 200, data: active ? [{ task_id: 'unknown', business_type: 'u_element_check', business_id: 0, terminal: false }] : [] }) } }); t.after(h.cleanup); h.elementRows.value = [records.readElementRow(elementRow())]
  await h.checks.recover(); assert.equal(h.checks.pending.taskId, ''); assert.equal(h.checks.busy.value, true); assert.match(h.checks.error.value, /环境/); active = false; await h.tick(1500); assert.equal(h.checks.busy.value, false); assert.equal(h.checks.result.visible, false)
})
test('accepted late submission resumes after returning from the background without resubmitting', async t => {
  const pending = deferred(), h = elementsHarness({ api: { postUiElementCheck: () => pending.promise } }); t.after(h.cleanup); h.mount(); await flush()
  const checking = h.checks.start(elementRow(), 'normal'); h.visibility('hidden'); h.visibility('visible'); await flush(); pending.resolve(launch); await checking; await flush()
  assert.equal(h.checks.pending.taskId, 'example-task'); assert.equal(h.writes.filter(([name]) => name === 'postUiElementCheck').length, 1); assert.equal(h.checks.busy.value, true)
})
test('ambiguous dispatch failure checks active tasks before permitting a retry', async t => {
  const h = elementsHarness({ api: { postUiElementCheck: async () => { throw Error('Example connection lost') }, getActiveExecutorTasks: async () => ({ code: 200, data: [{ task_id: 'active', business_type: 'u_element_check', business_id: 0, terminal: false }] }) } }); t.after(h.cleanup); h.elementRows.value = [records.readElementRow(elementRow())]
  assert.equal(await h.checks.start(elementRow(), 'normal'), false); await flush(); await h.checks.start(elementRow(), 'normal'); assert.equal(h.checks.busy.value, true); assert.equal(h.writes.length, 1); assert.equal(h.checks.result.visible, false)
})
test('pagination refresh recovers the newly visible element task without choosing a foreign environment', async t => {
  const h = elementsHarness({ api: { getUiElement: async () => ({ code: 200, data: [elementRow({ id: 21 })], totalSize: 21 }) } }); t.after(h.cleanup)
  const owner = JSON.stringify([h.user.userId, h.user.roleId, h.user.selected_environment]); h.observations.set(`ui-element-check:${owner}:21`, { taskId: 'page-two-task', businessType: 'u_element_check', owner, environment: 0, meta: { pageId: 0, checkId: 'page-two-check' } })
  h.pagination.page = 2; await h.doRefresh(); assert.equal(h.checks.pending.element.id, 21); assert.equal(h.checks.pending.taskId, 'page-two-task'); assert.equal(h.checks.result.visible, false)
})
