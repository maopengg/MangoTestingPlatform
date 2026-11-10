import assert from 'node:assert/strict'
import test from 'node:test'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { settingsPageHarness } from './helpers/settings-page-harness.mjs'

const item = (values = {}) => ({ id: 0, key: 'EXAMPLE', describe: 'Example', value: 'server', value_type: 4,
  is_secret: false, management_level: 3, has_value: true, ...values })
const data = (record = item()) => [{ key: 'api', title: 'API', items: [record] }]
const ok = value => ({ code: 200, data: value })

test('group DTO preserves zero/long IDs, nullable metadata, independent JSON and only known fields', t => {
  const h = settingsPageHarness(); t.after(h.close); const m = h.load('config-records.ts')
  const raw = data(item({ describe: null, value_type: null, placeholder: null, value: { values: [0, false] }, obsolete: 'omit' }))
  const parsed = m.copyConfigGroups(ok(raw)); assert.equal(parsed[0].items[0].id, 0)
  assert.equal(parsed[0].items[0].describe, 'EXAMPLE'); assert.equal(parsed[0].items[0].value_type, null)
  assert.equal('obsolete' in parsed[0].items[0], false); assert.equal('placeholder' in parsed[0].items[0], false)
  parsed[0].items[0].value.values[0] = 1; assert.equal(raw[0].items[0].value.values[0], 0)
  assert.equal(m.copyConfigGroups(ok(data(item({ id: '90071992547409931234' }))))[0].items[0].id, '90071992547409931234')
  for (const response of [{ code: 403, data: data() }, ok(null), ok({}), ok([{}, {}]), ok([...data(), ...data()]),
    ok([{ ...data()[0], items: [item(), item()] }]), ok(data(item({ id: Number.MAX_SAFE_INTEGER + 1 }))),
    ok(data(item({ has_value: 'false' }))), ok(data(item({ is_secret: 1 }))), ok(data(item({ value_type: '1' })))]) assert.throws(() => m.copyConfigGroups(response))
})

test('initial settings and enum reads are independent, merged per resource, and expose failures with retry', async t => {
  const groups = deferred(), enums = deferred(); let reads = 0, enumReads = 0
  const h = settingsPageHarness({ api: { getSystemCacheDataGrouped: () => { reads++; return groups.promise } }, enumRead: () => { enumReads++; return enums.promise } }); t.after(h.close)
  h.mount(); const pending = h.doRefresh(); assert.equal(h.doRefresh(), pending); await flush()
  assert.equal(reads, 1); assert.equal(enumReads, 1); assert.equal(h.settingsLoading.value, true); assert.equal(h.enumsLoading.value, true)
  groups.resolve(ok(data())); await pending; assert.equal(h.settingsReady.value, true); assert.equal(h.settingsLoading.value, false)
  assert.equal(h.enumsLoading.value, true); enums.reject(Error('offline')); await flush()
  assert.equal(h.settingsGroups.value[0].items[0].value, 'server'); assert.match(h.enumsError.value, /重试/)
})

test('network, denial and malformed group reads stay errors rather than empty successful configuration', async t => {
  let count = 0
  const h = settingsPageHarness({ api: { getSystemCacheDataGrouped: async () => {
    count++; if (count === 1) throw Error('offline'); if (count === 2) return { code: 403, data: data() }; if (count === 3) return ok({}); return ok(data())
  } } }); t.after(h.close)
  h.mount(); await flush()
  assert.match(h.settingsError.value, /重试/); assert.equal(h.settingsReady.value, false)
  for (let i = 0; i < 2; i++) { await h.doRefresh(); assert.match(h.settingsError.value, /重试/); assert.equal(h.settingsGroups.value.length, 0) }
  await h.doRefresh(); assert.equal(h.settingsError.value, ''); assert.equal(h.settingsReady.value, true); assert.equal(h.settingsLoading.value, false)
})

test('context switching clears old records and late reads cannot replace the new response', async t => {
  const first = deferred(), second = deferred(); let reads = 0
  const h = settingsPageHarness({ api: { getSystemCacheDataGrouped: () => ++reads === 1 ? first.promise : second.promise } }); t.after(h.close)
  h.mount(); await flush(); h.user.roleId++; assert.equal(h.settingsGroups.value.length, 0); await flush()
  assert.equal(reads, 2); second.resolve(ok(data(item({ value: 'new context' })))); await flush()
  first.resolve(ok(data(item({ value: 'old context' })))); await flush()
  assert.equal(h.settingsGroups.value[0].items[0].value, 'new context'); assert.equal(h.settingsLoading.value, false)
})

test('background cancels the initial read and restores it once visible without polling', async t => {
  const first = deferred(); let reads = 0
  const h = settingsPageHarness({ api: { getSystemCacheDataGrouped: () => ++reads === 1 ? first.promise : Promise.resolve(ok(data())) } }); t.after(h.close)
  h.mount(); await flush(); h.visibility('hidden'); first.resolve(ok(data(item({ value: 'late' })))); await flush()
  assert.equal(reads, 1); assert.equal(h.settingsGroups.value.length, 0)
  h.visibility('visible'); await flush(); assert.equal(reads, 2); assert.equal(h.settingsReady.value, true)
  h.visibility('hidden'); h.visibility('visible'); await flush(); assert.equal(reads, 2)
})

test('KeepAlive deactivation invalidates reads and activation restores them', async t => {
  const pending = deferred(); let reads = 0
  const h = settingsPageHarness({ api: { getSystemCacheDataGrouped: () => ++reads === 1 ? pending.promise : Promise.resolve(ok(data())) } }); t.after(h.close)
  h.mount(); await flush(); h.callbacks.deactivate.forEach(f => f()); pending.resolve(ok(data())); await flush()
  assert.equal(h.settingsGroups.value.length, 0); h.callbacks.activate.forEach(f => f()); await flush()
  assert.equal(reads, 2); assert.equal(h.settingsReady.value, true)
})

test('resumed writes settle before reconciliation, and newer local drafts survive it', async t => {
  const pending = deferred(); let reads = 0
  const h = settingsPageHarness({ api: { getSystemCacheDataGrouped: async () => ok(data(item({ value: ++reads === 1 ? 'initial' : 'submitted' }))), putSystemCacheData: () => pending.promise } }); t.after(h.close)
  h.mount(); await flush(); const group = h.settingsGroups.value[0], record = group.items[0]
  record.value = 'submitted'; const saving = h.saveItem(group, record); await flush()
  h.visibility('hidden'); record.value = 'later draft'; h.visibility('visible'); await flush()
  assert.equal(reads, 1); assert.equal(h.settingsGroups.value[0].items[0].value, 'later draft')
  pending.resolve(ok(null)); assert.equal(await saving, false); await flush()
  assert.equal(reads, 2); assert.equal(h.settingsGroups.value[0].items[0].value, 'later draft')
  assert.equal(h.lastSavedValues.get('EXAMPLE'), '"submitted"')
})

test('refresh preserves reference identity of unchanged editor input and retains invalid local drafts', async t => {
  const h = settingsPageHarness({ api: { getSystemCacheDataGrouped: async () => ok(data(item({ value: { rows: [] } }))) } }); t.after(h.close)
  await h.doRefresh(); const first = h.settingsGroups.value[0].items[0].value
  await h.doRefresh(); assert.equal(h.settingsGroups.value[0].items[0].value, first)
  h.settingsGroups.value[0].items[0].value = 'unsubmitted'; await h.doRefresh()
  assert.equal(h.settingsGroups.value[0].items[0].value, 'unsubmitted')
})

test('environment values do not disappear while enum options are empty, and invalid data is preserved for correction', t => {
  const h = settingsPageHarness(); t.after(h.close)
  const environment = item({ key: 'DATA_FACTORY_VALIDATION_ENVIRONMENTS', value: '[0,2,2]' })
  assert.deepEqual(h.normalizeEditValue(environment), [0, 2]); assert.deepEqual(h.normalizePayloadValue(environment), [0, 2])
  for (const value of ['broken', false, [null], [''], [true], [-1], [1.5]]) {
    assert.deepEqual(h.normalizeEditValue({ ...environment, value }), value)
    assert.throws(() => h.normalizePayloadValue({ ...environment, value }))
  }
  assert.equal(h.normalizeEditValue(item({ value_type: 1, value: '0' })), 0)
  assert.equal(h.normalizeEditValue(item({ value_type: 1, value: 'invalid number' })), 'invalid number')
})

test('initial navigation scrolls only an explicitly requested section and later refreshes retain position', async t => {
  for (const requested of [undefined, '', 'unknown', 'email', 'system-services']) {
    const calls = [], h = settingsPageHarness({ group: requested, api: { getSystemCacheDataGrouped: async () => ok([]) } })
    try {
      h.panelRef.value = { scrollTop: 5, getBoundingClientRect: () => ({ top: 10 }), scrollTo: value => calls.push(value) }
      h.configSectionElements.set('email', { getBoundingClientRect: () => ({ top: 100 }) })
      h.sectionElements.set('system-services', { getBoundingClientRect: () => ({ top: 200 }) })
      await h.doRefresh()
      assert.deepEqual(calls, [{ top: requested === 'email' ? 95 : requested === 'system-services' ? 195 : 0, behavior: 'auto' }])
      await h.doRefresh(); assert.equal(calls.length, 1)
    } finally { h.close() }
  }
})

test('moving Pytest timeout into its own visual section does not drop execution-group validation', async t => {
  const items = [['TEST_SUITE_STUCK_RESET_MINUTES', 20], ['EXECUTOR_API_MAX_RUNTIME_MINUTES', 5],
    ['EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES', 10], ['EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES', 5]]
    .map(([key, value], id) => item({ key, value, id, value_type: 1 }))
  const writes = [], h = settingsPageHarness({ api: { getSystemCacheDataGrouped: async () => ok([{ key: 'execution', title: '执行', items }]),
    putSystemCacheData: async payload => { writes.push(payload); return ok(null) } } }); t.after(h.close)
  h.mount(); await flush(); const pytest = h.settingsGroups.value[0].items[2]
  pytest.value = 30
  assert.equal(await h.saveItem({ key: 'pytest', title: 'Pytest', items: [pytest] }, pytest), false)
  assert.equal(pytest.value, 10); assert.equal(writes.length, 0)
  assert.equal(h.messages.at(-1)[0], 'warning')
})
