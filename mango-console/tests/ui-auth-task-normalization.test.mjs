import assert from 'node:assert/strict'
import test from 'node:test'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { setupUiAuthTasks, taskResponse } from './helpers/ui-auth-task-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'

const target = (values = {}) => ({ id: 0, auth_type: 1, ...values })
test('task boundaries preserve long IDs and verify response code, exact business, type, ID and terminal state', t => {
  const h = setupUiAuthTasks(); t.after(h.close); const dto = h.records, long = '90071992547409930000'
  assert.equal(dto.readAuthSubmission({ code: 200, data: { task_id: long } }), long)
  for (const taskId of [0, '000', '', null, {}, false, Number.MAX_SAFE_INTEGER + 1]) assert.throws(() => dto.readAuthSubmission({ code: 200, data: { task_id: taskId } }))
  assert.equal(dto.readAuthTask(taskResponse(long), long, 0, 'start').taskId, long)
  for (const patch of [{ task_id: 92 }, { business_id: 2 }, { business_type: 'other' }, { task_type: 'auth_capture' }, { terminal: true }, { status: 'unknown' }]) assert.throws(() => dto.readAuthTask(taskResponse(91, 0, 'start', 'running', patch), 91, 0, 'start'))
  assert.throws(() => dto.readAuthTask({ code: 403 }, 91, 0, 'start'))
})
test('submission captures zero ID, prevents duplicate POST and retains loading through task observation', async t => {
  const pending = deferred(), h = setupUiAuthTasks({ start: () => pending.promise }); t.after(h.close); const row = target()
  const starting = h.start(row, 'start'); row.id = 2; assert.equal(h.isSubmitting(0), true); assert.equal(await h.start(target(), 'start'), false); assert.deepEqual(h.writes, [['start', 0]])
  pending.resolve({ code: 200, data: { task_id: 91 } }); assert.equal(await starting, true); await flush(); assert.equal(h.isSubmitting(0), false); assert.equal(h.isLoading(0, 'start'), true)
  assert.equal(h.observation().taskId, '91'); assert.deepEqual(h.reads, [[91, true]])
})
test('unsupported authorization, hidden page and manual write busy conditions do not submit tasks', async t => {
  const h = setupUiAuthTasks(); t.after(h.close)
  for (const auth_type of [0, 2, 3, 4]) assert.equal(await h.start(target({ auth_type }), 'start'), false)
  h.setBusy(true); assert.equal(await h.start(target(), 'start'), false); h.setBusy(false); h.pausePage(); assert.equal(await h.start(target(), 'capture'), false); assert.deepEqual(h.writes, [])
})
test('POST failure releases physical lock for retry, while accepted malformed task response is reported as uncertain', async t => {
  let fail = true; const h = setupUiAuthTasks({ start: async () => fail ? { code: 403 } : { code: 200, data: {} } }); t.after(h.close)
  assert.equal(await h.start(target(), 'start'), false); assert.match(h.error.value, /提交失败/); assert.equal(h.isSubmitting(0), false)
  fail = false; assert.equal(await h.start(target(), 'start'), false); assert.match(h.error.value, /已提交.*任务信息异常/); assert.equal(h.reads.length, 0)
})
test('pending and running task reads use one-second local timers and only success clears observation and notifies', async t => {
  let status = 'pending'; const h = setupUiAuthTasks({ getExecutorTask: async taskId => taskResponse(taskId, 0, 'start', status) }); t.after(h.close)
  await h.start(target(), 'start'); await flush(); assert.equal(h.messages.length, 0); assert.equal(h.timers.size, 1)
  await h.tick(999); assert.equal(h.reads.length, 1); status = 'running'; await h.tick(1); assert.equal(h.reads.length, 2)
  status = 'success'; await h.tick(1000); assert.equal(h.messages.length, 1); assert.match(h.messages[0], /浏览器已打开/); assert.equal(h.observation(), null); assert.equal(h.isLoading(0, 'start'), false); assert.equal(h.timers.size, 0)
})
test('capture success refreshes only through its callback and keeps task/local loading separate from list state', async t => {
  const h = setupUiAuthTasks({ getExecutorTask: async taskId => taskResponse(taskId, 0, 'capture', 'success') }); t.after(h.close)
  await h.start(target(), 'capture'); await flush(); assert.deepEqual(h.writes, [['capture', 0]]); assert.equal(h.captured.length, 1); assert.match(h.messages[0], /提取并保存/); assert.equal(h.observation(0, 'capture'), null)
})
test('a late capture callback failure cannot restore old errors after identity invalidation', async t => {
  const pending = deferred(), h = setupUiAuthTasks({ getExecutorTask: async taskId => taskResponse(taskId, 0, 'capture', 'success'), onCaptured: () => pending.promise }); t.after(h.close)
  await h.start(target(), 'capture'); await flush(); h.invalidate(); pending.reject(Error('network')); await flush(); assert.equal(h.error.value, ''); assert.equal(h.timers.size, 0)
})
test('read failures keep retrying silently, retain the task and never repeat the submission', async t => {
  let fail = true; const h = setupUiAuthTasks({ getExecutorTask: async taskId => { if (fail) throw Error('network'); return taskResponse(taskId, 0, 'start', 'success') } }); t.after(h.close)
  await h.start(target(), 'start'); await flush(); assert.match(h.error.value, /正在重试/); assert.equal(h.isLoading(0, 'start'), true); assert.equal(h.observation().taskId, '91')
  await h.tick(1000); assert.equal(h.reads.length, 2); fail = false; await h.tick(1000); assert.equal(h.error.value, ''); assert.equal(h.messages.length, 1); assert.equal(h.writes.length, 1)
})
test('terminal failure clears the matching record and does not expose raw task error content', async t => {
  const h = setupUiAuthTasks({ getExecutorTask: async taskId => taskResponse(taskId, 0, 'start', 'failed', { error_message: 'example-private-error' }) }); t.after(h.close)
  await h.start(target(), 'start'); await flush(); assert.equal(h.messages.length, 0); assert.match(h.error.value, /请查看任务通知/); assert.deepEqual(h.errors, [h.error.value]); assert.equal(h.error.value.includes('example-private-error'), false); assert.equal(h.observation(), null); assert.equal(h.timers.size, 0)
})
test('two/fifteen-minute observation limits retain task recovery and clicking again resumes GET without a new POST', async () => {
  for (const [action, minutes] of [['start', 2], ['capture', 15]]) {
    let complete = false; const h = setupUiAuthTasks({ getExecutorTask: async taskId => taskResponse(taskId, 0, action, complete ? 'success' : 'running') })
    try {
      await h.start(target(), action); await flush(); await h.tick(minutes * 60 * 1000); assert.match(h.error.value, /超时/); assert.equal(h.isLoading(0, action), false); assert.notEqual(h.observation(0, action), null)
      complete = true; await h.start(target(), action); await flush(); assert.equal(h.writes.length, 1); assert.equal(h.messages.length, 1)
    } finally { h.close() }
  }
})
test('page suspension removes timers and resumes existing observations without duplicate POST or GET loops', async t => {
  const h = setupUiAuthTasks(); t.after(h.close); await h.start(target(), 'start'); await flush(); h.pausePage(); assert.equal(h.timers.size, 0); assert.equal(h.isLoading(0, 'start'), false)
  await h.tick(10_000); assert.equal(h.reads.length, 1); h.resumePage([target()]); h.resume([target()]); await flush(); assert.equal(h.reads.length, 2); assert.equal(h.writes.length, 1); assert.equal(h.timers.size, 1)
})
test('suspending an in-flight read suppresses stale terminal feedback and waits for settlement before the next GET', async t => {
  const pending = deferred(); let calls = 0; const h = setupUiAuthTasks({ getExecutorTask: taskId => ++calls === 1 ? pending.promise : Promise.resolve(taskResponse(taskId)) }); t.after(h.close)
  await h.start(target(), 'start'); h.pausePage(); h.resumePage([target()]); assert.equal(h.reads.length, 1)
  pending.resolve(taskResponse(91, 0, 'start', 'success')); await flush(); assert.equal(h.messages.length, 0); assert.notEqual(h.observation(), null)
  await h.tick(0); assert.equal(h.reads.length, 2); assert.equal(h.timers.size, 1)
})
test('token/permission epoch invalidation stops stale task reads and resumes with a fresh context', async t => {
  const pending = deferred(), h = setupUiAuthTasks({ getExecutorTask: () => pending.promise }); t.after(h.close)
  await h.start(target(), 'start'); h.invalidate(); pending.resolve(taskResponse(91, 0, 'start', 'success')); await flush(); assert.equal(h.messages.length, 0); assert.notEqual(h.observation(), null); assert.equal(h.timers.size, 0)
  h.resume([target()]); await flush(); assert.equal(h.messages.length, 1)
})
test('late POST is persisted under its original owner, remains physically guarded and never queries as another owner', async t => {
  const pending = deferred(), h = setupUiAuthTasks({ start: () => pending.promise }); t.after(h.close); const originalOwner = h.getOwner()
  const posting = h.start(target(), 'start'); h.pausePage(); h.resumePage([target()]); assert.equal(await h.start(target(), 'start'), false)
  h.setOwner('[2,2,0]'); pending.resolve({ code: 200, data: { task_id: 91 } }); await posting; await flush(); assert.equal(h.reads.length, 0); assert.equal(h.observation(), null)
  h.setOwner(originalOwner); h.resume([target()]); await flush(); assert.equal(h.reads.length, 1); assert.equal(h.writes.length, 1)
})
test('a remounted observer restores scoped session records and respects the stored long task ID', async t => {
  const long = '90071992547409930000', h = setupUiAuthTasks({ getExecutorTask: async taskId => taskResponse(taskId, 0, 'capture') }); t.after(h.close)
  h.store(0, 'capture', long); const remounted = h.createObserver(); remounted.resume([target()]); await flush()
  assert.equal(h.reads[0][0], long); assert.equal(remounted.isLoading(0, 'capture'), true); assert.equal(h.writes.length, 0); remounted.pause()
})
test('legacy observations migrate only after backend ownership and exact task/business verification', async t => {
  const pending = deferred(), h = setupUiAuthTasks({ getExecutorTask: () => pending.promise }); t.after(h.close); h.store(0, 'start', 91, true)
  h.resume([target()]); assert.equal(h.observation(), null); assert.notEqual(h.observation(0, 'start', true), null)
  pending.resolve(taskResponse()); await flush(); assert.notEqual(h.observation(), null); assert.equal(h.observation(0, 'start', true), null); assert.equal(h.writes.length, 0)
})
test('denied or mismatched legacy task cannot migrate, clear another record or announce success', async () => {
  for (const result of [{ code: 403 }, taskResponse(91, 2), taskResponse(91, 0, 'capture')]) {
    const h = setupUiAuthTasks({ getExecutorTask: async () => result })
    try { h.store(0, 'start', 91, true); h.resume([target()]); await flush(); assert.equal(h.observation(), null); assert.notEqual(h.observation(0, 'start', true), null); assert.deepEqual(h.messages, []); assert.match(h.error.value, /重试/) } finally { h.close() }
  }
})
test('owned observations are separated by user, role and environment and never persist session token data', async t => {
  const h = setupUiAuthTasks(); t.after(h.close); h.store()
  for (const owner of ['[2,2,0]', '[1,3,0]', '[1,2,1]']) { h.setOwner(owner); h.resume([target()]); await flush(); assert.equal(h.reads.length, 0); assert.equal(h.observation(), null) }
  assert.equal([...h.storage.keys()].some(key => key.includes('token')), false); assert.equal([...h.storage.values()].some(value => value.includes('example-session')), false)
})
test('corrupted observations block accidental resubmission and report a recoverable local error', async t => {
  const h = setupUiAuthTasks(); t.after(h.close); h.store(); const key = [...h.storage.keys()][0], stored = JSON.parse(h.storage.get(key)); stored.owner = 'other'; h.storage.set(key, JSON.stringify(stored))
  assert.equal(await h.start(target(), 'start'), false); assert.equal(h.writes.length, 0); assert.match(h.error.value, /记录异常/)
})
test('storage write failure does not lose a live in-memory task or release its duplicate submission guard', async t => {
  const h = setupUiAuthTasks(); t.after(h.close); h.sessionStorage.setItem = () => { throw Error('quota') }
  await h.start(target(), 'start'); await flush(); assert.equal(h.isLoading(0, 'start'), true); assert.equal(await h.start(target(), 'start'), false); assert.equal(h.writes.length, 1); assert.equal(h.reads.length, 1)
})
test('unavailable session storage does not block starting or observing the in-memory task', async t => {
  const h = setupUiAuthTasks(); t.after(h.close)
  h.sessionStorage.getItem = () => { throw Error('storage unavailable') }; h.sessionStorage.setItem = () => { throw Error('storage unavailable') }
  assert.equal(await h.start(target(), 'start'), true); await flush(); assert.equal(h.reads.length, 1); assert.equal(h.isLoading(0, 'start'), true); assert.equal(await h.start(target(), 'start'), false)
})
test('an old terminal result never clears a newer persisted observation', async t => {
  const pending = deferred(), h = setupUiAuthTasks({ getExecutorTask: () => pending.promise }); t.after(h.close)
  await h.start(target(), 'start'); h.store(0, 'start', 92); pending.resolve(taskResponse(91, 0, 'start', 'success')); await flush(); assert.equal(h.observation().taskId, '92')
})
test('shared task API keeps default error behavior and supports silent local observation without changing its protocol', () => {
  const calls = [], api = loadModule('src/api/system/executor-task.ts', { '@/api/http': { get: value => calls.push(value), post() {} } })
  api.getExecutorTask(91); api.getExecutorTask('90071992547409930000', true)
  assert.equal(calls[0].silentError, false); assert.equal(calls[1].silentError, true); assert.equal(calls[1].url, '/system/executor/task'); assert.deepEqual(calls[1].data(), { task_id: '90071992547409930000' })
})
