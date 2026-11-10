import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import * as jsonc from 'jsonc-parser'
import path from 'node:path'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'
const lossless = loadModule('src/utils/lossless-json.ts', { 'jsonc-parser': jsonc })
const dto = loadModule('src/components/DataFactory/case-config-record.ts', { '@/utils/lossless-json': lossless })
const long = '90071992547409930000'
const row = (changes = {}) => ({ id: 0, source_type: 2, source_id: 0, name: 'Example', template: { id: long, name: 'Example template', project_product: { id: 0, name: 'Example product' }, entity: { id: 0, name: 'Example entity', table_name: 'example_table', datasource_alias: 0 }, module: 0, output_config: [{ field: 'id', key: 'example_id' }] }, sort: 0, status: 1, stage: 0, cleanup_strategy: 0, field_overrides: { example: { generator_type: 1, generator_config: { value: 0 } } }, ...changes })
const response = (...rows) => ({ code: 200, data: rows })
const draft = (changes = {}) => ({ id: null, template: long, name: 'Example', sort: 0, status: 1, stage: 0, cleanup_strategy: 0, field_overrides: { example: { generator_type: 1, generator_config: { value: 0 } } }, ...changes })
function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, states = [], reads = [], writes = [], messages = [], invalidations = []
  const state = vue.reactive({ id: 0, sourceType: 2, local: false, readonly: false, configs: [] }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' }), user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const api = Object.fromEntries(['postDataFactoryCaseConfig', 'putDataFactoryCaseConfig', 'putDataFactoryCaseConfigSort', 'deleteDataFactoryCaseConfig'].map(name => [name, (...args) => { writes.push([name, ...args]); return overrides.write ? overrides.write(name, ...args) : Promise.resolve({ code: 200, msg: 'saved' }) }]))
  api.getDataFactoryCaseConfig = query => { reads.push(query); return overrides.read ? overrides.read(query) : Promise.resolve(response(row({ source_id: query.source_id, source_type: query.source_type }))) }
  const module = loadModule('src/components/DataFactory/composables/useCaseConfigCollection.ts', {
    vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@arco-design/web-vue': { Message: { success: value => messages.push(value) } }, '@/api/data-factory': api, '../case-config-record': dto,
  })
  const scope = vue.effectScope(), h = scope.run(() => module.useCaseConfigCollection({ caseId: () => state.id, sourceType: () => state.sourceType, local: () => state.local, readonly: () => state.readonly, configs: () => state.configs, changed: value => states.push(value), invalidated: () => invalidations.push(true) }))
  return { ...h, state, route, user, permission, callbacks, states, reads, writes, messages, invalidations,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    cleanup() { callbacks.unmount.forEach(fn => fn()); scope.stop(); globalThis.document = previous },
  }
}
test('finite collection boundary preserves zero/long IDs and lossless overrides without audit fields', () => {
  const override = lossless.parseLosslessJson('{"example":{"generator_type":1,"generator_config":{"value":90071992547409930000}}}')
  const result = dto.readFactoryConfigRows([row({ field_overrides: override, update_user: { id: 2 }, create_time: 'example' })], { sourceId: 0, sourceType: 2 })[0]
  assert.equal(result.id, 0); assert.equal(result.template.id, long); assert.equal(result.template.entity.datasource_alias.id, 0); assert.equal(result.stage, 0); assert.equal(result.cleanup_strategy, 0); assert.equal('update_user' in result, false); assert.equal('create_time' in result, false); assert.equal(lossless.stringifyLosslessJson(result.field_overrides), lossless.stringifyLosslessJson(override)); assert.notEqual(result.field_overrides, override)
  for (const values of [{}, [row(), row()], [row({ source_id: 2 })], [row({ source_type: 3 })], [row({ source_type: null })], [row({ source_id: null })], [row({ id: null })], [row({ status: 9 })]]) assert.throws(() => dto.readFactoryConfigRows(values, { sourceId: 0, sourceType: 2 }))
})
test('one list load owns the count projection, deduplicates mount/activation and rejects failed count as zero', async t => {
  const pending = deferred(); let fail = true; const h = setup({ read: () => fail ? pending.promise : Promise.resolve(response(row())) }); t.after(h.cleanup)
  assert.equal(h.summary.value.count, null); h.mount(); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(h.reads.length, 1); assert.equal(h.loading.value, true); pending.reject(Error('network')); await flush(); assert.equal(h.summary.value.count, null); assert.equal(h.loading.value, false); assert.match(h.loadError.value, /重试/)
  fail = false; assert.equal(await h.load(), true); assert.equal(h.summary.value.count, 1); assert.equal(h.states.at(-1).count, 1); assert.deepEqual(h.reads[1], { source_type: 2, source_id: 0 })
})
test('save uses whitelist and deep fixed snapshot, with one physical write through reload', async t => {
  const pending = deferred(), refreshing = deferred(); let loaded = false; const h = setup({ write: () => pending.promise, read: () => loaded ? refreshing.promise : Promise.resolve(response(row())) }); t.after(h.cleanup); await h.load(); loaded = true
  const value = draft({ update_user: 99 }), saving = h.save(value); value.field_overrides.example.generator_config.value = 2; assert.equal(h.pending.value.kind, 'save'); assert.equal((await h.save(draft())).accepted, false); await flush(); const payload = h.writes[0][1]; assert.equal(payload.source_id, 0); assert.equal(payload.source_type, 2); assert.equal(payload.field_overrides.example.generator_config.value, 0); assert.equal('update_user' in payload, false)
  pending.resolve({ code: 200, msg: 'saved' }); await flush(); assert.notEqual(h.pending.value, null); assert.equal(h.loading.value, false); refreshing.resolve(response(row())); assert.equal((await saving).accepted, true); assert.equal(h.pending.value, null); assert.deepEqual(h.messages, ['saved'])
})
test('update zero ID remains PUT, status changes succeed only after server acceptance and preserve zero enum values', async t => {
  const h = setup(); t.after(h.cleanup); await h.load(); assert.equal((await h.save(draft({ id: 0 }))).accepted, true); assert.equal(h.writes[0][0], 'putDataFactoryCaseConfig'); assert.equal(await h.status(0, false), true); const payload = h.writes[1][1]; assert.equal(payload.status, 0); assert.equal(payload.stage, 0); assert.equal(payload.cleanup_strategy, 0); assert.equal(payload.template, long)
})
test('sort validates exact stable membership and copies order without optimistic mutation', async t => {
  const h = setup({ read: async () => response(row(), row({ id: 2 })) }); t.after(h.cleanup); await h.load(); assert.equal((await h.sort([0])).accepted, false); assert.equal((await h.sort([0, 0])).accepted, false); assert.equal((await h.sort([0, 3])).accepted, false)
  const order = [2, 0], sorting = h.sort(order); order.reverse(); await sorting; assert.deepEqual(h.writes[0], ['putDataFactoryCaseConfigSort', { source_type: 2, case_sort_list: [{ id: 2, sort: 0 }, { id: 0, sort: 1 }] }])
})
test('failed status/delete/sort can retry fixed snapshots while save retry remains in the editor', async () => {
  for (const kind of ['status', 'delete', 'sort', 'save']) {
    let fail = true; const h = setup({ write: async () => { if (fail) throw Error('network'); return { code: 200 } } })
    try { await h.load(); const action = kind === 'status' ? () => h.status(0, false) : kind === 'delete' ? () => h.remove(0) : kind === 'sort' ? () => h.sort([0]) : () => h.save(draft()); await action(); assert.match(h.operationError.value, /重试/); assert.equal(h.pending.value, null); assert.equal(h.canRetry.value, kind !== 'save'); fail = false; if (kind !== 'save') { assert.equal((await h.retry()).accepted, true); assert.deepEqual(h.writes[0], h.writes[1]) } } finally { h.cleanup() }
  }
})
test('successful delete followed by failed reload retains the acknowledged count and retries only GET', async t => {
  let fail = false; const h = setup({ read: async () => { if (fail) throw Error('network'); return response(row()) } }); t.after(h.cleanup); await h.load(); fail = true; assert.equal((await h.remove(0)).accepted, true); assert.match(h.loadError.value, /重试/); assert.equal(h.summary.value.count, 0); assert.equal(h.canRetry.value, false); fail = false; await h.load(); assert.equal(h.writes.length, 1)
})
test('acknowledged status/sort survive a failed reload without applying speculative state before acceptance', async () => {
  for (const kind of ['status', 'sort']) {
    const pending = deferred(); let fail = false; const h = setup({ read: async () => { if (fail) throw Error('network'); return response(row(), row({ id: 2 })) }, write: () => pending.promise })
    try { await h.load(); fail = true; const saving = kind === 'status' ? h.status(0, false) : h.sort([2, 0]); await flush(); assert.equal(h.rows.value[0].id, 0); assert.equal(h.rows.value[0].status, 1); pending.resolve({ code: 200 }); await saving; assert.match(h.loadError.value, /重试/); if (kind === 'status') assert.equal(h.rows.value[0].status, 0); else assert.deepEqual(h.rows.value.map(row => row.id), [2, 0]); assert.equal(h.writes.length, 1) } finally { h.cleanup() }
  }
})
test('accepted save with unknown refreshed records reports unknown count instead of a fabricated current total', async t => {
  let fail = false; const h = setup({ read: async () => { if (fail) throw Error('network'); return response(row()) } }); t.after(h.cleanup); await h.load(); fail = true; assert.equal((await h.save(draft())).accepted, true); assert.equal(h.summary.value.count, null); assert.match(h.loadError.value, /重试/); assert.equal(h.canRetry.value, false)
})
test('read started before or during a write cannot overwrite the post-write reload', async t => {
  const before = deferred(), during = deferred(), write = deferred(); let count = 0; const h = setup({ read: () => ++count === 1 ? before.promise : count === 2 ? during.promise : Promise.resolve(response(row({ name: 'new' }))), write: () => write.promise }); t.after(h.cleanup)
  const old = h.load(); await flush(); const saving = h.save(draft()); await flush(); const concurrent = h.load(false); await flush(); write.resolve({ code: 200 }); await saving; assert.equal(h.rows.value[0].name, 'new'); before.resolve(response(row({ name: 'old' }))); during.resolve(response(row({ name: 'during' }))); assert.equal(await old, false); assert.equal(await concurrent, false); assert.equal(h.rows.value[0].name, 'new')
})
const changes = [h => h.state.id = 2, h => h.state.sourceType = 3, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1', h => { h.state.id = 2; h.state.id = 0 }]
test('context changes reject late reads and cannot let old finally clear newer list loading', async () => {
  for (const change of changes) {
    const pending = deferred(), next = deferred(); let count = 0; const h = setup({ read: () => ++count === 1 ? pending.promise : next.promise })
    try { const old = h.load(); await flush(); change(h); await flush(); pending.resolve(response(row())); assert.equal(await old, false); assert.equal(h.summary.value.count, null); assert.equal(h.rows.value.length, 0); if (h.route.path !== '/other') assert.equal(h.loading.value, true); next.resolve(response(row({ source_id: h.state.id, source_type: h.state.sourceType }))); await flush(); assert.equal(h.invalidations.length > 0, true) } finally { h.cleanup() }
  }
})
test('physical save remains locked across identity changes and never closes or refreshes the replacement context', async () => {
  for (const change of changes) {
    const pending = deferred(), h = setup({ write: () => pending.promise })
    try { const saving = h.save(draft()); await flush(); change(h); await flush(); const reads = h.reads.length; assert.equal((await h.save(draft())).accepted, false); assert.equal(h.pending.value.kind, 'save'); pending.resolve({ code: 200, msg: 'old' }); const result = await saving; assert.equal(result.accepted, true); assert.equal(result.current(), false); assert.equal(h.pending.value, null); assert.equal(h.messages.length, 0); assert.equal(h.reads.length, reads) } finally { h.cleanup() }
  }
})
test('captured delete confirmation cannot delete after context changes even if the same ID reappears', async t => {
  const h = setup(); t.after(h.cleanup); await h.load(); const current = h.capture(); h.state.id = 2; await flush(); assert.equal((await h.remove(0, current)).accepted, false); assert.equal(h.writes.length, 0)
})
test('background/KeepAlive pause invalidates reads and writes while return resumes a silent list read', async () => {
  for (const leave of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn())]) {
    const pending = deferred(); let count = 0; const h = setup({ read: () => ++count === 1 ? pending.promise : Promise.resolve(response(row({ name: 'new' }))) })
    try { h.mount(); await flush(); leave(h); h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); await flush(); pending.resolve(response(row({ name: 'old' }))); await flush(); assert.equal(h.rows.value[0].name, 'new'); assert.equal(h.loading.value, false) } finally { h.cleanup() }
  }
})
test('local and readonly modes use private finite copies and never dispatch remote list or mutation requests', async () => {
  for (const mode of ['local', 'readonly']) {
    const h = setup()
    try { h.state[mode] = true; h.state.configs = [row({ id: 'local', template: { id: 1, name: 'Example', entity: { name: 'Entity', table_name: 'example_table' } } })]; await flush(); await h.load(); assert.equal(h.rows.value[0].id, 'local'); assert.equal(h.rows.value[0].template.entity.name, 'Entity'); assert.notEqual(h.rows.value[0].field_overrides, h.state.configs[0].field_overrides); assert.equal(h.summary.value.count, 1); assert.equal((await h.save(draft())).accepted, false); assert.equal(await h.status('local', false), false); assert.equal((await h.remove('local')).accepted, false); assert.equal(h.reads.length, 0); assert.equal(h.writes.length, 0) } finally { h.cleanup() }
  }
})
test('unmount prevents late data/count/notifications and retains a physical write until settlement', async t => {
  const pending = deferred(), h = setup({ write: () => pending.promise }); t.after(h.cleanup); const saving = h.save(draft()); await flush(); h.callbacks.unmount.forEach(fn => fn()); const states = h.states.length; pending.resolve({ code: 200 }); const result = await saving; assert.equal(result.current(), false); await flush(); assert.equal(h.messages.length, 0); assert.equal(h.states.slice(states).some(state => state.count > 0), false); assert.equal(h.pending.value, null)
})
function panel(overrides = {}) {
  const previous = globalThis.document; globalThis.document = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const previousWindow = globalThis.window; globalThis.window = { setTimeout, clearTimeout }
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const calls = [], modal = []
  const h = harness('index', 'form,visible,open,save,collection,deleteConfig,caseConfigList', {
    filename: path.resolve('src/components/DataFactory/CaseConfigPanel.vue'), props: { caseId: 0, sourceType: 2, projectProductId: 0 },
    api: { getDataFactoryCaseConfig: async () => response(row()), getDataFactoryDatasourceAlias: async () => response(), getDataFactoryTemplate: async () => response(), postDataFactoryCaseConfig: (...args) => { calls.push(['post', ...args]); return overrides.write?.(...args) ?? Promise.resolve({ code: 200 }) }, putDataFactoryCaseConfig: (...args) => { calls.push(['put', ...args]); return overrides.write?.(...args) ?? Promise.resolve({ code: 200 }) }, deleteDataFactoryCaseConfig: (...args) => { calls.push(['delete', ...args]); return Promise.resolve({ code: 200 }) } },
    Modal: { confirm: value => { const entry = { ...value, closed: false }; modal.push(entry); return { close: () => entry.closed = true } } },
    modules: { 'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@/utils/lossless-json': lossless },
  })
  return { ...h, calls, modal, user, cleanup() { h.close(); globalThis.document = previous; globalThis.window = previousWindow } }
}
test('actual panel editing uses an isolated draft and preserves zero IDs/enum values through PUT', async t => {
  const h = panel(); t.after(h.cleanup); const record = dto.readFactoryConfigRows([row()])[0]; await h.open(record); await flush()
  assert.equal(h.form.id, 0); assert.equal(h.form.project_product, 0); assert.equal(h.form.datasource_alias, 0); assert.equal(h.form.module, 0); assert.equal(h.form.template, long); assert.equal(h.form.stage, 0)
  h.form.field_overrides.example.generator_config.value = 5; assert.equal(record.field_overrides.example.generator_config.value, 0); assert.equal(await h.save(), true); assert.equal(h.calls[0][0], 'put'); assert.equal(h.calls[0][1].id, 0); assert.equal(h.calls[0][1].field_overrides.example.generator_config.value, 5); assert.equal(h.visible.value, false)
})
test('actual panel late save cannot close a replacement window and does not release physical lock on identity change', async t => {
  const pending = deferred(), h = panel({ write: () => pending.promise }); t.after(h.cleanup); await h.open(dto.readFactoryConfigRows([row()])[0]); const saving = h.save(); await flush(); h.user.selected_environment = 2; assert.equal(h.visible.value, false); assert.equal(h.collection.pending.value.kind, 'save'); assert.equal(await h.save(), false)
  pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.equal(h.calls.length, 1); assert.equal(h.collection.pending.value, null)
})
test('actual panel deletion confirmation closes when owner changes without dispatching deletion', async t => {
  const h = panel(); t.after(h.cleanup); await h.collection.load(); h.deleteConfig(h.caseConfigList.value[0]); assert.equal(h.modal.length, 1); h.props.caseId = 2; assert.equal(h.modal[0].closed, true); assert.equal(await h.modal[0].onBeforeOk(), false); assert.equal(h.calls.length, 0)
})
