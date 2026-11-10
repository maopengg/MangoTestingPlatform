import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const assets = loadModule('src/components/business/ui-case-step-create.ts')
const options = loadModule('src/views/uitest/case/details/configuration-options.ts', { '@/components/business/ui-case-step-create': assets })
const publicResponse = (name = 'Variable') => ({ code: 200, data: [{ id: 0, name, key: 'example', value: 'omit', type: 5, test_envs: [0], status: 1 }] })
const authResponse = () => ({ code: 200, data: [{ id: '90071992547409930000', name: 'Auth', auth_type: 0, test_env: null, status: 0, custom_code: 'omit' }] })
const datasourceResponse = () => ({ code: 200, data: [{ id: 0, name: 'Datasource', db_type: 1, password: 'omit' }] })
function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = []
  const state = vue.reactive({ productId: 0 }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const wrap = (name, defaultFn) => (...args) => { reads.push([name, ...args]); return overrides[name] ? overrides[name](...args) : defaultFn(...args) }
  const module = loadModule('src/views/uitest/case/details/composables/useCaseConfigurationOptions.ts', {
    vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
    '@/components/business/ui-case-step-create': assets, '../configuration-options': options,
    '@/api/uitest/public': { getUiPublic: wrap('public', async () => publicResponse()) }, '@/api/uitest/auth-config': { getUiAuthConfig: wrap('auth', async () => authResponse()) }, '@/api/data-factory': { getDataFactoryDatasourceAlias: wrap('datasources', async () => datasourceResponse()) },
  })
  const scope = vue.effectScope(), h = scope.run(() => module.useCaseConfigurationOptions(() => state.productId))
  return { ...h, state, route, user, permission, callbacks, reads,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); scope.stop(); globalThis.document = previous },
  }
}
test('option DTOs retain finite presentation only, zero/long IDs, default status and common environment', () => {
  const [pub] = options.readUiCasePublicChoices(publicResponse()); assert.equal(pub.value, 0); assert.deepEqual(pub.testEnvs, [0]); assert.equal(pub.disabled, true); assert.equal(pub.statusText, '默认开启'); assert.equal(pub.value === 'omit', false); assert.equal('custom_code' in pub, false)
  const [auth] = options.readUiCaseAuthChoices(authResponse()); assert.equal(auth.value, '90071992547409930000'); assert.equal(auth.authType, 0); assert.equal(auth.testEnv, null); assert.equal(auth.isCommonEnv, true); assert.equal('custom_code' in auth, false)
  assert.deepEqual(options.readUiCaseDatasourceChoices(datasourceResponse()), [{ value: 0, label: 'Datasource', dbType: 1 }])
  assert.throws(() => options.readUiCasePublicChoices({ code: 403 })); assert.throws(() => options.readUiCasePublicChoices({ code: 200, data: [{ id: 1, status: false }] })); assert.throws(() => options.readUiCaseDatasourceChoices({ code: 200, data: [{ id: 0, name: 'D', db_type: '90071992547409930000' }] }))
})
test('three resources load independently with exact product query and duplicate read deduplication', async t => {
  const pending = deferred(), h = setup({ public: () => pending.promise }); t.after(h.close)
  const first = h.publicVariables.load(), second = h.publicVariables.load(); assert.equal(first, second)
  await Promise.all([h.authorizations.load(), h.datasources.load()]); assert.equal(h.publicVariables.loading.value, true); assert.equal(h.authorizations.loading.value, false); assert.equal(h.datasources.loading.value, false)
  assert.deepEqual(h.reads.find(item => item[0] === 'public')[1], { page: 1, pageSize: 10000, project_product_id: 0 }); assert.deepEqual(h.reads.find(item => item[0] === 'datasources')[1], { project_product: 0, status: 1 })
  pending.resolve(publicResponse()); assert.equal(await first, true); assert.equal(h.publicVariables.rows.value[0].value, 0)
})
test('one failed resource retains retry while other metadata remains usable', async t => {
  let fail = true; const h = setup({ public: async () => fail ? { code: 403 } : publicResponse() }); t.after(h.close)
  await Promise.all([h.publicVariables.load(), h.authorizations.load(), h.datasources.load()]); assert.match(h.publicVariables.error.value, /失败/); assert.equal(h.publicVariables.loading.value, false); assert.equal(h.authorizations.rows.value.length, 1); assert.equal(h.datasources.rows.value.length, 1)
  fail = false; assert.equal(await h.publicVariables.load(), true); assert.equal(h.publicVariables.error.value, '')
})
test('product replacement rejects old results/finally and keeps latest loading until completion', async t => {
  const old = deferred(), current = deferred(), h = setup({ public: params => params.project_product_id === 0 ? old.promise : current.promise }); t.after(h.close)
  const first = h.publicVariables.load(); await flush(); h.state.productId = 2; await flush(); old.resolve(publicResponse('Old')); assert.equal(await first, false); assert.equal(h.publicVariables.loading.value, true); assert.deepEqual(h.publicVariables.rows.value, [])
  current.resolve(publicResponse('New')); await flush(); assert.equal(h.publicVariables.rows.value[0].name, 'New'); assert.equal(h.publicVariables.loading.value, false)
})
const changes = [h => h.state.productId = 2, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1', h => { h.state.productId = 2; h.state.productId = 0 }]
test('all identity/context changes invalidate old metadata including A-B-A without stale errors', async () => {
  for (const change of changes) {
    const pending = deferred(); let reads = 0; const h = setup({ public: () => ++reads === 1 ? pending.promise : Promise.resolve(publicResponse('New')) })
    try { const old = h.publicVariables.load(); await flush(); change(h); await flush(); pending.resolve(publicResponse('Old')); assert.equal(await old, false); assert.notEqual(h.publicVariables.rows.value[0]?.name, 'Old'); assert.equal(h.publicVariables.error.value, '') } finally { h.close() }
  }
})
test('background and KeepAlive pause reads, reject late data and resume silently', async () => {
  for (const leave of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn())]) {
    const pending = deferred(); let reads = 0; const h = setup({ public: () => ++reads === 1 ? pending.promise : Promise.resolve(publicResponse('Return')) })
    try { h.mount(); const loading = h.publicVariables.load(); await flush(); leave(h); pending.resolve(publicResponse('Old')); assert.equal(await loading, false); assert.deepEqual(h.publicVariables.rows.value, []); h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(h.publicVariables.rows.value[0].name, 'Return'); assert.equal(h.publicVariables.loading.value, false) } finally { h.close() }
  }
})
test('unmount clears finite metadata and rejects pending results', async t => {
  const pending = deferred(), h = setup({ public: () => pending.promise }); t.after(h.close)
  const loading = h.publicVariables.load(); await flush(); h.callbacks.unmount.forEach(fn => fn()); pending.resolve(publicResponse()); assert.equal(await loading, false); assert.deepEqual(h.publicVariables.rows.value, []); assert.equal(h.publicVariables.loading.value, false)
})
test('missing/invalid product never sends unscoped option queries', async t => {
  const h = setup(); t.after(h.close); h.state.productId = null; assert.equal(await h.publicVariables.load(), false); h.state.productId = 'bad'; assert.equal(await h.authorizations.load(), false); await flush(); assert.deepEqual(h.reads, [])
})
