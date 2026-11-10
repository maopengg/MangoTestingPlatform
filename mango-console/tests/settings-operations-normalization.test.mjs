import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/system/settings')
const group = () => ({ key: 'ai', title: 'Example', items: [] })
const ok = data => ({ code: 200, data, msg: 'Example result' })
function setup(api = {}) {
  const previousDocument = globalThis.document
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = doc
  const route = vue.reactive({ path: '/system/settings/index', fullPath: '/system/settings/index', query: {} })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'example', selected_environment: 0 })
  const permission = vue.reactive({ permissionKeys: [] }), messages = [], callbacks = { activate: [], deactivate: [], unmount: [] }
  const h = harness('index', 'handleAiTest,handleVisionTest,handleEmailTest,handleRuntimeCacheClear,handleMethodCacheRefresh,handleMethodCacheView,handleBackendServiceSwitchChange,doPostSystemSetDebugLog,closeCacheDrawer,saveVisibilityChanged,testResults,testRecipient,aiTestLoading,visionTestLoading,emailTestLoading,runtimeCacheClearLoading,methodCacheRefreshLoading,methodCacheViewLoading,backendServiceConfigLoading,debugLogSaving,settingsData,cacheDrawer,cacheDrawerLoading,cacheDrawerError,methodCacheItems,lastSavedValues', {
    base, api, modules: {
      vue: { ...vue, onMounted() {}, onActivated: f => callbacks.activate.push(f), onDeactivated: f => callbacks.deactivate.push(f), onBeforeUnmount: f => callbacks.unmount.push(f) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/hooks/useMenuIcon': { useMenuIcon: () => ({ resolveMenuIcon: () => '' }) },
      '@/store/modules/platform-branding': { default: () => ({ apply() {} }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['warning', 'error', 'success'].map(kind => [kind, value => messages.push([kind, value])])), Modal: {} },
    },
  })
  return { ...h, route, user, permission, messages, callbacks,
    visibility(value) { doc.visibilityState = value; h.saveVisibilityChanged() },
    close() { callbacks.unmount.forEach(f => f()); h.close(); globalThis.document = previousDocument },
  }
}

test('operation responses require successful envelopes and real boolean statuses', t => {
  const h = setup(); t.after(h.close); const m = h.load('settings-response.ts')
  assert.deepEqual(m.settingsTestResult(ok({ status: false, message: 'failed', secret: 'omit' })), { status: false, message: 'failed' })
  assert.deepEqual(m.settingsTestResult(ok({ test_data: { status: true } }), 'test_data'), { status: true, message: 'Example result' })
  for (const value of [null, [], { code: 403, data: { status: true } }, ok({}), ok({ status: 'false' }), ok({ status: 1 }), ok({ status: true, message: {} })]) assert.throws(() => m.settingsTestResult(value))
  assert.throws(() => m.settingsTestResult(ok({}), 'test_data'))
  assert.equal(m.settingsDebugStatus(ok({ is_debug: false })), false)
  assert.throws(() => m.settingsDebugStatus(ok({ is_debug: 'false' })))
  const value = { rows: [0, false, null, 'example'], detail: {} }, copy = m.copySettingsCache(value)
  assert.deepEqual(copy, value); copy.rows[0] = 1; assert.equal(value.rows[0], 0)
  for (const value of [undefined, NaN, Infinity, { value: undefined }]) assert.throws(() => m.copySettingsCache(value))
})

test('text and vision tests have independent loading, prevent duplicates and retain false results', async t => {
  const pending = deferred(), calls = [], h = setup({ postSystemAiTest: capability => { calls.push(capability); return pending.promise } }); t.after(h.close)
  const a = h.handleAiTest(group()), b = h.handleVisionTest(group()); await flush()
  assert.equal(h.aiTestLoading.value, true); assert.equal(h.visionTestLoading.value, true)
  await h.handleAiTest(group()); await h.handleVisionTest(group()); assert.deepEqual(calls, ['text', 'vision'])
  pending.resolve(ok({ status: false, message: 'Example failure' })); await Promise.all([a, b])
  assert.equal(h.testResults.ai.status, false); assert.equal(h.testResults.ai_vision.status, false)
  assert.equal(h.messages.some(([kind]) => kind === 'success'), false)
  assert.equal(h.aiTestLoading.value, false); assert.equal(h.visionTestLoading.value, false)
})

test('malformed and network test failures recover and can be retried', async t => {
  let count = 0
  const h = setup({ postSystemAiTest: async () => {
    count++; if (count === 1) return ok({ status: 'false' }); if (count === 2) throw Error('offline'); return ok({ status: true, message: 'Recovered' })
  } }); t.after(h.close)
  await h.handleAiTest(group()); assert.equal(h.testResults.ai.status, false)
  await h.handleAiTest(group()); assert.equal(h.testResults.ai.status, false)
  await h.handleAiTest(group()); assert.equal(h.testResults.ai.status, true); assert.equal(h.aiTestLoading.value, false)
})

test('context changes while saving prevent a test request under the new identity', async t => {
  const pending = deferred(), calls = [], h = setup({ putSystemCacheData: () => pending.promise, postSystemAiTest: async () => { calls.push('test'); return ok({ status: true }) } }); t.after(h.close)
  const item = { id: 1, key: 'EXAMPLE', describe: 'Example', value: 'new', value_type: 4, management_level: 3, has_value: true, is_secret: false }
  const testing = h.handleAiTest({ ...group(), items: [item] }); await flush()
  h.user.roleId++; pending.resolve(ok(null)); await testing
  assert.deepEqual(calls, []); assert.equal(h.testResults.ai, undefined); assert.equal(h.aiTestLoading.value, false)
})

test('email snapshots recipient, validates first, deduplicates and handles false/malformed responses', async t => {
  const pending = deferred(), recipients = [], h = setup({ postSystemEmailTest: recipient => { recipients.push(recipient); return pending.promise } }); t.after(h.close)
  h.testRecipient.value = 'bad'; await h.handleEmailTest(group()); assert.equal(recipients.length, 0)
  h.testRecipient.value = '  user@example.com  '; const a = h.handleEmailTest(group()); await flush()
  h.testRecipient.value = 'other@example.org'; await h.handleEmailTest(group()); assert.deepEqual(recipients, ['user@example.com'])
  pending.resolve(ok({ status: false, message: 'Example mail failure' })); await a
  assert.equal(h.testResults.email.status, false); assert.equal(h.emailTestLoading.value, false)
})

test('late test results after background, KeepAlive or identity changes stay silent', async t => {
  for (const pause of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(f => f()), h => h.user.selected_environment = 1,
    h => h.permission.permissionKeys = ['example:read'], h => h.route.fullPath += '?group=api', h => h.callbacks.unmount.forEach(f => f())]) {
    const pending = deferred(), h = setup({ postSystemAiTest: () => pending.promise })
    try {
      const testing = h.handleAiTest(group()); await flush(); pause(h)
      pending.resolve(ok({ status: true, message: 'Late result' })); await testing
      assert.equal(h.testResults.ai, undefined); assert.equal(h.messages.length, 0); assert.equal(h.aiTestLoading.value, false)
    } finally { h.close() }
  }
})

test('runtime cache clearing deduplicates, reports failures and retries', async t => {
  const pending = deferred(); let calls = 0
  const h = setup({ postSystemRuntimeCacheClear: () => ++calls === 1 ? pending.promise : Promise.resolve(ok(null)) }); t.after(h.close)
  const first = h.handleRuntimeCacheClear(); await h.handleRuntimeCacheClear(); assert.equal(calls, 1)
  pending.reject(Error('offline')); await first; assert.equal(h.runtimeCacheClearLoading.value, false)
  assert.equal(h.messages.at(-1)[0], 'error'); await h.handleRuntimeCacheClear(); assert.equal(h.messages.at(-1)[0], 'success')
})

test('method refresh checks its own result and never treats missing/malformed status as success', async t => {
  const values = [ok({}), ok({ test_data: { status: 'false' } }), ok({ test_data: { status: false, message: 'Example warning' } }), ok({ test_data: { status: true } })]
  const h = setup({ postSystemMethodCacheRefresh: async () => values.shift() }); t.after(h.close)
  for (let i = 0; i < 4; i++) { await h.handleMethodCacheRefresh(h.methodCacheItems[0]); assert.equal(h.methodCacheRefreshLoading.test_data, false) }
  assert.deepEqual(h.messages.map(([kind]) => kind), ['error', 'error', 'warning', 'success'])
})

test('cache viewer opens with regional loading; closing prevents a late response from reopening', async t => {
  const pending = deferred(), h = setup({ getSystemCacheDataKeyValue: () => pending.promise }); t.after(h.close)
  const viewing = h.handleMethodCacheView(h.methodCacheItems[0])
  assert.equal(h.cacheDrawer.visible, true); assert.equal(h.cacheDrawerLoading.value, true); assert.equal(h.cacheDrawer.data, null)
  h.closeCacheDrawer(); pending.resolve(ok({ example: 'late' })); await viewing
  assert.equal(h.cacheDrawer.visible, false); assert.equal(h.cacheDrawer.data, null); assert.equal(h.cacheDrawerLoading.value, false)
})

test('cache switching keeps the most recent target and does not share response objects', async t => {
  const a = deferred(), b = deferred(), h = setup({ getSystemCacheDataKeyValue: key => key === 'test_data_select_value' ? a.promise : b.promise }); t.after(h.close)
  const first = h.handleMethodCacheView(h.methodCacheItems[0]), second = h.handleMethodCacheView(h.methodCacheItems[1])
  const data = { value: 0 }; b.resolve(ok(data)); await second
  a.resolve(ok({ value: 'old' })); await first
  assert.match(h.cacheDrawer.title, /ass_select_value/); assert.deepEqual(h.cacheDrawer.data, { value: 0 })
  data.value = 1; assert.equal(h.cacheDrawer.data.value, 0); assert.equal(h.cacheDrawerLoading.value, false)
})

test('cache viewer failure stays in its drawer with retry and cannot publish after pause', async t => {
  let calls = 0; const pending = deferred(), h = setup({ getSystemCacheDataKeyValue: () => ++calls === 1 ? Promise.reject(Error('offline')) : pending.promise }); t.after(h.close)
  await h.handleMethodCacheView(h.methodCacheItems[0]); assert.match(h.cacheDrawerError.value, /重试/)
  assert.equal(h.cacheDrawerLoading.value, false)
  const retry = h.handleMethodCacheView(h.methodCacheItems[0]); h.visibility('hidden')
  pending.resolve(ok(false)); await retry
  assert.equal(h.cacheDrawer.visible, false); assert.equal(h.cacheDrawer.data, null); assert.equal(h.cacheDrawerError.value, '')
})

test('debug switch updates only after validated success, rejects duplicate and permits retry', async t => {
  const pending = deferred(), values = [], h = setup({ postSystemSetDebugLog: value => { values.push(value); return pending.promise } }); t.after(h.close)
  const saving = h.doPostSystemSetDebugLog(true); await h.doPostSystemSetDebugLog(false)
  assert.equal(h.settingsData.isDebug, false); assert.deepEqual(values, [true])
  pending.resolve(ok({ is_debug: true })); await saving
  assert.equal(h.settingsData.isDebug, true); assert.equal(h.debugLogSaving.value, false)
})

test('guest switch snapshots its write and preserves the original value on failure', async t => {
  const pending = deferred(), writes = [], h = setup({ putSystemCacheData: payload => { writes.push(payload); return pending.promise } }); t.after(h.close)
  const item = { id: 1, key: 'GUEST_CAN_VIEW_ALL_PROJECT_DATA', value: false, has_value: true }
  const saving = h.handleBackendServiceSwitchChange(item, true); await h.handleBackendServiceSwitchChange(item, false)
  assert.deepEqual(writes, [[{ id: 1, key: 'GUEST_CAN_VIEW_ALL_PROJECT_DATA', value: true }]])
  assert.equal(item.value, false); pending.resolve({ code: 403 }); await saving
  assert.equal(item.value, false); assert.equal(h.backendServiceConfigLoading[item.key], false)
})

test('late switch and cache operation receipts cannot publish into another identity', async t => {
  const pending = deferred(), h = setup({ postSystemSetDebugLog: () => pending.promise, putSystemCacheData: () => pending.promise,
    postSystemRuntimeCacheClear: () => pending.promise, postSystemMethodCacheRefresh: () => pending.promise }); t.after(h.close)
  const item = { id: 1, key: 'GUEST_CAN_VIEW_ALL_PROJECT_DATA', value: false, has_value: true }
  const requests = [h.doPostSystemSetDebugLog(true), h.handleBackendServiceSwitchChange(item, true), h.handleRuntimeCacheClear(), h.handleMethodCacheRefresh(h.methodCacheItems[0])]
  h.user.userId++; pending.resolve(ok({ is_debug: true, test_data: { status: true } })); await Promise.all(requests)
  assert.equal(item.value, false); assert.equal(h.settingsData.isDebug, false); assert.equal(h.messages.length, 0)
})

test('malformed debug response leaves the old switch state and a retry can succeed', async t => {
  let count = 0
  const h = setup({ postSystemSetDebugLog: async () => ok({ is_debug: ++count === 1 ? 'true' : true }) }); t.after(h.close)
  await h.doPostSystemSetDebugLog(true); assert.equal(h.settingsData.isDebug, false); assert.equal(h.messages.at(-1)[0], 'error')
  await h.doPostSystemSetDebugLog(true); assert.equal(h.settingsData.isDebug, true); assert.equal(h.messages.at(-1)[0], 'success')
})

test('guest switch updates its saved baseline only after a successful response', async t => {
  const h = setup({ putSystemCacheData: async () => ok(null) }); t.after(h.close)
  const item = { id: '90071992547409931234', key: 'GUEST_CAN_VIEW_ALL_PROJECT_DATA', value: false, has_value: true }
  await h.handleBackendServiceSwitchChange(item, true)
  assert.equal(item.value, true); assert.equal(h.lastSavedValues.get(item.key), 'true')
  assert.equal(h.backendServiceConfigLoading[item.key], false)
})

test('method refresh has per-kind physical locks, including across pause and activation', async t => {
  const pending = deferred(), calls = [], h = setup({ postSystemMethodCacheRefresh: type => { calls.push(type); return pending.promise } }); t.after(h.close)
  const first = h.handleMethodCacheRefresh(h.methodCacheItems[0]), second = h.handleMethodCacheRefresh(h.methodCacheItems[1])
  h.visibility('hidden'); h.visibility('visible'); await h.handleMethodCacheRefresh(h.methodCacheItems[0])
  assert.deepEqual(calls, ['test_data', 'api_assertion'])
  pending.resolve(ok({ test_data: { status: true }, api_assertion: { status: true } })); await Promise.all([first, second])
  assert.equal(h.messages.length, 0); assert.equal(h.methodCacheRefreshLoading.test_data, false); assert.equal(h.methodCacheRefreshLoading.api_assertion, false)
})
