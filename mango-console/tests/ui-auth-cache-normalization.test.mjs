import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/uitest/auth-config')
const latest = {}
new Function('exports', ts.transpileModule(readFileSync('src/hooks/use-latest-request.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText)(latest)
const response = (id, name = 'Example auth') => ({ code: 200, data: { id, name, cache_data: {}, expires_at: null, remaining_minutes: null, last_refresh_error: '', refreshing: false } })
function setup(fetch = async id => response(id)) {
  const previous = globalThis.document, document = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = document
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], messages = []
  const route = vue.reactive({ path: '/uitest/auth-config/index', fullPath: '/uitest/auth-config/index' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 })
  const permission = vue.reactive({ permissionKeys: ['uitest.auth-config:read'] })
  const h = harness('UiAuthCacheDialog', 'visible,recordId,text,loading,error,open,closeCache:close,loadCache', {
    base, api: { getUiAuthConfigCache: id => { reads.push(id); return fetch(id) } }, modules: {
      vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
      '@/hooks/use-latest-request': latest, 'vue-router': { useRoute: () => route },
      '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@arco-design/web-vue': { Message: { error: value => messages.push(value) } },
    },
  })
  return { ...h, reads, messages, route, user, permission, callbacks,
    mount() { callbacks.mount.forEach(fn => fn()) },
    visibility(value) { document.visibilityState = value; document.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous },
  }
}

test('cache opens before the request settles, preserves ID zero and displays an independent response snapshot', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close)
  const opening = h.open({ id: 0 }); assert.equal(h.visible.value, true); assert.equal(h.loading.value, true); assert.deepEqual(h.reads, [0])
  const result = response(0); pending.resolve(result); await opening
  assert.equal(h.loading.value, false); assert.deepEqual(JSON.parse(h.text.value), result.data)
  result.data.name = 'Changed elsewhere'; assert.equal(JSON.parse(h.text.value).name, 'Example auth')
})
test('long string IDs pass unchanged to the existing cache API', async t => {
  const h = setup(); t.after(h.close); await h.open({ id: '90071992547409930000' })
  assert.deepEqual(h.reads, ['90071992547409930000']); assert.equal(JSON.parse(h.text.value).id, '90071992547409930000')
})
test('malformed records are rejected without sending cache requests', async t => {
  const h = setup(); t.after(h.close)
  for (const row of [null, [], {}, { id: false }, { id: 'invalid' }]) {
    await h.open(row); assert.equal(h.visible.value, false); assert.equal(h.loading.value, false); assert.equal(h.text.value, '')
  }
  assert.deepEqual(h.reads, []); assert.equal(h.messages.length, 5)
})
test('network, business and malformed responses keep a retryable local error without leaking exception content', async () => {
  for (const result of [() => { throw Error('example-private-content') }, () => ({ code: 403 }), () => ({ code: 200, data: null }), () => ({ code: 200, data: [] }), () => response(2)]) {
    let fail = true; const h = setup(id => fail ? result() : response(id))
    try {
      await h.open({ id: 0 }); assert.equal(h.visible.value, true); assert.equal(h.loading.value, false); assert.equal(h.text.value, '')
      assert.match(h.error.value, /加载失败/); assert.equal(h.error.value.includes('example-private-content'), false)
      fail = false; await h.loadCache(); assert.equal(h.error.value, ''); assert.equal(JSON.parse(h.text.value).id, 0)
    } finally { h.close() }
  }
})
test('duplicate retry clicks do not create concurrent reads in the same cache window', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close)
  const opening = h.open({ id: 0 }); await h.loadCache(); await h.loadCache(); assert.deepEqual(h.reads, [0])
  pending.resolve(response(0)); await opening; assert.equal(h.loading.value, false)
})
test('old cache success and finally cannot overwrite a new record or end its loading', async t => {
  const old = deferred(), current = deferred(), h = setup(id => id === 0 ? old.promise : current.promise); t.after(h.close)
  const first = h.open({ id: 0 }), second = h.open({ id: 1 })
  old.resolve(response(0, 'Old')); await first; assert.equal(h.loading.value, true); assert.equal(h.text.value, '')
  current.resolve(response(1, 'Current')); await second; assert.equal(h.loading.value, false); assert.equal(JSON.parse(h.text.value).name, 'Current')
})
test('closing and reopening clears content and ignores the previous failure', async t => {
  const old = deferred(); let count = 0; const h = setup(id => ++count === 1 ? old.promise : Promise.resolve(response(id))); t.after(h.close)
  const first = h.open({ id: 0 }); h.closeCache(); await h.open({ id: 0 }); old.reject(Error('network')); await first
  assert.equal(h.visible.value, true); assert.equal(h.error.value, ''); assert.equal(JSON.parse(h.text.value).id, 0)
  h.closeCache(); assert.equal(h.recordId.value, null); assert.equal(h.text.value, ''); assert.equal(h.loading.value, false)
})
test('identity changes close and erase caches, and late reads cannot restore them', async () => {
  for (const change of [h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '?id=2']) {
    const pending = deferred(), h = setup(() => pending.promise)
    try {
      const opening = h.open({ id: 0 }); change(h); assert.equal(h.visible.value, false); assert.equal(h.recordId.value, null)
      pending.resolve(response(0)); await opening; assert.equal(h.text.value, ''); assert.equal(h.error.value, ''); assert.equal(h.loading.value, false)
    } finally { h.close() }
  }
})
test('background, KeepAlive deactivation and unmount invalidate reads without reopening on return', async () => {
  for (const leave of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn()), h => h.callbacks.unmount.forEach(fn => fn())]) {
    const pending = deferred(), h = setup(() => pending.promise)
    try {
      h.mount(); const opening = h.open({ id: 0 }); leave(h); await h.open({ id: 1 }); assert.deepEqual(h.reads, [0])
      pending.resolve(response(0)); await opening; assert.equal(h.visible.value, false); assert.equal(h.text.value, '')
      h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(h.visible.value, false)
    } finally { h.close() }
  }
})
test('parent delegates cache viewing to its narrow window API', () => {
  const calls = [], source = path.join(base, 'index.vue'), onCache = method('onCache', { cacheRef: { value: { open: row => calls.push(row) } } }, source)
  const row = { id: 0 }; onCache(row); assert.equal(calls[0], row)
})
test('cache SFC compiles with local loading, retry, token code surface and no writable cache controls', async () => {
  const filename = path.join(base, 'components/UiAuthCacheDialog.vue'), source = readFileSync(filename, 'utf8'), { descriptor, errors } = parse(source)
  assert.deepEqual(errors, []); const script = compileScript(descriptor, { id: 'ui-auth-cache' })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: 'ui-auth-cache', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, []); const style = await compileStyleAsync({ source: descriptor.styles[0].content, filename, id: 'ui-auth-cache', scoped: true })
  assert.deepEqual(style.errors, []); assert.match(descriptor.template.content, /:loading="loading"/); assert.match(descriptor.template.content, /@click="loadCache"/)
  assert.match(descriptor.template.content, /mango-code-panel/); assert.doesNotMatch(descriptor.template.content, /v-html|a-input|textarea/)
})
