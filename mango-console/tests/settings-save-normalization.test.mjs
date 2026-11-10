import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/system/settings')
const item = (values = {}) => ({ id: 1, key: 'EXAMPLE', describe: '配置', value: 'initial', value_type: 4,
  is_secret: false, management_level: 3, has_value: true, ...values })
function setup(overrides = {}) {
  const requests = [], dialogs = [], messages = []
  const previousDocument = globalThis.document
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = doc
  const route = vue.reactive({ path: '/system/settings/index', fullPath: '/system/settings/index', query: {} })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'example', selected_environment: 0 })
  const permission = vue.reactive({ permissionKeys: [] })
  const callbacks = { activate: [], deactivate: [], unmount: [] }
  const h = harness('index', 'saveItem,saveBeforeTest,rememberSavedValues,lastSavedValues,itemSaveLoading,pendingSaves,saveVisibilityChanged,normalizeEditValue,normalizePayloadValue,itemValueError,handleSwitchChange', {
    base,
    api: { putSystemCacheData: async payload => { requests.push(payload); return { code: 200 } }, ...overrides.api },
    modules: {
      vue: { ...vue, onMounted() {}, onActivated: f => callbacks.activate.push(f), onDeactivated: f => callbacks.deactivate.push(f), onBeforeUnmount: f => callbacks.unmount.push(f) },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/permission': { default: () => permission },
      '@/store/modules/get-enum': { useEnum: () => ({ getEnum: overrides.getEnum || (async () => {}) }) },
      '@/hooks/useMenuIcon': { useMenuIcon: () => ({ resolveMenuIcon: () => '' }) },
      '@/store/modules/platform-branding': { default: () => ({ apply() {} }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['warning', 'error', 'success'].map(key => [key, value => messages.push([key, value])])),
        Modal: { warning: options => { dialogs.push(options); return { close: () => options.onClose() } } } },
    },
  })
  const record = item(overrides.item), group = { key: 'example', title: '配置', items: [record] }
  h.rememberSavedValues([group])
  return { ...h, record, group, requests, dialogs, messages, route, user, permission, callbacks,
    close() { callbacks.unmount.forEach(f => f()); h.close(); globalThis.document = previousDocument },
    visibility(value) { doc.visibilityState = value; h.saveVisibilityChanged() },
  }
}

test('integer-backed callback switch accepts boolean editing and persists numeric zero or one', async t => {
  const h = setup({ item: { key: 'MOCK_CALLBACK_ENABLED', value: 0, value_type: 1 } }); t.after(h.close)
  assert.equal(h.normalizeEditValue(h.record), false)
  await h.handleSwitchChange(h.group, h.record, true)
  assert.equal(h.itemValueError(h.record), '')
  assert.equal(h.record.value, true)
  assert.deepEqual(h.requests[0], [{ id: 1, key: 'MOCK_CALLBACK_ENABLED', value: 1 }])
  await h.handleSwitchChange(h.group, h.record, false)
  assert.equal(h.itemValueError(h.record), '')
  assert.deepEqual(h.requests[1], [{ id: 1, key: 'MOCK_CALLBACK_ENABLED', value: 0 }])
  assert.equal(h.messages.some(([kind]) => kind === 'warning'), false)
})

test('failed integer switch save restores the last confirmed value', async t => {
  const h = setup({ item: { key: 'MOCK_CALLBACK_ENABLED', value: 0, value_type: 1 },
    api: { putSystemCacheData: async () => ({ code: 500 }) } }); t.after(h.close)
  await h.handleSwitchChange(h.group, h.record, true)
  assert.equal(h.normalizePayloadValue(h.record), 0)
  assert.equal(h.itemValueError(h.record), '')
  assert.equal(h.messages.some(([kind]) => kind === 'success'), false)
})

test('ordinary numeric settings still reject booleans, malformed values and fractional integers', async t => {
  const h = setup({ item: { key: 'API_TIMEOUT', value: 180, value_type: 1 } }); t.after(h.close)
  for (const value of [true, 'invalid', 1.5, Infinity]) {
    h.record.value = value
    assert.match(h.itemValueError(h.record), /数值配置格式异常/)
    assert.equal(await h.saveItem(h.group, h.record), false)
  }
  assert.equal(h.requests.length, 0)
})

test('cautious confirmation submits exactly the captured value, not a later edit', async t => {
  const h = setup({ item: { management_level: 2 } }); t.after(h.close)
  h.record.value = 'approved'; const saving = h.saveItem(h.group, h.record); await flush()
  assert.equal(h.itemSaveLoading.EXAMPLE, true); assert.equal(h.dialogs.length, 1)
  h.record.value = 'later edit'; h.dialogs[0].onOk(); h.dialogs[0].onClose(); assert.equal(await saving, true)
  assert.deepEqual(h.requests, [[{ id: 1, key: 'EXAMPLE', value: 'approved' }]])
  assert.equal(h.record.value, 'later edit'); assert.equal(h.lastSavedValues.get('EXAMPLE'), '"approved"')
})

test('identical saves join, different drafts serialize without losing the latest edit', async t => {
  const first = deferred(), calls = [], h = setup({ api: { putSystemCacheData: payload => {
    calls.push(structuredClone(payload)); return calls.length === 1 ? first.promise : Promise.resolve({ code: 200 })
  } } }); t.after(h.close)
  h.record.value = 'first'; const a = h.saveItem(h.group, h.record)
  assert.equal(h.saveItem(h.group, h.record), a); await flush()
  h.record.value = 'second'; const b = h.saveItem(h.group, h.record)
  assert.notEqual(a, b); await flush(); assert.equal(calls.length, 1)
  first.resolve({ code: 200 }); assert.equal(await a, true); assert.equal(await b, true)
  assert.deepEqual(calls.map(call => call[0].value), ['first', 'second'])
  assert.equal(h.lastSavedValues.get('EXAMPLE'), '"second"'); assert.equal(h.itemSaveLoading.EXAMPLE, false)
  assert.equal(h.pendingSaves.size, 0)
})

test('failed earlier save preserves a newer draft and the queued save can succeed', async t => {
  const first = deferred(), values = [], h = setup({ api: { putSystemCacheData: payload => {
    values.push(payload[0].value); return values.length === 1 ? first.promise : Promise.resolve({ code: 200 })
  } } }); t.after(h.close)
  h.record.value = 'first'; const a = h.saveItem(h.group, h.record); await flush()
  h.record.value = 'second'; const b = h.saveItem(h.group, h.record)
  first.reject(new Error('offline')); assert.equal(await a, false); assert.equal(h.record.value, 'second')
  assert.equal(await b, true); assert.deepEqual(values, ['first', 'second']); assert.equal(h.record.value, 'second')
})

test('failed unchanged draft rolls back and remains retryable; failure response is not success', async t => {
  let attempts = 0
  const h = setup({ api: { putSystemCacheData: async () => ({ code: ++attempts === 1 ? 400 : 200 }) } }); t.after(h.close)
  h.record.value = 'changed'; assert.equal(await h.saveItem(h.group, h.record), false)
  assert.equal(h.record.value, 'initial'); assert.equal(h.itemSaveLoading.EXAMPLE, false)
  h.record.value = 'retry'; assert.equal(await h.saveItem(h.group, h.record), true)
  assert.equal(h.lastSavedValues.get('EXAMPLE'), '"retry"')
})

test('cancelling or closing confirmation settles the pending save and does not erase newer edits', async t => {
  const h = setup({ item: { management_level: 2 } }); t.after(h.close)
  h.record.value = 'cancel'; const a = h.saveItem(h.group, h.record); await flush()
  h.dialogs[0].onCancel(); assert.equal(await a, false); assert.equal(h.record.value, 'initial')
  h.record.value = 'close'; const b = h.saveItem(h.group, h.record); await flush()
  h.record.value = 'new draft'; h.dialogs[1].onClose(); assert.equal(await b, false)
  assert.equal(h.record.value, 'new draft'); assert.equal(h.requests.length, 0); assert.equal(h.pendingSaves.size, 0)
})

test('nested submitted payloads are independent of the editor and omit item metadata', async t => {
  const h = setup({ item: { value: { version: 1, rows: [] } } }); t.after(h.close)
  h.record.value = { version: 1, rows: [{ name: 'saved' }] }
  const saving = h.saveItem(h.group, h.record); h.record.value.rows[0].name = 'later'
  assert.equal(await saving, true)
  assert.deepEqual(h.requests, [[{ id: 1, key: 'EXAMPLE', value: { version: 1, rows: [{ name: 'saved' }] } }]])
  assert.equal(h.record.value.rows[0].name, 'later')
})

test('save-before-test waits for the queued draft, and an unchanged or blank configured secret is not written', async t => {
  const first = deferred(), calls = [], h = setup({ api: { putSystemCacheData: payload => {
    calls.push(payload[0].value); return calls.length === 1 ? first.promise : Promise.resolve({ code: 200 })
  } } }); t.after(h.close)
  assert.equal(await h.saveItem(h.group, h.record), true); assert.equal(calls.length, 0)
  h.record.value = 'first'; const a = h.saveItem(h.group, h.record); await flush()
  h.record.value = 'latest'; const b = h.saveItem(h.group, h.record), beforeTest = h.saveBeforeTest(h.group)
  first.resolve({ code: 200 }); await Promise.all([a, b]); assert.equal(await beforeTest, true)
  assert.deepEqual(calls, ['first', 'latest'])
  const secret = item({ key: 'SECRET', is_secret: true, value: '' })
  assert.equal(await h.saveItem({ ...h.group, items: [secret] }, secret), true); assert.equal(calls.length, 2)
})

test('profile masking uses the saved snapshot and never replaces a newer edit', async t => {
  const pending = deferred(), h = setup({ item: { key: 'EVALUATION_AI_PROFILES', value: [] },
    api: { putSystemCacheData: () => pending.promise } }); t.after(h.close)
  h.record.value = [{ id: 'example', name: 'Example', provider_type: 'openai', model: 'example', base_url: 'https://example.com/v1', timeout: 120, enabled: true, api_key: 'example-test-value' }]
  const saving = h.saveItem(h.group, h.record); await flush()
  h.record.value = [{ id: 'example', api_key: 'new-example-value' }]
  pending.resolve({ code: 200 }); assert.equal(await saving, true)
  assert.equal(h.record.value[0].api_key, 'new-example-value')
  assert.equal(JSON.parse(h.lastSavedValues.get('EVALUATION_AI_PROFILES'))[0].api_key, '__KEEP_SECRET__')
})

test('identity, permission, environment and route changes cancel unresolved confirmations', async t => {
  for (const change of [h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'next-example',
    h => h.user.selected_environment = 1, h => h.permission.permissionKeys = ['example:read'],
    h => h.route.fullPath += '?group=api', h => h.route.path = '/other']) {
    const h = setup({ item: { management_level: 2 } })
    try {
      h.record.value = 'changed'; const saving = h.saveItem(h.group, h.record); await flush()
      change(h); assert.equal(await saving, false); h.dialogs[0].onOk(); await flush()
      assert.equal(h.requests.length, 0); assert.equal(h.messages.some(([kind]) => kind === 'success'), false)
    } finally { h.close() }
  }
})

test('background and KeepAlive pause cancel confirmation, and activation allows a fresh save', async t => {
  const h = setup({ item: { management_level: 2 } }); t.after(h.close)
  h.record.value = 'first'; const first = h.saveItem(h.group, h.record); await flush()
  h.visibility('hidden'); assert.equal(await first, false); assert.equal(await h.saveItem(h.group, h.record), false)
  h.visibility('visible'); const second = h.saveItem(h.group, h.record); await flush()
  h.callbacks.deactivate.forEach(f => f()); assert.equal(await second, false)
  assert.equal(await h.saveItem(h.group, h.record), false)
  h.callbacks.activate.forEach(f => f()); const third = h.saveItem(h.group, h.record); await flush()
  h.dialogs.at(-1).onOk(); assert.equal(await third, true); assert.equal(h.requests.length, 1)
})

test('late write receipts cannot restore, mask, acknowledge or notify a new context', async t => {
  const pending = deferred(), h = setup({ api: { putSystemCacheData: () => pending.promise } }); t.after(h.close)
  h.record.value = 'submitted'; const saving = h.saveItem(h.group, h.record); await flush()
  h.user.roleId++; h.record.value = 'new context'
  pending.resolve({ code: 200 }); assert.equal(await saving, false)
  assert.equal(h.record.value, 'new context'); assert.equal(h.lastSavedValues.get('EXAMPLE'), undefined)
  assert.equal(h.messages.some(([kind]) => kind === 'success'), false); assert.equal(h.itemSaveLoading.EXAMPLE, false)
})

test('old queued snapshots are discarded before another write when context changes', async t => {
  const pending = deferred(), calls = [], h = setup({ api: { putSystemCacheData: payload => {
    calls.push(payload[0].value); return pending.promise
  } } }); t.after(h.close)
  h.record.value = 'first'; const first = h.saveItem(h.group, h.record); await flush()
  h.record.value = 'second'; const second = h.saveItem(h.group, h.record)
  h.user.selected_environment = 1; pending.resolve({ code: 200 })
  assert.equal(await first, false); assert.equal(await second, false); assert.deepEqual(calls, ['first'])
})

test('enum refresh failure after a saved name does not roll back or repeat the write', async t => {
  let reads = 0
  const h = setup({ item: { key: 'ENVIRONMENT_DISPLAY_NAMES', value: {} },
    getEnum: async () => { reads++; throw Error('offline') } }); t.after(h.close)
  h.record.value = { 0: 'Example environment' }
  assert.equal(await h.saveItem(h.group, h.record), true)
  assert.deepEqual(h.record.value, { 0: 'Example environment' }); assert.equal(reads, 1)
  assert.equal(h.messages.some(([kind]) => kind === 'warning'), true)
  assert.equal(await h.saveItem(h.group, h.record), true); assert.equal(h.requests.length, 1)
})

test('parent normalization preserves malformed structured settings for the editor error state', t => {
  const h = setup(); t.after(h.close)
  for (const key of ['REPORT_DELIVERY_CONFIG', 'DATASOURCE_PERFORMANCE_POLICY', 'EVALUATION_AI_PROFILES', 'ENVIRONMENT_DISPLAY_NAMES']) {
    for (const value of ['broken JSON', null, false, 0]) assert.equal(h.normalizeEditValue(item({ key, value })), value)
    assert.deepEqual(h.normalizeEditValue(item({ key, value: '{"version":1}' })), { version: 1 })
    assert.deepEqual(h.normalizeEditValue(item({ key, value: '[1,2]' })), [1, 2])
  }
})

test('invalid environment names cannot turn into empty maps or string-coerced saves', async t => {
  const h = setup(); t.after(h.close)
  for (const value of ['broken JSON', null, [], { 0: false }, { 0: 123 }]) {
    const record = item({ key: 'ENVIRONMENT_DISPLAY_NAMES', value }), group = { ...h.group, items: [record] }
    assert.doesNotThrow(() => h.rememberSavedValues(group.items.length ? [group] : []))
    assert.equal(await h.saveItem(group, record), false)
    assert.deepEqual(record.value, value)
  }
  assert.equal(h.requests.length, 0)
})
