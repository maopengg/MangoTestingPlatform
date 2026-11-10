import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/system/settings')
const config = () => ({ version: 1, enabled: false, include_details: true, failed_cases_only: true, include_screenshots: false, link_ttl_seconds: 604800 })
const ok = () => ({ code: 200, data: { defaults: config() } })
function setup(options = {}) {
  const life = { mount: [], activate: [], deactivate: [], unmount: [] }, calls = [], messages = []
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: [] })
  const route = vue.reactive({ path: '/system/settings/index', fullPath: '/system/settings/index' })
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const h = harness('ReportDeliveryEditor', 'draft,defaults,metadataLoading,metadataError,sampling,loadMetadata,save,sample', {
    base, props: { modelValue: config(), loading: false, ...options.props }, api: {
      getReportDeliveryMetadata() { calls.push(['metadata']); return options.read?.() ?? Promise.resolve(ok()) },
      downloadSampleReport(signal) { calls.push(['sample', signal]); return options.download?.(signal) ?? Promise.resolve() },
    }, modules: {
      vue: { ...vue, onMounted: f => life.mount.push(f), onActivated: f => life.activate.push(f), onDeactivated: f => life.deactivate.push(f), onBeforeUnmount: f => life.unmount.push(f) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@arco-design/web-vue': { Message: { warning: value => messages.push(['warning', value]), error: value => messages.push(['error', value]) } },
    },
  })
  let previous, mounted = false
  return { ...h, life, calls, messages, user, permission, route,
    mount() { mounted = true; previous = globalThis.document; globalThis.document = doc; life.mount.forEach(f => f()); life.activate.forEach(f => f()) },
    async visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')); await flush() },
    close() { if (mounted) { const current = globalThis.document; globalThis.document = doc; life.unmount.forEach(f => f()); globalThis.document = current === doc ? previous : current } h.close() },
  }
}
test('report DTO accepts finite fields and rejects broken metadata, booleans, TTL and versions', t => {
  const h = setup(); t.after(h.close); const m = h.load('report-delivery.ts')
  assert.deepEqual(m.parseReportDeliveryConfig({ enabled: true, extra: 'omit' }, config()), { ...config(), enabled: true })
  assert.deepEqual(m.parseReportDeliveryConfig(JSON.stringify(config())), config())
  assert.throws(() => m.parseReportDeliveryMetadata({ code: 403, data: { defaults: config() } }))
  for (const value of [null, [], false, {}, { ...config(), enabled: 'false' }, { ...config(), version: 2 }, { ...config(), link_ttl_seconds: 0 }, { ...config(), link_ttl_seconds: 1.5 }]) assert.throws(() => m.parseReportDeliveryConfig(value))
})
test('metadata requests coalesce; no save before successful read; failure retries without defaulting to empty', async t => {
  const first = deferred(); let n = 0; const h = setup({ read: () => ++n === 1 ? first.promise : Promise.resolve(ok()) }); t.after(h.close)
  h.mount(); const a = h.loadMetadata(), b = h.loadMetadata(); assert.equal(a, b); h.save(); assert.equal(h.events.length, 0)
  first.reject(Error('offline')); await a; assert.equal(h.metadataLoading.value, false); assert.match(h.metadataError.value, /重试/); assert.equal(h.draft.value, null)
  h.save(); assert.equal(h.events.length, 0); await h.loadMetadata(); assert.equal(h.metadataError.value, ''); assert.deepEqual(h.draft.value, config())
})
test('draft isolation, finite emitted snapshot and external rollback retain actual values', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  h.draft.value.enabled = true; assert.equal(h.props.modelValue.enabled, false); h.save()
  const payload = h.events.find(e => e[0] === 'update:modelValue')[1]; assert.equal(payload.enabled, true)
  h.draft.value.enabled = false; assert.equal(payload.enabled, true)
  h.props.modelValue = { ...config(), link_ttl_seconds: 300 }; await flush(); assert.equal(h.draft.value.link_ttl_seconds, 300)
  h.props.modelValue = null; await flush(); assert.equal(h.draft.value, null); h.save(); assert.equal(h.events.filter(e => e[0] === 'save').length, 1)
})
test('invalid local TTL cannot emit and correction can save; parent loading blocks repeated submissions', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  h.draft.value.link_ttl_seconds = undefined; h.save(); assert.equal(h.events.length, 0); assert.equal(h.messages[0][0], 'warning')
  h.draft.value.link_ttl_seconds = 300; h.props.loading = true; h.save(); assert.equal(h.events.length, 0)
  h.props.loading = false; h.save(); assert.equal(h.events[0][1].link_ttl_seconds, 300)
})
test('identity changes drop late metadata responses and read current defaults', async t => {
  const first = deferred(); let n = 0; const h = setup({ read: () => ++n === 1 ? first.promise : Promise.resolve(ok()) }); t.after(h.close)
  h.mount(); await flush(); h.user.token = 'new'; await flush(); first.resolve({ code: 200, data: { defaults: { ...config(), link_ttl_seconds: 300 } } }); await flush()
  assert.equal(h.defaults.value.link_ttl_seconds, 604800)
  for (const change of [() => h.user.userId++, () => h.user.roleId++, () => h.user.selected_environment++, () => h.permission.permissionKeys.push('system.settings:read'), () => { h.route.fullPath += '?x' }]) {
    const count = h.calls.length; change(); assert.equal(h.draft.value, null); await flush(); assert.equal(h.calls.length, count + 1)
  }
})
test('sample download is guarded, paused with AbortSignal, and never automatically restarted', async t => {
  const pending = deferred(); const h = setup({ download: () => pending.promise }); t.after(h.close); h.mount(); await flush()
  const download = h.sample(); await h.sample(); assert.equal(h.calls.filter(c => c[0] === 'sample').length, 1); assert.equal(h.sampling.value, true)
  const signal = h.calls.find(c => c[0] === 'sample')[1]; await h.visibility('hidden'); assert.equal(signal.aborted, true)
  await h.visibility('visible'); await h.sample(); assert.equal(h.calls.filter(c => c[0] === 'sample').length, 1)
  pending.reject(Error('late')); await download; assert.equal(h.sampling.value, false); assert.equal(h.messages.length, 0)
})
test('failed download permits retry without role preblocking; unavailable component prevents requests', async t => {
  let n = 0; const h = setup({ download: async () => { if (++n === 1) throw Error('offline') } }); t.after(h.close); h.mount(); await flush()
  await h.sample(); assert.equal(h.messages[0][0], 'error'); assert.equal(h.sampling.value, false)
  await h.sample(); assert.equal(h.calls.filter(c => c[0] === 'sample').length, 2)
  h.life.deactivate.forEach(f => f()); const count = h.calls.length; await h.sample(); await h.loadMetadata(); assert.equal(h.calls.length, count)
  h.life.activate.forEach(f => f()); await flush(); assert.ok(h.draft.value)
  h.route.path = '/other'; h.save(); assert.equal(h.events.length, 0)
})
test('report editor script, template and styles compile', async () => {
  const filename = path.join(base, 'components/ReportDeliveryEditor.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'report-settings' })
  assert.deepEqual(compileTemplate({ filename, id: 'report-settings', source: descriptor.template.content, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ filename, id: 'report-settings', source: style.content, scoped: style.scoped })).errors, [])
})
