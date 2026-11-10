import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { monitoringHarness, taskRecord } from './helpers/monitoring-task-harness.mjs'

const calls = (h, method) => h.calls.filter(([name]) => name === method)
const page = (rows, total = rows.length) => ({ code: 200, data: rows, totalSize: total })

test('initial task page/detail use finite snapshots, local loading and enum keys', async () => {
  const h = monitoringHarness(); assert.equal(h.taskListLoading.value, true); await flush()
  assert.deepEqual(calls(h, 'getMonitoringTask')[0][1], { page: 1, pageSize: 20 })
  assert.equal(h.workspaceTaskId.value, 1); assert.equal(h.workspaceCodeText.value, 'print(1)'); assert.equal(h.workspaceReady.value, true)
  assert.equal(h.workspaceTask.value.test_env, 0); assert.equal(h.workspaceTask.value.notice_group, null); assert.equal(h.monitoringTaskStatusText(taskRecord()), '待执行')
  h.dispose()
})
test('task list factories and search values are per-instance; query maps product leaf zero and omits empty values', async () => {
  const a = monitoringHarness(), b = monitoringHarness(); await flush()
  a.taskName.value = ' Example '; await a.onSidebarFilterChange({ projectProduct: [5, 0] })
  assert.deepEqual(calls(a, 'getMonitoringTask').at(-1)[1], { page: 1, pageSize: 20, name: 'Example', project_product: 0 })
  assert.equal(a.currentProjectProductLabel.value, 'Project/Product'); assert.equal(b.currentProjectProductLabel.value, '全部产品')
  assert.equal(b.taskName.value, ''); assert.equal(b.conditionItems[1].value, null)
  a.dispose(); b.dispose()
})
test('append pagination deduplicates overlapping rows including duplicates within a page', async () => {
  const h = monitoringHarness({ api: { getMonitoringTask: query => query.page === 1 ? page([taskRecord(1)], 3) : page([taskRecord(1), taskRecord(2), taskRecord(2, { name: 'latest' }), taskRecord(3)], 3) } }); await flush()
  await h.tasks.load(true); assert.equal(h.taskPaging.page, 2); assert.deepEqual(h.taskRows.value.map(row => row.id), [1, 2, 3]); assert.equal(h.taskRows.value[1].name, 'latest')
  await h.tasks.load(true); assert.equal(calls(h, 'getMonitoringTask').length, 2); h.dispose()
})
test('append failure retains rows and page and retries the same page', async () => {
  let fail = true
  const h = monitoringHarness({ api: { getMonitoringTask: query => { if (query.page === 2 && fail) throw Error('offline'); return page([taskRecord(query.page)], 2) } } }); await flush()
  await h.tasks.load(true); assert.equal(h.taskListFailed.value, true); assert.equal(h.taskPaging.page, 1); assert.deepEqual(h.taskRows.value.map(row => row.id), [1])
  fail = false; await h.tasks.retry(); assert.equal(h.taskPaging.page, 2); assert.equal(h.taskListFailed.value, false); h.dispose()
})
test('new query invalidates previous append and its finally cannot stop current loading', async () => {
  const append = deferred(), latest = deferred(); let count = 0
  const h = monitoringHarness({ api: { getMonitoringTask: () => ++count === 1 ? page([taskRecord()], 2) : count === 2 ? append.promise : latest.promise } }); await flush()
  const a = h.tasks.load(true); h.taskName.value = 'new'; const b = h.onTaskSearch()
  append.resolve(page([taskRecord(2)], 2)); await a; assert.equal(h.taskListLoading.value, true)
  latest.resolve(page([taskRecord(3)], 1)); await b; await flush(); assert.deepEqual(h.taskRows.value.map(row => row.id), [3]); h.dispose()
})
test('same query while pending coalesces but mutation refresh forces a newer read', async () => {
  const jobs = [deferred(), deferred()]; let count = 0
  const h = monitoringHarness({ api: { getMonitoringTask: () => jobs[count++].promise } })
  const a = h.tasks.load(), b = h.tasks.load(); assert.equal(a, b); assert.equal(count, 1)
  h.onEditorSaved(); assert.equal(count, 2); jobs[1].resolve(page([taskRecord(2)])); await flush()
  jobs[0].resolve(page([taskRecord(1)])); await a; assert.equal(h.taskRows.value[0].id, 2); h.dispose()
})
test('malformed page and request failure keep the successful snapshot and total for retry', async () => {
  let broken = null; const h = monitoringHarness({ api: { getMonitoringTask: () => broken || page([taskRecord()], 8) } }); await flush()
  for (const bad of [{ code: 300, data: [], totalSize: 0 }, { code: 200, data: [{}], totalSize: 2 }, { code: 200, data: [], totalSize: 'bad' }]) {
    broken = bad; await h.tasks.load(); assert.equal(h.taskRows.value[0].id, 1); assert.equal(h.taskPaging.total, 8); assert.equal(h.taskListFailed.value, true)
  }
  broken = null; await h.tasks.load(); assert.equal(h.taskListFailed.value, false); h.dispose()
})
test('detail failure disables save/run until successful retry instead of treating empty code as loaded', async () => {
  let fail = true; const h = monitoringHarness({ api: { getMonitoringTaskDetail: id => { if (fail) throw Error('offline'); return { code: 200, data: taskRecord(id) } } } }); await flush()
  assert.equal(h.workspace.loadFailed.value, true); assert.equal(h.workspaceReady.value, false); assert.equal(await h.runWorkspaceTask(), false)
  fail = false; await h.workspace.retryLoad(); assert.equal(h.workspaceReady.value, true); assert.equal(h.workspaceCodeText.value, 'print(1)'); h.dispose()
})
test('selecting a new task invalidates late detail and keeps its code', async () => {
  const old = deferred(); const h = monitoringHarness({ api: { getMonitoringTaskDetail: id => id === 1 ? old.promise : { code: 200, data: taskRecord(id) } } }); await flush()
  await h.selectWorkspaceTask(taskRecord(2)); old.resolve({ code: 200, data: taskRecord(1) }); await flush()
  assert.equal(h.workspaceTaskId.value, 2); assert.equal(h.workspaceCodeText.value, 'print(2)'); h.dispose()
})
test('save failure retains dirty code and prevents selection and start; retry succeeds', async () => {
  let fail = true; const h = monitoringHarness({ api: { putMonitoringTask: () => { if (fail) throw Error('offline'); return { code: 200, msg: 'ok' } } } }); await flush()
  h.workspaceCodeText.value = 'changed'; await h.selectWorkspaceTask(taskRecord(2)); assert.equal(h.workspaceTaskId.value, 1); assert.equal(h.workspaceDirty.value, true)
  assert.equal(h.workspace.saveFailed.value, true)
  assert.equal(await h.runWorkspaceTask(), false); assert.equal(calls(h, 'postMonitoringTaskStart').length, 0)
  fail = false; await h.selectWorkspaceTask(taskRecord(2)); assert.equal(h.workspaceTaskId.value, 2); h.dispose()
})
test('pending start survives a scope reset physically but cannot affect the new workspace or open old logs', async () => {
  const pending = deferred(), h = monitoringHarness({ api: { postMonitoringTaskStart: () => pending.promise } }); await flush()
  const job = h.runWorkspaceTask(); await flush(); h.user.token = 'other'; await flush()
  assert.equal(h.workspaceActionLoading.value, true); assert.equal(await h.runWorkspaceTask(), false)
  pending.resolve({ code: 200, data: taskRecord(1, { status: 5 }), msg: 'old-start' }); assert.equal(await job, false)
  assert.equal(h.logPanelVisible.value, false); assert.equal(h.messages.some(([, text]) => text === 'old-start'), false); h.dispose()
})
test('queued task selection cannot move an in-progress run to another task', async () => {
  const pending = deferred(), h = monitoringHarness({ api: { putMonitoringTask: () => pending.promise } }); await flush()
  h.workspaceCodeText.value = 'changed'; const choice = h.selectWorkspaceTask(taskRecord(2)), job = h.runWorkspaceTask()
  pending.resolve({ code: 200, msg: 'saved' }); await Promise.all([choice, job]); assert.equal(calls(h, 'postMonitoringTaskStart')[0][1], 1); h.dispose()
})
test('environment and route A-B-A ignore old detail responses after current workspace reload', async () => {
  for (const change of [h => { h.user.selected_environment = 2; h.user.selected_environment = 0 }, h => { h.route.fullPath = '/other'; h.route.fullPath = '/monitoring/task/index' }]) {
    const pending = deferred(); let id = 1
    const h = monitoringHarness({ api: { getMonitoringTask: () => page([taskRecord(id)]), getMonitoringTaskDetail: value => value === 1 ? pending.promise : { code: 200, data: taskRecord(value) } } }); await flush()
    id = 2; change(h); await flush(); pending.resolve({ code: 200, data: taskRecord(1) }); await flush()
    assert.equal(h.workspaceTaskId.value, 2); assert.equal(h.workspaceCodeText.value, 'print(2)'); h.dispose()
  }
})
test('read-only state arriving after a code write cannot restore the old server code', async () => {
  const stale = deferred(); let detail = 0
  const h = monitoringHarness({ api: { getMonitoringTaskDetail: id => ++detail === 1 ? { code: 200, data: taskRecord(id) } : stale.promise } }); await flush()
  const read = h.workspace.refreshState(); h.workspaceCodeText.value = 'new'; await h.saveWorkspaceCode(false)
  stale.resolve({ code: 200, data: taskRecord(1) }); await read; assert.equal(h.workspaceCodeText.value, 'new'); assert.equal(h.workspaceDirty.value, false); h.dispose()
})
test('autosave drains newest edits serially and run waits for both writes before starting captured task', async () => {
  const first = deferred(), second = deferred(); let writes = 0
  const h = monitoringHarness({ api: { putMonitoringTask: () => ++writes === 1 ? first.promise : second.promise } }); await flush()
  h.workspaceCodeText.value = 'A'; const saving = h.saveWorkspaceCode(false), running = h.runWorkspaceTask()
  h.workspaceCodeText.value = 'B'; first.resolve({ code: 200, msg: 'saved A' }); await flush()
  assert.deepEqual(calls(h, 'putMonitoringTask').map(row => row[1].script_content), ['A', 'B']); assert.equal(calls(h, 'postMonitoringTaskStart').length, 0)
  second.resolve({ code: 200, msg: 'saved B' }); await Promise.all([saving, running]); await flush()
  assert.equal(calls(h, 'postMonitoringTaskStart')[0][1], 1); assert.equal(h.workspaceDirty.value, false); assert.equal(h.fileSaving.value, false)
  assert.equal(h.logPanelVisible.value, true); h.dispose()
})
test('identity A-B-A during autosave never starts a task or acknowledges old draft', async () => {
  const pending = deferred(), h = monitoringHarness({ api: { putMonitoringTask: () => pending.promise } }); await flush()
  h.workspaceCodeText.value = 'changed'; const job = h.runWorkspaceTask(); h.user.token = 'other'; h.user.token = 'fixture-token'; await flush()
  assert.equal(h.fileSaving.value, true); assert.equal(h.workspaceActionLoading.value, true)
  pending.resolve({ code: 200, msg: 'old' }); await job; assert.equal(calls(h, 'postMonitoringTaskStart').length, 0)
  assert.equal(h.messages.some(([, text]) => text === 'old'), false); assert.equal(h.fileSaving.value, false); h.dispose()
})
test('physical control lock survives invalidation; raw response relations cannot corrupt typed task metadata', async () => {
  const pending = deferred(); const h = monitoringHarness({ api: { postMonitoringTaskStart: () => pending.promise } }); await flush()
  const job = h.runWorkspaceTask(); await flush(); await h.runWorkspaceTask(); assert.equal(calls(h, 'postMonitoringTaskStart').length, 1)
  pending.resolve({ code: 200, data: { ...taskRecord(), project_product: 0, notice_group: 0, status: 5, pid: 20 }, msg: 'ok' }); await job
  assert.equal(typeof h.workspaceTask.value.project_product, 'object'); assert.equal(h.monitoringTaskStatusText(taskRecord(1, { status: 5, pid: 20 })), '启动中'); h.dispose()
})
test('stale state request before start cannot overwrite successful control state', async () => {
  const stale = deferred(); let details = 0
  const h = monitoringHarness({ api: { getMonitoringTaskDetail: id => ++details === 1 ? { code: 200, data: taskRecord(id) } : details === 2 ? stale.promise : { code: 200, data: taskRecord(id, { status: 5 }) } } }); await flush()
  const read = h.workspace.refreshState(); const run = h.runWorkspaceTask(); await run
  assert.equal(h.workspaceTask.value.status, 5); stale.resolve({ code: 200, data: taskRecord() }); await read; await flush()
  assert.equal(h.workspaceTask.value.status, 5); assert.equal(h.workspaceActionLoading.value, false); h.dispose()
})
test('clean code refreshes from server while an edited draft survives metadata refresh', async () => {
  const h = monitoringHarness(); await flush()
  h.tasks.updateTask(taskRecord(1, { script_content: 'server change' })); assert.equal(h.workspaceCodeText.value, 'server change')
  h.workspaceCodeText.value = 'draft'; h.tasks.updateTask(taskRecord(1, { script_content: 'another server change' }))
  assert.equal(h.workspaceCodeText.value, 'draft'); assert.equal(h.workspaceDirty.value, true); h.dispose()
})
test('runtime patches never replace the selected task solely because it is outside the currently loaded list', async () => {
  const h = monitoringHarness(); await flush(); await h.workspace.load(taskRecord(55))
  h.tasks.updateTask(taskRecord(55), false); assert.equal(h.workspaceTaskId.value, 55)
  await h.tasks.load(); await flush(); assert.equal(h.workspaceTaskId.value, 1); h.dispose()
})
test('invalid control responses never report success and can be retried', async () => {
  let bad = true; const h = monitoringHarness({ api: { postMonitoringTaskStart: id => ({ code: 200, data: taskRecord(bad ? 99 : id), msg: 'must-not-report-wrong-task' }) } }); await flush()
  assert.equal(await h.runWorkspaceTask(), false); assert.equal(h.messages.some(([kind]) => kind === 'success'), false)
  bad = false; assert.equal(await h.runWorkspaceTask(), true); h.dispose()
})
test('stop preserves business state and physical mutex while pending, then closes logs after acknowledgement', async () => {
  const pending = deferred(); let stopped = false
  const running = id => taskRecord(id, { status: stopped ? 2 : 1, pid: stopped ? null : 25 })
  const h = monitoringHarness({ api: { getMonitoringTask: () => page([running(1)]), getMonitoringTaskDetail: id => ({ code: 200, data: running(id) }), postMonitoringTaskStop: () => pending.promise } }); await flush(); h.logs.open(); await flush()
  const job = h.stopWorkspaceTask(); assert.equal(await h.stopWorkspaceTask(), false); assert.equal(calls(h, 'postMonitoringTaskStop').length, 1)
  stopped = true; pending.resolve({ code: 200, data: running(1), msg: 'stopped' }); assert.equal(await job, true); await flush()
  assert.equal(h.logPanelVisible.value, false); assert.equal(h.workspace.processActive.value, false); assert.equal(h.workspaceActionLoading.value, false); h.dispose()
})
test('non-success code save retains dirty draft and allows explicit retry', async () => {
  let fail = true; const h = monitoringHarness({ api: { putMonitoringTask: () => ({ code: fail ? 300 : 200, msg: 'write' }) } }); await flush()
  h.workspaceCodeText.value = 'changed'; assert.equal(await h.saveWorkspaceCode(false), false); assert.equal(h.workspaceDirty.value, true); assert.equal(h.workspace.saveFailed.value, true)
  fail = false; assert.equal(await h.saveWorkspaceCode(false), true); assert.equal(h.workspaceDirty.value, false); assert.equal(h.workspace.saveFailed.value, false); h.dispose()
})
test('delete confirmation fails recoverably, deduplicates physical writes and invalidates old identities', async () => {
  const pending = deferred(); let count = 0
  const h = monitoringHarness({ api: { deleteMonitoringTask: () => { count++; return pending.promise } } }); await flush(); h.onDelete(h.workspaceTask.value)
  const dialog = h.dialogs[0], job = dialog.options.onBeforeOk(); assert.equal(dialog.options.onBeforeCancel(), false)
  assert.equal(await dialog.options.onBeforeOk(), false); assert.equal(count, 1)
  h.user.token = 'other'; assert.equal(dialog.closed, true); pending.resolve({ code: 200, msg: 'stale delete' }); assert.equal(await job, false)
  assert.equal(h.deletingIds.size, 0); assert.equal(h.messages.some(([, msg]) => msg === 'stale delete'), false); h.dispose()
})
test('pending execution state refreshes on public five-second polling without workspace loading and stops when completed', async () => {
  let completed = false; const h = monitoringHarness({ api: { getMonitoringTaskDetail: id => ({ code: 200, data: taskRecord(id, { status: completed ? 4 : 0 }) }) } }); await flush()
  assert.ok([...h.timers.values()].some(timer => timer.delay === 5000)); const count = calls(h, 'getMonitoringTaskDetail').length
  completed = true; await h.tick(5000)
  assert.equal(calls(h, 'getMonitoringTaskDetail').length, count + 1); assert.equal(h.workspaceLoading.value, false); assert.equal(h.workspaceTask.value.status, 4)
  assert.equal([...h.timers.values()].some(timer => timer.delay === 5000), false); h.dispose()
})
test('state polling failure retries rather than losing current task, and pauses in background', async () => {
  let fail = false; const h = monitoringHarness({ api: { getMonitoringTaskDetail: id => { if (fail) throw Error('offline'); return { code: 200, data: taskRecord(id) } } } }); await flush()
  fail = true; await h.tick(5000); assert.equal(h.workspace.stateFailed.value, true); assert.equal(h.workspaceTaskId.value, 1)
  const count = calls(h, 'getMonitoringTaskDetail').length; await h.visibility('hidden'); await h.tick(5000); assert.equal(calls(h, 'getMonitoringTaskDetail').length, count)
  fail = false; await h.visibility('visible'); await h.tick(0); assert.equal(h.workspace.stateFailed.value, false); h.dispose()
})
test('local logs retain two-second protocol, silence polling loading and pause/resume with visibility', async () => {
  const h = monitoringHarness(); await flush(); h.logs.open(); assert.equal(h.logRefreshLoading.value, true); await flush()
  assert.deepEqual(calls(h, 'getMonitoringTaskLogs')[0].slice(1), [1, 500]); assert.equal(h.logText.value, 'Example\n')
  await h.tick(2000); assert.equal(h.logRefreshLoading.value, false); const count = calls(h, 'getMonitoringTaskLogs').length
  await h.visibility('hidden'); await h.tick(2000); assert.equal(calls(h, 'getMonitoringTaskLogs').length, count)
  await h.visibility('visible'); assert.equal(calls(h, 'getMonitoringTaskLogs').length, count + 1); h.logs.close(); assert.equal([...h.timers.values()].some(timer => timer.interval), false); h.dispose()
})
test('late logs after close/reopen cannot replace new log window or end its loading', async () => {
  const old = deferred(), latest = deferred(); let count = 0
  const h = monitoringHarness({ api: { getMonitoringTaskLogs: () => ++count === 1 ? old.promise : latest.promise } }); await flush()
  h.logs.open(); h.logs.close(); h.logs.open(); old.resolve({ code: 200, data: ['old'] }); await flush(); assert.equal(h.logRefreshLoading.value, true); assert.equal(h.logText.value, '')
  latest.resolve({ code: 200, data: ['new'] }); await flush(); assert.equal(h.logText.value, 'new'); h.dispose()
})
test('failed log reads retry locally and reopened identical logs still scroll when auto-scroll is enabled', async () => {
  let fail = true, scrolled = 0; const h = monitoringHarness({ api: { getMonitoringTaskLogs: () => { if (fail) throw Error('offline'); return { code: 200, data: ['same'] } } } }); await flush()
  h.logEditorRef.value = { scrollToBottom: () => scrolled++ }; h.logs.open(); await flush(); assert.equal(h.logFailed.value, true)
  fail = false; await h.tick(2000); assert.equal(h.logFailed.value, false); assert.equal(h.logText.value, 'same'); assert.ok(scrolled > 0)
  h.logs.close(); const previous = scrolled; h.logs.open(); await flush(); assert.ok(scrolled > previous); h.dispose()
})
test('download lock survives close, stale downloads create no file, and successful URLs are cleaned', async () => {
  const pending = deferred(); let count = 0
  const h = monitoringHarness({ api: { downloadMonitoringTaskLog: () => ++count === 1 ? pending.promise : { data: new Blob(['log'], { type: 'text/plain' }) } } }); await flush(); h.logs.open(); await flush()
  const job = h.logs.download(); h.logs.close(); h.logs.open(); await h.logs.download(); assert.equal(count, 1)
  pending.resolve({ data: new Blob(['old']) }); await job; assert.equal(h.downloads.length, 0)
  await h.logs.download(); assert.equal(h.downloads.length, 1); assert.equal(h.appended.length, 0); await h.tick(1000); assert.deepEqual(h.revoked, ['blob:fixture-1']); h.dispose()
})
test('JSON error downloads and anchor failures do not leak files or object URLs', async () => {
  for (const broken of ['json', 'anchor']) {
    const h = monitoringHarness({ click: broken === 'anchor' ? () => { throw Error('blocked') } : undefined,
      api: { downloadMonitoringTaskLog: () => ({ data: new Blob(['error'], { type: broken === 'json' ? 'application/json' : 'text/plain' }) }) } })
    await flush(); h.logs.open(); await flush(); await h.logs.download()
    assert.equal(h.downloads.length, 0); assert.equal(h.appended.length, 0); assert.equal(h.logDownloadLoading.value, false)
    if (broken === 'anchor') assert.deepEqual(h.revoked, ['blob:fixture-1']); h.dispose()
  }
})
test('Demo copy holds physical lock across identity close and suppresses stale success', async () => {
  const pending = deferred(), h = monitoringHarness({ component: 'MonitoringTaskDemo', copy: () => pending.promise })
  h.open(); const job = h.copyMonitoringDemo(); await h.copyMonitoringDemo(); assert.equal(h.clipboard.length, 1)
  h.user.token = 'other'; assert.equal(h.visible.value, false); assert.equal(h.copying.value, true)
  h.open(); await h.copyMonitoringDemo(); assert.equal(h.clipboard.length, 1); pending.resolve(); await job
  assert.equal(h.messages.length, 0); assert.equal(h.copying.value, false); h.dispose()
})
test('KeepAlive suspends UI and all timers; late reads cannot restore old workspace, resume reloads once', async () => {
  const h = monitoringHarness(); await flush(); h.logs.open(); await flush()
  h.hooks.deactivated.forEach(fn => fn()); assert.equal(h.workspaceTaskId.value, null); assert.equal(h.logPanelVisible.value, false); assert.equal(h.timers.size, 0)
  const count = calls(h, 'getMonitoringTask').length; h.hooks.activated.forEach(fn => fn()); await h.tick(0); await flush()
  assert.equal(calls(h, 'getMonitoringTask').length, count + 1); assert.equal(h.workspaceTaskId.value, 1); h.dispose()
})
test('unsaved code survives same-identity KeepAlive restoration but never crosses identity changes', async () => {
  const h = monitoringHarness(); await flush(); h.workspaceCodeText.value = 'unsaved draft'
  h.hooks.deactivated.forEach(fn => fn()); assert.equal(h.workspaceTaskId.value, null)
  h.hooks.activated.forEach(fn => fn()); await flush(); assert.equal(h.workspaceCodeText.value, 'unsaved draft'); assert.equal(h.workspaceDirty.value, true)
  h.user.token = 'other'; await flush(); assert.equal(h.workspaceCodeText.value, 'print(1)'); assert.equal(h.workspaceDirty.value, false); h.dispose()
})
test('pending autosave during cache suspension retains its draft and cannot falsely acknowledge a failed write', async () => {
  const pending = deferred(), h = monitoringHarness({ api: { putMonitoringTask: () => pending.promise } }); await flush()
  h.workspaceCodeText.value = 'unsaved'; const job = h.saveWorkspaceCode(false)
  h.hooks.deactivated.forEach(fn => fn()); h.hooks.activated.forEach(fn => fn()); await flush()
  assert.equal(h.workspaceCodeText.value, 'unsaved'); assert.equal(h.fileSaving.value, true)
  pending.reject(Error('offline')); assert.equal(await job, false); assert.equal(h.workspaceDirty.value, true); assert.equal(h.fileSaving.value, false); h.dispose()
})
test('snapshot mapping whitelists metadata, preserving nulls/zero and rejecting malformed task records', () => {
  const h = monitoringHarness(), { readMonitoringTask } = h.load('task-records.ts')
  const row = readMonitoringTask({ ...taskRecord(), secret: 'must-not-copy' }); assert.equal('secret' in row, false); assert.equal(row.test_env, 0); assert.equal(row.pid, null)
  assert.throws(() => readMonitoringTask({ ...taskRecord(), script_content: {} })); h.dispose()
})
test('all three routed/private SFC script and templates compile', () => {
  for (const relative of ['index.vue', 'components/MonitoringTaskEditor.vue', 'components/MonitoringTaskDemo.vue']) {
    const filename = path.resolve('src/views/monitoring/task', relative), source = readFileSync(filename, 'utf8'), { descriptor } = parse(source, { filename })
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  }
})
test('task API preserves endpoints, request bodies, list-detail normalization and blob protocol', async () => {
  const exports = {}, requests = []
  const request = async options => { requests.push({ url: options.url, data: options.data() }); return page([taskRecord(1)]) }
  const blobGet = async (url, options) => { requests.push({ url, ...options }); return { data: new Blob(['log']) } }
  new Function('exports', 'require', ts.transpileModule(readFileSync('src/api/monitoring/task.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText)(exports, id => id === '@/api/http'
    ? { get: request, post: request, put: request, deleted: request } : { default: { get: blobGet } })
  await exports.getMonitoringTask({ page: 2, pageSize: 20, project_product: 0 })
  assert.deepEqual(requests.at(-1), { url: 'monitoring/task', data: { page: 2, pageSize: 20, project_product: 0 } })
  assert.equal((await exports.getMonitoringTaskDetail(1)).data.id, 1); assert.equal((await exports.getMonitoringTaskDetail(99)).data, null)
  await exports.putMonitoringTask({ id: 1, script_content: 'code' }); assert.deepEqual(requests.at(-1).data, { id: 1, script_content: 'code' })
  await exports.postMonitoringTaskStart(1); assert.deepEqual(requests.at(-1), { url: 'monitoring/task/start', data: { id: 1 } })
  await exports.postMonitoringTaskStop(1); assert.deepEqual(requests.at(-1), { url: 'monitoring/task/stop', data: { id: 1 } })
  await exports.getMonitoringTaskLogs(1, 500); assert.deepEqual(requests.at(-1), { url: 'monitoring/task/logs', data: { id: 1, limit: 500 } })
  await exports.downloadMonitoringTaskLog(1); assert.deepEqual(requests.at(-1), { url: 'monitoring/task/download/log', params: { id: 1 }, responseType: 'blob' })
})
