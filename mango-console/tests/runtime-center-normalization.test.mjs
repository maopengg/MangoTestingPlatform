import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/system/runtime-center')
const summary = () => ({ healthy_service_count: 0, total_service_count: 6, api_worker_count: 0, api_worker_desired_count: 0, api_worker_thread_pool_size: 0, api_total_concurrency: 0, pending_task_count: 0, recent_error_count: 0 })
const service = (id = 'worker') => ({ id, service_name: 'worker', status: 'online', status_name: '正常', online_count: 1, stale_count: 0, instance_count: 1, instances: [], metadata: { running_count: 0, mode: 'request-observed' }, log_query: 'service="worker"', last_seen_at: '2026-11-09 10:00:00' })
const diagnostic = (key = 'api_worker_online') => ({ key, title: 'API Worker', status: 'warning', status_name: '警告', message: 'Example diagnostic' })
const data = () => ({ summary: summary(), services: [service()], diagnostics: [diagnostic(), { ...diagnostic('storage'), title: 'Storage' }] })
const ok = (value = data()) => ({ code: 200, data: value, msg: 'ok' })
function setup(options = {}) {
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, calls = [], messages = [], opens = []
  const route = vue.reactive({ path: '/system/runtime-center/index', fullPath: '/system/runtime-center/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: [] })
  const latest = {}
  new Function('exports', ts.transpileModule(readFileSync('src/hooks/use-latest-request.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText)(latest)
  const h = harness('index', 'summary,services,diagnostics,sourceLoading,errors,summaryCards,diagnosticSummary,configurationDiagnostics,openingLogId,refreshOverview,openLog', {
    base, transformSource: source => source.replace(/import\.meta\.env\.VITE_APP_LOG_PLATFORM_URL/g, JSON.stringify(options.logUrl || '')),
    api: { getRuntimeOverview() { calls.push('overview'); return options.read?.() ?? Promise.resolve(ok()) } }, modules: {
      vue: { ...vue, onMounted: f => callbacks.mount.push(f), onActivated: f => callbacks.activate.push(f), onDeactivated: f => callbacks.deactivate.push(f), onBeforeUnmount: f => callbacks.unmount.push(f) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/hooks/use-latest-request': latest, '@/hooks/table': { useTableColumn: value => value },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(kind => [kind, value => messages.push([kind, value])])) },
    },
  })
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const win = { location: { origin: 'https://example.com' }, open(...args) { opens.push(args); if (options.openError) throw Error('blocked') } }
  const nav = { clipboard: options.clipboard === null ? undefined : { writeText: options.clipboard || (async () => {}) } }
  let mounted = false, previousDocument, previousWindow, previousNavigator
  return { ...h, route, user, permission, calls, messages, opens, callbacks,
    mount() { mounted = true; previousDocument = globalThis.document; previousWindow = globalThis.window; previousNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator'); globalThis.document = doc; globalThis.window = win; Object.defineProperty(globalThis, 'navigator', { value: nav, configurable: true }); callbacks.mount.forEach(f => f()); callbacks.activate.forEach(f => f()) },
    async visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')); await flush() },
    close() { if (mounted) { const current = globalThis.document; globalThis.document = doc; callbacks.unmount.forEach(f => f()); globalThis.document = current === doc ? previousDocument : current; if (globalThis.window === win) globalThis.window = previousWindow; if (globalThis.navigator === nav) { if (previousNavigator) Object.defineProperty(globalThis, 'navigator', previousNavigator); else delete globalThis.navigator } } h.close() },
  }
}
test('finite counters preserve zero; missing data and malformed envelopes do not masquerade as healthy zero', t => {
  const h = setup(); t.after(h.close); const m = h.load('runtime-overview.ts')
  assert.equal(m.parseRuntimeSummary(summary()).api_worker_desired_count, 0)
  for (const value of [null, '', false, -1, 1.5, Infinity, '1']) assert.throws(() => m.parseRuntimeSummary({ ...summary(), pending_task_count: value }))
  assert.throws(() => m.parseRuntimeSummary({})); assert.throws(() => m.runtimeOverviewData({ code: 403, data: data() }))
  for (const value of [null, [], false]) assert.throws(() => m.runtimeOverviewData(ok(value)))
  assert.throws(() => m.parseRuntimeServices({})); assert.throws(() => m.parseRuntimeDiagnostics([diagnostic(), diagnostic()]))
})
test('grouped and redacted services retain server counts and never reconstruct missing logs or instances', t => {
  const h = setup(); t.after(h.close); const m = h.load('runtime-overview.ts')
  const row = { ...service(0), metadata: undefined, instances: undefined, log_query: undefined }
  const parsed = m.parseRuntimeServices([row])[0]
  assert.equal(parsed.id, 0); assert.equal(parsed.online_count, 1); assert.equal(parsed.instances, null); assert.equal(parsed.log_query, '')
  assert.deepEqual(m.serviceMetadata(parsed), ['-']); assert.equal(m.serviceInstanceNames(parsed), '-')
  const long = m.parseRuntimeServices([service('90071992547409931234')])[0]; assert.equal(long.id, '90071992547409931234')
  assert.deepEqual(m.serviceMetadata(m.parseRuntimeServices([service()])[0]), ['执行中 0', 'request-observed'])
  assert.throws(() => m.parseRuntimeServices([service(), service()])); assert.throws(() => m.parseRuntimeServices([{ ...service(), online_count: false }]))
})
test('legacy flat service grouping retains status precedence, latest heartbeat, instance selection and input ownership', t => {
  const h = setup(); t.after(h.close); const m = h.load('runtime-overview.ts')
  const flat = (id, status, time) => ({ id, service_name: 'worker', instance_name: `instance-${id}`, status, status_name: status, last_seen_at: time, metadata: { thread_pool_size: 0 }, log_query: 'service="worker"' })
  const input = [flat(1, 'stale', '2026-11-09 10:00:00'), flat(2, 'online', '2026-11-09 11:00:00'), flat(3, 'offline', '2026-11-09 12:00:00')], original = structuredClone(input)
  const group = m.parseRuntimeServices(input)[0]
  assert.equal(group.status, 'online'); assert.equal(group.online_count, 1); assert.equal(group.stale_count, 1); assert.equal(group.last_seen_at, '2026-11-09 12:00:00')
  assert.equal(m.serviceInstanceNames(group), 'instance-2'); assert.equal(m.serviceInstanceSummary(group), '在线 1 个实例'); assert.deepEqual(input, original)
  assert.equal(m.parseRuntimeServices([flat(1, 'stale', '')])[0].status, 'stale')
  assert.equal(m.parseRuntimeServices([{ ...flat(1, 'offline', ''), log_query: undefined }])[0].log_query, '')
  assert.throws(() => m.parseRuntimeServices([service(), flat(1, 'online', '')]))
})
test('single overview request coalesces and loads regions without adding polling or extra endpoints', async t => {
  const pending = deferred(); const h = setup({ read: () => pending.promise }); t.after(h.close)
  h.mount(); const a = h.refreshOverview(), b = h.refreshOverview(); assert.equal(a, b); await flush()
  assert.equal(h.calls.length, 1); assert.equal(h.sourceLoading.value, true); assert.equal(h.summaryCards.value[0].value, '-')
  pending.resolve(ok()); await a
  assert.equal(h.sourceLoading.value, false); assert.equal(h.summaryCards.value[1].value, '0/0'); assert.equal(h.summaryCards.value[3].value, 0)
  assert.equal(h.services.value.length, 1); assert.equal(h.configurationDiagnostics.value.length, 1); assert.equal(h.diagnosticSummary.value, '0 异常 / 1 警告')
})
test('service heartbeats and configuration diagnostics are displayed separately without counting worker configuration as a service', async t => {
  const worker = { ...service('api-worker'), service_name: 'api-worker', online_count: 2, instance_count: 2,
    instances: [1, 2].map(id => ({ id, service_name: 'api-worker', status: 'online', instance_name: `api-worker-${id}` })) }
  const h = setup({ read: async () => ok({ ...data(), services: [worker], diagnostics: [
    diagnostic('api_worker_online'), diagnostic('scheduler_online'), diagnostic('mcp_service_online'),
    diagnostic('realtime_service_online'), diagnostic('monitoring_service_online'),
    { ...diagnostic('api_worker_thread_pool_size'), title: 'API Worker 线程池配置', status: 'success' },
    { ...diagnostic('api_worker_desired_count'), title: 'API Worker 实例数', status: 'warning' },
    { ...diagnostic('storage'), title: 'Storage', status: 'error' },
  ] }) }); t.after(h.close)
  h.mount(); await flush()
  const m = h.load('runtime-overview.ts')
  assert.equal(h.services.value.length, 1)
  assert.equal(m.serviceInstanceSummary(h.services.value[0]), '在线 2 个实例')
  assert.equal(m.serviceInstanceNames(h.services.value[0]), 'api-worker-1、api-worker-2')
  assert.deepEqual(h.configurationDiagnostics.value.map(item => item.key), ['api_worker_thread_pool_size', 'api_worker_desired_count', 'storage'])
  assert.equal(h.diagnosticSummary.value, '1 异常 / 1 警告')
})
test('offline services and empty service results never imply an online worker from configured capacity', async t => {
  const offline = { ...service('api-worker'), service_name: 'api-worker', status: 'offline', status_name: '离线', online_count: 0, instance_count: 0 }
  let n = 0
  const h = setup({ read: async () => ok({ ...data(), services: ++n === 1 ? [offline] : [], summary: { ...summary(), api_worker_desired_count: 5, api_worker_thread_pool_size: 5 } }) }); t.after(h.close)
  h.mount(); await flush()
  assert.equal(h.load('runtime-overview.ts').serviceInstanceSummary(h.services.value[0]), '当前无在线实例')
  assert.equal(h.summaryCards.value[1].value, '0/5')
  await h.refreshOverview()
  assert.deepEqual(h.services.value, [])
  assert.equal(h.configurationDiagnostics.value.length, 1)
})
test('one malformed region does not discard valid neighboring data and retry recovers', async t => {
  let n = 0; const h = setup({ read: async () => ++n === 1 ? ok({ ...data(), summary: {} }) : ok() }); t.after(h.close)
  h.mount(); await flush(); assert.match(h.errors.overview, /重试/); assert.equal(h.services.value.length, 1); assert.equal(h.diagnostics.value.length, 2)
  await h.refreshOverview(); assert.equal(h.errors.overview, ''); assert.equal(h.summary.value.pending_task_count, 0)
})
test('malformed service data does not discard diagnostics or indicators', async t => {
  const h = setup({ read: async () => ok({ ...data(), services: [{}] }) }); t.after(h.close)
  h.mount(); await flush(); assert.match(h.errors.services, /重试/); assert.equal(h.summary.value.total_service_count, 6); assert.equal(h.diagnostics.value.length, 2)
})
test('malformed diagnostic data does not discard services or indicators', async t => {
  const h = setup({ read: async () => ok({ ...data(), diagnostics: [{}] }) }); t.after(h.close)
  h.mount(); await flush(); assert.match(h.errors.diagnostics, /重试/); assert.equal(h.summary.value.total_service_count, 6); assert.equal(h.services.value.length, 1)
})
test('network and backend denials clear stale values, close loading and permit retry', async t => {
  let n = 0; const h = setup({ read: async () => ++n === 1 ? ok() : n === 2 ? { code: 403, data: data() } : n === 3 ? Promise.reject(Error('offline')) : ok() }); t.after(h.close)
  h.mount(); await flush(); await h.refreshOverview(); assert.equal(h.summary.value, null); assert.equal(h.services.value.length, 0); assert.match(h.errors.services, /重试/)
  await h.refreshOverview(); assert.equal(h.sourceLoading.value, false); assert.match(h.errors.diagnostics, /重试/)
  await h.refreshOverview(); assert.equal(h.errors.services, ''); assert.equal(h.services.value.length, 1)
})
test('all identity dependencies invalidate old responses and reset prior context', async t => {
  const first = deferred(); let n = 0; const h = setup({ read: () => ++n === 1 ? first.promise : Promise.resolve(ok()) }); t.after(h.close)
  h.mount(); await flush(); h.user.token = 'new'; await flush(); first.resolve(ok({ ...data(), summary: { ...summary(), recent_error_count: 99 } })); await flush()
  assert.equal(h.summary.value.recent_error_count, 0)
  for (const change of [() => h.user.userId++, () => h.user.roleId++, () => h.user.selected_environment++, () => h.permission.permissionKeys.push('system.runtime_center:read'), () => { h.route.fullPath += '?x' }]) {
    const count = h.calls.length; change(); assert.equal(h.summary.value, null); await flush(); assert.equal(h.calls.length, count + 1)
  }
})
test('background and KeepAlive suspend reads and invalidate late responses; return loads fresh state', async t => {
  const pending = deferred(); let n = 0; const h = setup({ read: () => ++n === 1 ? pending.promise : Promise.resolve(ok()) }); t.after(h.close)
  h.mount(); await flush(); await h.visibility('hidden'); const count = h.calls.length; await h.refreshOverview(); assert.equal(h.calls.length, count); assert.equal(h.sourceLoading.value, false)
  await h.visibility('visible'); pending.resolve(ok({ ...data(), services: [] })); await flush(); assert.equal(h.services.value.length, 1)
  h.callbacks.deactivate.forEach(f => f()); await h.refreshOverview(); const before = h.calls.length
  h.callbacks.activate.forEach(f => f()); await flush(); assert.equal(h.calls.length, before + 1)
  h.route.path = '/other'; const current = h.calls.length; await h.refreshOverview(); assert.equal(h.calls.length, current)
})
test('clipboard waits for completion, guards duplicates and only then confirms success', async t => {
  const pending = deferred(), copies = []; const h = setup({ clipboard: query => { copies.push(query); return pending.promise } }); t.after(h.close)
  h.mount(); await flush(); const request = h.openLog(service(0)); await h.openLog(service(1))
  assert.equal(h.openingLogId.value, 0); assert.equal(copies.length, 1); assert.equal(h.messages.length, 0)
  pending.resolve(); await request; assert.equal(h.openingLogId.value, null); assert.deepEqual(h.messages, [['success', '日志查询条件已复制']])
})
test('clipboard failures retain error feedback and retry successfully', async t => {
  let n = 0; const h = setup({ clipboard: async () => { if (++n === 1) throw Error('denied') } }); t.after(h.close)
  h.mount(); await flush(); await h.openLog(service()); assert.equal(h.messages[0][0], 'error'); assert.equal(h.openingLogId.value, null)
  await h.openLog(service()); assert.equal(h.messages[1][0], 'success')
})
test('unavailable clipboard never reports successful copy', async t => {
  const h = setup({ clipboard: null }); t.after(h.close); h.mount(); await flush()
  await h.openLog(service()); assert.equal(h.messages[0][0], 'error'); assert.equal(h.openingLogId.value, null)
})
test('copy response after identity switch remains silent and cannot unlock another copy early', async t => {
  const pending = deferred(); const h = setup({ clipboard: () => pending.promise }); t.after(h.close)
  h.mount(); await flush(); const request = h.openLog(service()); h.user.roleId++; await flush()
  assert.equal(h.openingLogId.value, 'worker'); await h.openLog(service()); pending.resolve(); await request
  assert.equal(h.messages.length, 0); assert.equal(h.openingLogId.value, null)
})
test('log URL preserves query/hash, rejects unsafe configuration and opens with isolation', async t => {
  const h = setup({ logUrl: 'https://example.com/logs?tenant=example#panel' }); t.after(h.close); const m = h.load('runtime-overview.ts')
  for (const value of ['javascript:alert(1)', 'data:text/html,example', 'https://user:password@example.com']) assert.equal(m.runtimeLogUrl(value, 'x', 'https://example.com'), null)
  h.mount(); await flush(); await h.openLog(service())
  const [url, target, features] = h.opens[0]; assert.equal(new URL(url).searchParams.get('tenant'), 'example'); assert.equal(new URL(url).searchParams.get('query'), 'service="worker"'); assert.equal(new URL(url).hash, '#panel'); assert.equal(target, '_blank'); assert.equal(features, 'noopener,noreferrer')
  await h.openLog({ ...service(), log_query: '' }); assert.equal(h.messages.at(-1)[0], 'warning')
})
test('invalid log URL produces an error and recovers the button', async t => {
  const h = setup({ logUrl: 'javascript:alert(1)' }); t.after(h.close); h.mount(); await flush()
  await h.openLog(service()); assert.equal(h.opens.length, 0); assert.equal(h.messages[0][0], 'error'); assert.equal(h.openingLogId.value, null)
})
test('window exceptions produce errors and recover the button', async t => {
  const h = setup({ logUrl: 'https://example.com/logs', openError: true }); t.after(h.close); h.mount(); await flush()
  await h.openLog(service()); assert.equal(h.opens.length, 1); assert.equal(h.messages[0][0], 'error'); assert.equal(h.openingLogId.value, null)
})
test('runtime SFC script/template/style compile and config retains real table fields', async () => {
  const filename = path.join(base, 'index.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'runtime' })
  assert.deepEqual(compileTemplate({ filename, id: 'runtime', source: descriptor.template.content, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ filename, id: 'runtime', source: style.content, scoped: style.scoped, preprocessLang: style.lang })).errors, [])
})
