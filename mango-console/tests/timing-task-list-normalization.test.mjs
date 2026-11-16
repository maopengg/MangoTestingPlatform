import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { setupTaskList, taskRow, taskRecent, taskResponse, taskListBase } from './helpers/timing-task-list-harness.mjs'

test('task list DTOs whitelist nested relations and preserve IDs, full paths and independent arrays', t => {
  const h = setupTaskList(); t.after(h.close); const dto = h.load('task-list-records.ts'), source = taskRow({ id: '90071992547409930000', secret: 'omit' }), row = dto.readTaskListRecord(source)
  assert.equal(row.id, source.id); assert.equal(row.project_product.id, 0); assert.equal(row.module.full_path, 'Root/Module'); assert.equal('secret' in row, false)
  row.test_envs.push(2); row.timing_strategies[0].name = 'Changed'; assert.deepEqual(source.test_envs, [0]); assert.equal(source.timing_strategies[0].name, 'Timing')
  for (const value of [{ code: 403 }, { code: 200, data: [], totalSize: '1' }, taskResponse([taskRow({ id: -1 })])]) assert.throws(() => dto.readTaskList(value))
})
test('recent DTOs use requested task IDs only and preserve retained statistics and report ID zero', t => {
  const h = setupTaskList(); t.after(h.close); const dto = h.load('task-list-records.ts')
  const result = dto.readTaskRecentResults({ code: 200, data: { 0: [taskRecent()], 1: [taskRecent({ report_retained: false, test_suite_id: null })], unrelated: 'omit' } }, [0,1])
  assert.deepEqual(Object.keys(result), ['0','1']); assert.equal(result[0][0].test_suite_id, 0); assert.equal(result[1][0].report_retained, false)
  assert.throws(() => dto.readTaskRecentResults({ code: 200, data: { 0: [taskRecent({ status_key: 'unknown' })] } }, [0]))
  assert.deepEqual(dto.readTaskRecentResults({ code: 200, data: {} }, [0]), { 0: [] })
})
test('平台受阻最近结果保留独立状态与计数，兼容旧响应缺少 blocked', t => {
  const h = setupTaskList(); t.after(h.close)
  const dto = h.load('task-list-records.ts')
  const result = dto.readTaskRecentResults({ code: 200, data: { 0: [taskRecent({ status: 6, status_key: 'blocked', blocked: 380, fail: 0 })] } }, [0])
  assert.equal(result[0][0].status_key, 'blocked')
  assert.equal(result[0][0].blocked, 380)
  assert.equal(result[0][0].fail, 0)
})
test('list, recent results and metadata have independent loading and include task ID zero', async t => {
  const list = deferred(), recent = deferred(), users = deferred(), h = setupTaskList({ getSystemTasks: () => list.promise, getSystemTaskRecentResults: () => recent.promise, getUserName: () => users.promise }); t.after(h.close)
  await h.mount(); assert.equal(h.listLoading.value, true); assert.equal(h.usersLoading.value, true); assert.equal(h.taskGroupOptionsLoading.value, false)
  list.resolve(taskResponse()); await flush(); assert.equal(h.listLoading.value, false); assert.equal(h.recentResultsLoading.value, true)
  assert.deepEqual(h.reads.find(read => read[0] === 'getSystemTaskRecentResults')[1], [0])
  recent.resolve({ code: 200, data: { 0: [taskRecent()] } }); await flush(); assert.equal(h.recentResultsLoading.value, false); assert.equal(h.usersLoading.value, true)
  users.resolve({ code: 200, data: [] }); await flush(); assert.equal(h.usersLoading.value, false); assert.equal(h.rows.value[0].id, 0)
})
test('search, reset, navigation and group drill-down use page one and collection protocol', async t => {
  const h = setupTaskList(); t.after(h.close); await h.mount()
  h.pagination.page = 6; h.conditionItems.find(item => item.key === 'status').value = [0,1]
  await h.onWorkbenchSearch(); const query = h.reads.filter(read => read[0] === 'getSystemTasks').at(-1)[1]
  assert.equal(query.page, 1); assert.equal(query.pageSize, 20); assert.equal(query.status__in, '0,1'); assert.equal('size' in query, false)
  await h.onSidebarFilterChange({ projectProduct: [1,0], module: [2,0], selectedModuleId: 0, moduleIds: [0,1] }); await flush()
  const moduleQuery = h.reads.filter(read => read[0] === 'getSystemTasks').at(-1)[1]
  assert.equal(moduleQuery.project_product, 0); assert.equal(moduleQuery.module, 0); assert.equal('module__in' in moduleQuery, false); assert.equal(h.taskGroupFilters.navigation_module_id, 0)
  h.pagination.page = 4; await h.filterTasksByGroup({ id: 0, name: 'Zero group' }); assert.equal(h.reads.filter(read => read[0] === 'getSystemTasks').at(-1)[1].task_group__in, '0')
  h.pagination.page = 7; await h.onResetSearch(); assert.equal(h.pagination.page, 1)
  for (const item of h.conditionItems) assert.deepEqual(item.value, item.multiple ? [] : '')
  const resetQuery = h.reads.filter(read => read[0] === 'getSystemTasks').at(-1)[1]; assert.deepEqual(resetQuery, { page: 1, pageSize: 20 })
})
test('module subtree filters keep the full ID list while exact selected module wins', async t => {
  const h = setupTaskList(); t.after(h.close); await h.mount()
  await h.onSidebarFilterChange({ projectProduct: 1, moduleIds: [0,'90071992547409930000'] })
  const query = h.reads.filter(read => read[0] === 'getSystemTasks').at(-1)[1]
  assert.equal(query.module__in, '0,90071992547409930000'); assert.equal('module' in query, false)
})
test('latest list response wins and stale recent results cannot replace a new page', async t => {
  const first = deferred(), second = deferred(), oldRecent = deferred(); let calls = 0
  const h = setupTaskList({ getSystemTasks: () => ++calls === 1 ? first.promise : second.promise, getSystemTaskRecentResults: ids => ids[0] === 0 ? oldRecent.promise : Promise.resolve({ code: 200, data: { 1: [] } }) }); t.after(h.close)
  await h.mount(); const latest = h.doRefresh(); second.resolve(taskResponse([taskRow({ id: 1 })])); await latest; await flush()
  first.resolve(taskResponse()); await flush(); assert.equal(h.rows.value[0].id, 1); assert.equal(h.listLoading.value, false)
  oldRecent.resolve({ code: 200, data: { 0: [taskRecent()] } }); await flush(); assert.deepEqual(h.recentResults.value, { 1: [] })
})
test('recent result request from an already displayed row is invalidated by a new list', async t => {
  const old = deferred(); let calls = 0
  const h = setupTaskList({ getSystemTasks: async () => taskResponse([taskRow({ id: calls++ ? 1 : 0 })]), getSystemTaskRecentResults: ids => ids[0] === 0 ? old.promise : Promise.resolve({ code: 200, data: { 1: [] } }) }); t.after(h.close)
  await h.mount(); assert.equal(h.recentResultsLoading.value, true); await h.doRefresh(); await flush()
  old.resolve({ code: 200, data: { 0: [taskRecent()] } }); await flush(); assert.deepEqual(h.recentResults.value, { 1: [] })
})
test('pagination clamps after count decreases and refetches the valid page', async t => {
  const h = setupTaskList({ getSystemTasks: async query => taskResponse([taskRow()], query.page === 5 ? 22 : 22) }); t.after(h.close); await h.mount()
  h.pagination.page = 5; await h.doRefresh(); assert.equal(h.pagination.page, 2)
  assert.deepEqual(h.reads.filter(read => read[0] === 'getSystemTasks').slice(-2).map(read => read[1].page), [5,2]); assert.equal(h.pagination.pageCount, 22)
})
test('list/recent/metadata failures retain data, release loading and allow independent retry', async t => {
  let failList = false, failRecent = false, failUsers = true, failGroup = true
  const h = setupTaskList({ getSystemTasks: async () => failList ? { code: 403 } : taskResponse(), getSystemTaskRecentResults: async () => { if (failRecent) throw Error('network'); return { code: 200, data: { 0: [] } } },
    getUserName: async () => { if (failUsers) throw Error('network'); return { code: 200, data: [] } }, getScheduledTaskGroupOptions: async () => ({ code: failGroup ? 403 : 200, data: [] }) }); t.after(h.close)
  await h.mount(); assert.match(h.usersError.value, /负责人/); assert.match(h.taskGroupOptionsError.value, /任务组/); assert.equal(h.rows.value.length, 1)
  failList = true; await h.doRefresh(); assert.match(h.listError.value, /失败/); assert.equal(h.listLoading.value, false); assert.equal(h.rows.value.length, 1)
  failList = false; failRecent = true; await h.doRefresh(); await flush(); assert.match(h.recentError.value, /失败/); assert.equal(h.recentResultsLoading.value, false); assert.equal(h.listError.value, '')
  failRecent = false; await h.list.loadRecentResults(); failUsers = false; failGroup = false; await Promise.all([h.getNickName(), h.loadTaskGroupOptions()])
  assert.equal(h.recentError.value, ''); assert.equal(h.usersError.value, ''); assert.equal(h.taskGroupOptionsError.value, '')
})
test('late group options from another product cannot overwrite the current product', async t => {
  const first = deferred(), second = deferred()
  const h = setupTaskList({ getScheduledTaskGroupOptions: product => product === 1 ? first.promise : product === 2 ? second.promise : Promise.resolve({ code: 200, data: [] }) }); t.after(h.close); await h.mount()
  await h.onSidebarFilterChange({ projectProduct: 1 }); await h.onSidebarFilterChange({ projectProduct: 2 })
  second.resolve({ code: 200, data: [{ key: 2, title: 'Current' }] }); await flush(); first.resolve({ code: 200, data: [{ key: 1, title: 'Old' }] }); await flush()
  assert.equal(h.conditionItems.find(item => item.key === 'task_group').optionItems[0].title, 'Current'); assert.equal(h.taskGroupOptionsLoading.value, false)
})
test('delete uses fixed ID, blocks duplicate confirmation and keeps failed confirmation retryable', async t => {
  const pending = deferred(); let calls = 0
  const h = setupTaskList({ deleteSystemTasks: () => ++calls === 1 ? pending.promise : Promise.resolve({ code: 200 }) }); t.after(h.close); await h.mount()
  const source = h.rows.value[0]; h.onDelete(source); const confirmation = h.confirmations.at(-1); source.id = 9
  const deleting = confirmation.config.onBeforeOk(); assert.equal(await confirmation.config.onBeforeOk(), false); assert.equal(h.writes.length, 1); assert.equal(h.writes[0][1], 0)
  pending.resolve({ code: 403 }); assert.equal(await deleting, false); assert.equal(confirmation.closed, false); assert.match(h.operationError.value, /删除失败/); assert.deepEqual(h.deletingIds.value, [])
  assert.equal(await confirmation.config.onBeforeOk(), true); assert.equal(confirmation.closed, true); assert.deepEqual(h.writeIds.value, [])
})
test('successful delete with failed reload remains a successful write and exposes a separate read error', async t => {
  let fail = false
  const h = setupTaskList({ deleteSystemTasks: async () => { fail = true; return { code: 200 } }, getSystemTasks: async () => { if (fail) throw Error('read'); return taskResponse() } }); t.after(h.close); await h.mount()
  h.onDelete(h.rows.value[0]); const confirmation = h.confirmations.at(-1); assert.equal(await confirmation.config.onBeforeOk(), true); await flush()
  assert.equal(confirmation.closed, true); assert.equal(h.operationError.value, ''); assert.match(h.listError.value, /加载失败/)
})
test('cancelled deletion confirmation cannot later execute its captured callback', async t => {
  const h = setupTaskList(); t.after(h.close); await h.mount(); h.onDelete(h.rows.value[0]); const confirmation = h.confirmations.at(-1)
  confirmation.config.onCancel(); assert.equal(await confirmation.config.onBeforeOk(), false); assert.equal(h.writes.length, 0)
})
test('trigger preparation and fine-tuning preparation ignore superseded capacity responses', async t => {
  const first = deferred(), second = deferred(); let calls = 0
  const h = setupTaskList({ getSystemTaskExecutionOptions: () => ++calls === 1 ? first.promise : second.promise }); t.after(h.close); await h.mount()
  const old = h.onTrigger(h.rows.value[0]); const current = h.onEdit(h.load('task-list-records.ts').readTaskListRecord(taskRow({ id: 2, task_group: 0 })))
  second.resolve({ code: 200, data: { api_platform_limit: 4 } }); await current; first.resolve({ code: 200, data: { api_platform_limit: 99 } }); await old
  assert.equal(h.triggerShell.opened.length, 0); assert.equal(h.fineShell.opened.length, 1); assert.equal(h.fineShell.opened[0].id, 2); assert.equal(h.apiPlatformLimit.value, 4)
})
test('trigger snapshots task/environment parameters, prevents double writes and survives cancellation without reopening', async t => {
  const pending = deferred(), h = setupTaskList({ postSystemTriggerManual: () => pending.promise }); t.after(h.close); await h.mount(); const source = h.rows.value[0]
  await h.onTrigger(source); source.id = 9; const config = { executionName: 'Temporary', testEnv: null, testEnvs: [0,2], apiConcurrencyLimit: 3 }
  const writing = h.onConfirmTrigger(config); config.testEnvs.push(1); await h.onConfirmTrigger(config); assert.equal(h.writes.length, 1)
  assert.deepEqual(h.writes[0], ['postSystemTriggerManual',0,3,[0,2]])
  h.onCancelTrigger(); await h.onTrigger(h.load('task-list-records.ts').readTaskListRecord(taskRow({ id: 2 }))); assert.equal(h.triggerShell.visible, false); assert.equal(h.triggerSaving.value, true)
  pending.resolve({ code: 200 }); await writing; assert.equal(h.triggerShell.visible, false); assert.equal(h.triggerSaving.value, false); assert.deepEqual(h.messages, [])
})
test('capacity and trigger failures release their loading and retry the same window', async t => {
  let failCapacity = true, failWrite = true
  const h = setupTaskList({ getSystemTaskExecutionOptions: async () => ({ code: failCapacity ? 403 : 200, data: { api_platform_limit: 8 } }), postSystemTriggerManual: async () => ({ code: failWrite ? 403 : 200 }) }); t.after(h.close); await h.mount()
  await h.onTrigger(h.rows.value[0]); assert.equal(h.triggerShell.visible, false); assert.match(h.executionOptionsError.value, /容量/); assert.equal(h.executionOptionsLoading.value, false)
  failCapacity = false; await h.onTrigger(h.rows.value[0]); h.triggerShell.loading = true
  assert.equal(await h.onConfirmTrigger({ executionName: '', testEnv: null, testEnvs: [0], apiConcurrencyLimit: null }), false)
  assert.match(h.triggerError.value, /失败/); assert.equal(h.triggerShell.visible, true); assert.equal(h.triggerShell.loading, false)
  failWrite = false; assert.equal(await h.onConfirmTrigger({ executionName: '', testEnv: null, testEnvs: [0], apiConcurrencyLimit: null }), true); assert.equal(h.triggerShell.visible, false)
})
test('switch writes are immutable, serialized per task and keep notification dependencies', async t => {
  const pending = deferred(); let server = taskRow()
  const h = setupTaskList({ getSystemTasks: async () => taskResponse([server]), putSystemTasks: async payload => { await pending.promise; server = { ...server, ...payload }; return { code: 200 } } }); t.after(h.close); await h.mount()
  const record = h.rows.value[0], writing = h.onModifyStatus(false, record, 'is_notice')
  assert.equal(await h.onModifyStatus(true, record, 'status'), false); assert.equal(h.writes.length, 1); assert.deepEqual(h.writes[0][1], { id: 0, is_notice: 0, fail_notice: 0 })
  pending.resolve(); assert.equal(await writing, true); await flush(); assert.equal(record.is_notice, 1); assert.equal(h.rows.value[0].is_notice, 0); assert.deepEqual(h.writeIds.value, [])
  assert.equal(await h.onModifyStatus(true, h.rows.value[0], 'fail_notice'), false); assert.equal(h.writes.length, 1)
})
test('group task switches use member protocol and preserve task group ID zero and long member IDs', async t => {
  const h = setupTaskList({ getSystemTasks: async () => taskResponse([taskRow({ task_group: 0, task_group_member_id: '90071992547409930000' })]) }); t.after(h.close); await h.mount()
  const record = h.rows.value[0]; assert.equal(await h.onModifyStatus(true, record, 'status'), true)
  assert.deepEqual(h.writes[0], ['updateScheduledTaskGroupMemberStatus',0,'90071992547409930000',true])
  assert.equal(await h.onModifyStatus(true, record, 'is_notice'), false); h.onDelete(record); assert.equal(h.confirmations.length, 0)
})
test('malformed group status acknowledgement is distinguished from failure and reloads authoritative state', async t => {
  const h = setupTaskList({ getSystemTasks: async () => taskResponse([taskRow({ task_group: 1, task_group_member_id: 2 })]), updateScheduledTaskGroupMemberStatus: async () => ({ code: 200, data: {} }) }); t.after(h.close); await h.mount()
  const before = h.reads.filter(read => read[0] === 'getSystemTasks').length
  assert.equal(await h.onModifyStatus(true, h.rows.value[0], 'status'), false); assert.match(h.operationError.value, /已提交.*返回结果异常/)
  await flush(); assert.equal(h.reads.filter(read => read[0] === 'getSystemTasks').length, before + 1); assert.deepEqual(h.writeIds.value, [])
})
test('retention editor owns summary/draft, failed save keeps it, successful save replaces current row only', async t => {
  let fail = true, server = taskRow()
  const h = setupTaskList({ getSystemTasks: async () => taskResponse([server]), putSystemTasks: async payload => { if (fail) throw Error('network'); server = { ...server, ...payload }; return { code: 200 } } }); t.after(h.close); await h.mount()
  const source = h.rows.value[0]; h.openRetentionEditor(source); h.retentionEditor.value = 'abnormal_only'; source.name = 'Later name'
  assert.equal(h.retentionEditor.record.name, 'Example task'); assert.equal(await h.saveRetentionPolicy(), false); assert.equal(h.retentionEditor.visible, true); assert.match(h.retentionError.value, /失败/)
  fail = false; assert.equal(await h.saveRetentionPolicy(), true); await flush(); assert.equal(h.retentionEditor.visible, false); assert.equal(h.rows.value[0].report_retention_policy, 'abnormal_only'); assert.equal(source.report_retention_policy, 'all')
})
test('retention cancellation keeps physical write lock until settlement and never updates a replacement window', async t => {
  const pending = deferred(), h = setupTaskList({ putSystemTasks: () => pending.promise }); t.after(h.close); await h.mount()
  h.openRetentionEditor(h.rows.value[0]); h.retentionEditor.value = 'abnormal_only'; const writing = h.saveRetentionPolicy(); await h.saveRetentionPolicy(); h.closeRetention()
  h.openRetentionEditor(h.load('task-list-records.ts').readTaskListRecord(taskRow({ id: 2 }))); assert.equal(h.retentionEditor.visible, false); assert.equal(h.writes.length, 1)
  pending.resolve({ code: 200 }); assert.equal(await writing, false); assert.equal(h.retentionEditor.visible, false); assert.deepEqual(h.messages, []); assert.equal(h.retentionSaving.value, false)
})
test('identity changes clear prior rows, options and windows and suppress pending writes without unlocking early', async () => {
  for (const change of [h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/elsewhere', h => h.route.fullPath += '?id=2']) {
    const pending = deferred(), h = setupTaskList({ putSystemTasks: () => pending.promise })
    try {
      await h.mount(); const record = h.rows.value[0]; h.openRetentionEditor(record); const writing = h.saveRetentionPolicy(); h.openTaskDiagnostic(record); h.openOfflineReport(record); change(h)
      assert.equal(h.retentionEditor.visible, false); assert.equal(h.diagnosticDrawer.visible, false); assert.equal(h.offlineExport.visible, false); assert.equal(h.rows.value.length, 0)
      assert.equal(await h.onModifyStatus(true, record, 'status'), false); assert.equal(h.writes.length, 1)
      pending.resolve({ code: 200 }); await writing; assert.deepEqual(h.messages, []); assert.deepEqual(h.writeIds.value, [])
    } finally { h.close() }
  }
})
test('background and KeepAlive invalidate pending reads and resume without leaking stale rows', async () => {
  for (const mode of ['background','deactivate','unmount']) {
    const pending = deferred(); let calls = 0
    const h = setupTaskList({ getSystemTasks: () => ++calls === 1 ? pending.promise : Promise.resolve(taskResponse([taskRow({ id: 2 })])) })
    try {
      await h.mount(); if (mode === 'background') h.visibility('hidden'); else h.callbacks[mode].forEach(fn => fn())
      assert.equal(h.listLoading.value, false); pending.resolve(taskResponse()); await flush(); assert.deepEqual(h.rows.value, [])
      if (mode === 'background') h.visibility('visible'); if (mode === 'deactivate') h.callbacks.activate.forEach(fn => fn())
      await flush(); assert.equal(h.rows.value.length, mode === 'unmount' ? 0 : 1); if (mode !== 'unmount') assert.equal(h.rows.value[0].id, 2)
    } finally { h.close() }
  }
})
test('write finishing after the page returns refreshes current data without stale success feedback', async t => {
  const pending = deferred(); let server = taskRow()
  const h = setupTaskList({ getSystemTasks: async () => taskResponse([server]), putSystemTasks: async payload => { await pending.promise; server = { ...server, ...payload }; return { code: 200 } } }); t.after(h.close)
  await h.mount(); h.openRetentionEditor(h.rows.value[0]); h.retentionEditor.value = 'abnormal_only'; const saving = h.saveRetentionPolicy()
  h.visibility('hidden'); h.visibility('visible'); await flush(); assert.equal(h.rows.value[0].report_retention_policy, 'all')
  pending.resolve(); await saving; await flush(); assert.equal(h.rows.value[0].report_retention_policy, 'abnormal_only'); assert.equal(h.retentionEditor.visible, false); assert.deepEqual(h.messages, [])
})
test('late owner options after identity switch cannot replace the new identity options', async t => {
  const old = deferred(); let calls = 0
  const h = setupTaskList({ getUserName: () => ++calls === 1 ? old.promise : Promise.resolve({ code: 200, data: [{ key: 2, title: 'New owner' }] }) }); t.after(h.close)
  await h.mount(); h.user.userId++; await flush(); assert.equal(h.userOptions.value[0].title, 'New owner')
  old.resolve({ code: 200, data: [{ key: 1, title: 'Old owner' }] }); await flush(); assert.equal(h.userOptions.value[0].title, 'New owner'); assert.equal(h.usersLoading.value, false)
})
test('delete responses after background or unmount cannot emit stale success', async () => {
  for (const mode of ['background','deactivate','unmount']) {
    const pending = deferred(), h = setupTaskList({ deleteSystemTasks: () => pending.promise })
    try {
      await h.mount(); h.onDelete(h.rows.value[0]); const confirmation = h.confirmations.at(-1), writing = confirmation.config.onBeforeOk()
      if (mode === 'background') h.visibility('hidden'); else h.callbacks[mode].forEach(fn => fn())
      assert.equal(confirmation.closed, true); assert.deepEqual(h.writeIds.value, ['0']); pending.resolve({ code: 200 }); assert.equal(await writing, false); assert.deepEqual(h.messages, []); assert.deepEqual(h.writeIds.value, [])
    } finally { h.close() }
  }
})
test('trigger write finishing in background, KeepAlive or after unmount cannot reopen a window or report old success', async () => {
  for (const mode of ['background','deactivate','unmount']) {
    const pending = deferred(), h = setupTaskList({ postSystemTriggerManual: () => pending.promise })
    try {
      await h.mount(); await h.onTrigger(h.rows.value[0]); const writing = h.onConfirmTrigger({ executionName: 'Example', testEnv: null, testEnvs: [0], apiConcurrencyLimit: null })
      if (mode === 'background') h.visibility('hidden'); else h.callbacks[mode].forEach(fn => fn())
      assert.equal(h.triggerShell.visible, false); assert.equal(h.triggerSaving.value, true); pending.resolve({ code: 200 }); await writing
      assert.deepEqual(h.messages, []); assert.equal(h.triggerSaving.value, false); assert.equal(h.triggerShell.visible, false); assert.deepEqual(h.writeIds.value, [])
    } finally { h.close() }
  }
})
test('report/case navigation guards absent results and preserves zero product/module/report IDs', async t => {
  const h = setupTaskList(); t.after(h.close); await h.mount()
  h.openRecentResult(); h.openRecentResult(taskRecent({ report_retained: false, test_suite_id: null })); h.openRecentResult(taskRecent({ test_suite_id: null })); assert.equal(h.navigation.length, 0)
  h.openRecentResult(taskRecent()); assert.equal(h.navigation.at(-1).query.id, 0)
  h.onClick(h.rows.value[0]); assert.equal(h.navigation.at(-1).query.module_id, 0); assert.equal(h.navigation.at(-1).query.project_product_id, 0)
})
test('ordinary edit and navigation defaults delegate only the selected record/selection', async t => {
  const h = setupTaskList(); t.after(h.close); await h.mount(); h.navigationCreateRef.value = { getCreateDefaults: () => ({ projectProduct: 0, module: 0 }) }
  h.onAdd(); assert.deepEqual(h.editorShell.opened.at(-1), { projectProduct: 0, module: 0 }); await h.onEdit(h.rows.value[0]); assert.equal(h.editorShell.opened.at(-1).id, 0)
  h.openTaskGroupCreate(); assert.deepEqual(h.groupCalls.at(-1), ['create',0])
  h.activeTab.value = 'groups'; await flush(); assert.equal(h.triggerShell.visible, false); h.activeTab.value = 'tasks'; await flush(); assert.equal(h.listLoading.value, false)
})
test('main list scripts/templates/styles compile without a mixed page data object or unsafe state types', async () => {
  const filename = path.join(taskListBase,'index.vue'), source = readFileSync(filename,'utf8'), { descriptor, errors } = parse(source,{ filename }); assert.deepEqual(errors, [])
  assert.doesNotMatch(descriptor.scriptSetup.content, /\bany\b|const data = reactive|useTable\(/)
  assert.match(descriptor.template.content, /v-if="recentError && !recentResults\[String\(record.id\)\]\?\.length"/)
  const script = compileScript(descriptor,{ id: 'task-list' }), template = compileTemplate({ source: descriptor.template.content, filename, id: 'task-list', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
  assert.deepEqual([...new Set([...template.code.matchAll(/_ctx\.([A-Za-z_$]\w*)/g)].map(match => match[1]))].filter(name => !(name in script.bindings)), [], 'template handlers must resolve to actual setup bindings')
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: 'task-list', scoped: true })).errors, [])
})
