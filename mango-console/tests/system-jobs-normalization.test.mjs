import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { fire, row, ok, setup } from './helpers/system-jobs-harness.mjs'

const base = path.resolve('src/views/timing/system-jobs')

test('Options API name retained and every instance owns filter arrays and option objects', t => {
  const a = setup(), b = setup(); t.after(b.close); t.after(a.close); assert.equal(a.component.name, 'TimingSystemJobs')
  const source = a.conditionItems.find(item => item.key === 'source_type'), status = a.conditionItems.find(item => item.key === 'latest_status')
  source.value.push(0); status.value.push(0, 'untriggered'); source.optionItems[0].label = 'Changed'
  assert.deepEqual(b.conditionItems.find(item => item.key === 'source_type').value, []); assert.notEqual(b.conditionItems.find(item => item.key === 'source_type').optionItems[0].label, 'Changed')
  for (const field of [source, status]) { assert.equal(field.multiple, true); assert.equal(field.searchOperator, 'in'); field.reset(); assert.deepEqual(field.value, []) }
})
test('finite job DTO preserves fire zero/long IDs and missing latest fire without sharing nested evidence', t => {
  const h = setup(); t.after(h.close); const m = h.module('job-records.ts'), original = row(), copied = m.copySystemJob(original)
  assert.equal(copied.latest_fire.id, 0); assert.equal(copied.latest_fire.status, 0); assert.equal(copied.source_type, 0); assert.equal(copied.next_fire_at, '')
  assert.equal('extra_data' in copied.latest_fire, false); copied.latest_fire.status_name = 'Changed'; assert.equal(original.latest_fire.status_name, '待分发')
  assert.equal(m.copySystemJob(row({ latest_fire: null })).latest_fire, null)
  assert.equal(m.copySystemJob(row({ latest_fire: fire({ id: '90071992547409931234', status: null }) })).latest_fire.id, '90071992547409931234')
})
test('error and malformed list responses remain failures, unknown future integer statuses are preserved', t => {
  const h = setup(); t.after(h.close); const m = h.module('job-records.ts')
  for (const value of [{ code: 403, data: [] }, ok({}), ok([row()], '1'), ok([row(), row()], 2), ok([row({ key: '' })]), ok([row({ latest_fire: fire({ id: Number.MAX_SAFE_INTEGER + 1 }) })]), ok([row({ source_type: false })]), ok([row({ latest_fire: fire({ status: '0' }) })])]) assert.throws(() => m.parseSystemJobs(value))
  assert.equal(m.parseSystemJobs(ok([row({ latest_fire: fire({ status: 99 }) })])).rows[0].latest_fire.status, 99)
  assert.deepEqual(m.parseSystemJobs(ok([], 0)), { rows: [], total: 0 })
})
test('trigger result validates recorded fire/status without equating HTTP success to task success', t => {
  const h = setup(); t.after(h.close); const m = h.module('job-records.ts')
  assert.deepEqual(m.parseSystemJobTrigger(ok({ fire_id: 0, status: 4 })), { fireId: 0, status: 4, message: '触发完成' })
  assert.equal(m.parseSystemJobTrigger(ok({ fire_id: '90071992547409931234', status: 5 })).status, 5)
  for (const value of [{ code: 400 }, ok({}), ok({ fire_id: false, status: 3 }), ok({ fire_id: 1, status: '3' })]) assert.throws(() => m.parseSystemJobTrigger(value))
})
test('actual filter mapping preserves untriggered/status zero/source collections and trims original text protocol', t => {
  const h = setup(); t.after(h.close)
  for (const [key, value] of Object.entries({ key: ' example ', source_type: [0, 4], latest_status: [0, 'untriggered'], latest_error_message: ' error ' })) h.conditionItems.find(item => item.key === key).value = value
  assert.deepEqual(h.buildQuery(), { key: 'example', source_type__in: '0,4', latest_status__in: '0,untriggered', latest_error_message: 'error' })
  const m = h.module('job-records.ts'); assert.deepEqual(m.systemJobQuery({ source_type__in: 0, name: ' ', unused: 'omit' }), { source_type__in: '0' })
  assert.throws(() => m.systemJobQuery({ cron: {} }))
})
test('list duplicate mount/manual reads coalesce and loading releases after success', async t => {
  const request = deferred(), h = setup({ read: () => request.promise }); t.after(h.close); h.mount()
  const task = h.doRefresh(); assert.equal(h.doRefresh(), task); await flush(); assert.equal(h.reads.length, 1); assert.equal(h.listLoading.value, true)
  request.resolve(ok([row()])); await task; assert.equal(h.rows.value.length, 1); assert.equal(h.listLoading.value, false)
})
test('failed or malformed reads retain last good same-context data and can retry', async t => {
  let n = 0; const h = setup({ read: async () => { n++; if (n === 2) throw Error('offline'); if (n === 3) return ok({}); return ok([row()]) } }); t.after(h.close)
  h.mount(); await flush(); await h.doRefresh(); assert.equal(h.rows.value.length, 1); assert.match(h.listError.value, /重试/); assert.equal(h.listLoading.value, false)
  await h.doRefresh(); assert.match(h.listError.value, /重试/); await h.doRefresh(); assert.equal(h.listError.value, '')
})
test('latest search wins over late old result and reset returns collections/text/page to defaults', async t => {
  const a = deferred(), b = deferred(); let n = 0; const h = setup({ read: () => ++n === 1 ? a.promise : n === 2 ? b.promise : Promise.resolve(ok([row()])) }); t.after(h.close)
  h.mount(); await flush(); h.pagination.page = 3; h.conditionItems.find(item => item.key === 'latest_status').value = ['untriggered']; const latest = h.onSearch(); await flush()
  assert.deepEqual(h.reads.at(-1), { latest_status__in: 'untriggered', page: 1, pageSize: 20 })
  b.resolve(ok([row({ key: 'new_job' })])); await latest; a.resolve(ok([row({ key: 'old_job' })])); await flush(); assert.equal(h.rows.value[0].key, 'new_job')
  await h.onResetSearch(); assert.deepEqual(h.reads.at(-1), { page: 1, pageSize: 20 }); assert.deepEqual(h.conditionItems.find(item => item.key === 'latest_status').value, [])
})
test('shrunk totals refetch final page while preserving actual zero total', async t => {
  const h = setup({ read: async () => ok([], 0) }); t.after(h.close); h.mount(); await flush(); h.pagination.page = 4; await h.doRefresh()
  assert.equal(h.pagination.page, 1); assert.equal(h.pagination.pageCount, 0); assert.equal(h.reads.at(-1).page, 1)
})
test('cancelled confirmation and inactive context callbacks do not trigger jobs', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush(); h.onTrigger(row()); const a = h.confirms.at(-1)
  a.options.onCancel(); assert.equal(await a.options.onBeforeOk(), false)
  h.onTrigger(row()); const b = h.confirms.at(-1); h.visibility('hidden'); assert.equal(b.closed, true); assert.equal(await b.options.onBeforeOk(), false); assert.deepEqual(h.writes, [])
})
test('trigger confirmation uses fixed key, physical duplicate lock and closes only after response', async t => {
  const request = deferred(), h = setup({ trigger: () => request.promise }); t.after(h.close); h.mount(); await flush()
  const input = row(); h.onTrigger(input); const confirmation = h.confirms.at(-1); input.key = 'changed_job'
  const task = confirmation.options.onBeforeOk(); assert.equal(await confirmation.options.onBeforeOk(), false); h.onTrigger(row()); assert.equal(h.confirms.length, 1)
  assert.deepEqual(h.triggeringKeys.value, ['example_job']); assert.equal(confirmation.closed, false); assert.deepEqual(h.writes, ['example_job'])
  request.resolve(ok({ fire_id: 0, status: 3 })); assert.equal(await task, true); assert.equal(confirmation.closed, true); assert.deepEqual(h.triggeringKeys.value, [])
})
test('trigger refusal retains confirmation, unlocks failed row and allows explicit retry', async t => {
  let n = 0; const h = setup({ trigger: async () => ++n === 1 ? { code: 403 } : ok({ fire_id: 1, status: 3 }) }); t.after(h.close); h.mount(); await flush(); h.onTrigger(row())
  const confirmation = h.confirms.at(-1); assert.equal(await confirmation.options.onBeforeOk(), false); assert.equal(confirmation.closed, false); assert.deepEqual(h.triggeringKeys.value, [])
  assert.equal(await confirmation.options.onBeforeOk(), true); assert.equal(confirmation.closed, true); assert.equal(n, 2)
})
test('different jobs retain independent in-flight locks and late first completion cannot close second confirmation', async t => {
  const a = deferred(), b = deferred(), h = setup({ trigger: key => key === 'example_job' ? a.promise : b.promise }); t.after(h.close); h.mount(); await flush()
  h.onTrigger(row()); const first = h.confirms.at(-1), taskA = first.options.onBeforeOk()
  h.onTrigger(row({ key: 'other_job', name: 'Other' })); const second = h.confirms.at(-1), taskB = second.options.onBeforeOk()
  assert.deepEqual(h.triggeringKeys.value, ['example_job', 'other_job']); a.resolve(ok({ fire_id: 1, status: 3 })); assert.equal(await taskA, false)
  assert.equal(second.closed, false); assert.deepEqual(h.triggeringKeys.value, ['other_job'])
  b.resolve(ok({ fire_id: 2, status: 3 })); assert.equal(await taskB, true); assert.deepEqual(h.triggeringKeys.value, [])
})
test('recorded failed task remains failed after trigger response, no optimistic success status is written', async t => {
  let n = 0; const h = setup({ read: async () => ok([row({ latest_fire: fire({ status: ++n === 1 ? 0 : 4, status_name: n === 1 ? '待分发' : '失败' }) })]), trigger: async () => ok({ fire_id: 0, status: 4 }) }); t.after(h.close)
  h.mount(); await flush(); h.onTrigger(h.rows.value[0]); assert.equal(await h.confirms.at(-1).options.onBeforeOk(), true)
  assert.equal(h.rows.value[0].latest_fire.status, 4); assert.equal(h.statusColor(4), 'red')
})
test('trigger success and subsequent refresh error stay separate without duplicate automatic reads', async t => {
  let n = 0; const h = setup({ read: async () => { if (++n > 1) throw Error('offline'); return ok([row()]) } }); t.after(h.close)
  h.mount(); await flush(); h.onTrigger(row()); const confirmation = h.confirms.at(-1); assert.equal(await confirmation.options.onBeforeOk(), true)
  assert.equal(confirmation.closed, true); assert.match(h.listError.value, /重试/); await flush(); assert.equal(n, 2); assert.equal(h.messages.some(([name]) => name === 'success'), true)
})
test('identity change clears data/filters/confirmation; late trigger remains physically locked but never notifies new user', async t => {
  const request = deferred(), h = setup({ trigger: () => request.promise }); t.after(h.close); h.mount(); await flush()
  h.onTrigger(row()); const confirmation = h.confirms.at(-1), task = confirmation.options.onBeforeOk(); h.user.userId = 2
  assert.equal(confirmation.closed, true); assert.deepEqual(h.rows.value, []); assert.deepEqual(h.triggeringKeys.value, ['example_job']); await flush()
  h.onTrigger(row()); assert.equal(h.confirms.length, 1); request.resolve(ok({ fire_id: 1, status: 3 })); assert.equal(await task, false)
  assert.equal(h.messages.some(([name]) => name === 'success'), false); assert.deepEqual(h.triggeringKeys.value, [])
})
test('all remaining context dimensions reload current data and late old list cannot overwrite it', async t => {
  const first = deferred(); let n = 0; const h = setup({ read: () => ++n === 1 ? first.promise : Promise.resolve(ok([row({ key: 'new_job' })])) }); t.after(h.close)
  h.mount(); await flush(); h.user.roleId++; await flush(); first.resolve(ok([row({ key: 'old_job' })])); await flush(); assert.equal(h.rows.value[0].key, 'new_job')
  for (const change of [() => { h.user.token = 'changed-session' }, () => h.user.selected_environment++, () => h.permission.permissionKeys.push('timing.system_jobs:change'), () => { h.route.fullPath += '?example=1' }]) {
    const before = h.reads.length; change(); await flush(); assert.ok(h.reads.length > before)
  }
})
test('background and KeepAlive invalidate reads/confirmations and return resumes without replaying trigger', async t => {
  const request = deferred(); let n = 0; const h = setup({ read: () => ++n === 1 ? request.promise : Promise.resolve(ok([row({ key: 'new_job' })])) }); t.after(h.close)
  h.mount(); await flush(); h.onTrigger(row()); const confirmation = h.confirms.at(-1); h.visibility('hidden')
  assert.equal(confirmation.closed, true); assert.equal(h.listLoading.value, false); request.resolve(ok([row({ key: 'old_job' })])); await flush(); assert.deepEqual(h.rows.value, [])
  h.visibility('visible'); await flush(); assert.equal(h.rows.value[0].key, 'new_job'); assert.deepEqual(h.writes, [])
  h.callbacks.deactivate.forEach(f => f()); const before = h.reads.length; await h.doRefresh(); assert.equal(h.reads.length, before)
  h.callbacks.activate.forEach(f => f()); await flush(); assert.equal(h.reads.length, before + 1)
})
test('route leave and unmount invalidate callbacks and do not issue reads or triggers after disposal', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush(); h.onTrigger(row()); const confirmation = h.confirms.at(-1)
  h.route.path = '/index/home'; h.route.fullPath = '/index/home'; const before = h.reads.length
  assert.equal(await confirmation.options.onBeforeOk(), false); await h.doRefresh(); assert.equal(h.reads.length, before)
  h.callbacks.unmount.forEach(f => f()); h.visibility('visible'); await flush(); assert.equal(h.reads.length, before); assert.deepEqual(h.writes, [])
})
test('status colors keep pending, success, failure and skipped/cancelled semantics', t => {
  const h = setup(); t.after(h.close)
  for (const [value, color] of [[0, 'orange'], [1, 'blue'], [2, 'blue'], [3, 'green'], [4, 'red'], [5, 'gray'], [6, 'gray'], [99, 'orange'], [null, 'orange']]) assert.equal(h.statusColor(value), color)
})
test('actual Options API script and template compile with all declared column configurations', () => {
  const filename = path.join(base, 'index.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
  assert.deepEqual(errors, []); assert.equal(descriptor.scriptSetup, null)
  assert.deepEqual(ts.transpileModule(descriptor.script.content, { reportDiagnostics: true, compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).diagnostics, [])
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { expressionPlugins: ['typescript'] } }).errors, [])
})
