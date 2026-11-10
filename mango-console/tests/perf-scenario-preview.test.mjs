import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/scenario/details')
const fixture = (patch = {}) => ({ code: 200, data: {
  scenario_version: 2, snapshot_hash: 'a'.repeat(64), script: 'export default function () {}',
  snapshot: JSON.stringify({ schema_version: 1, scenario_id: 1, scenario_version: 2 }), ignored: 'extra', ...patch,
} })
function setup(overrides = {}) {
  const state = vue.reactive({ id: '1', version: 0, current: true })
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const listeners = new Set(), add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (event, fn, ...args) => { if (event === 'visibilitychange') listeners.add(fn); return add(event, fn, ...args) }
  doc.removeEventListener = (event, fn, ...args) => { if (event === 'visibilitychange') listeners.delete(fn); return remove(event, fn, ...args) }
  const previousDoc = globalThis.document
  globalThis.document = doc
  const navigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  const copied = [], messages = [], requests = [], cache = new Map()
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: {
    clipboard: overrides.noClipboard ? undefined : { writeText: async value => {
      copied.push(value)
      if (overrides.copy) return overrides.copy(value)
    } },
  } })
  const modules = {
    vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn),
      onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
    '@arco-design/web-vue': { Message: { success: message => messages.push(['success', message]), error: message => messages.push(['error', message]) } },
    '@/api/perf': { getPerfScenarioScriptPreview: async id => { requests.push(id); return overrides.read ? overrides.read(id) : fixture() } },
  }
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename)
    const exports = {}; cache.set(filename, exports)
    const source = ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
    new Function('exports', 'require', source)(exports, id => {
      if (id in modules) return modules[id]
      if (id.startsWith('.')) return load(path.resolve(path.dirname(filename), id) + '.ts')
      { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw new Error(`Unmocked module: ${id}`) }
    })
    return exports
  }
  const scope = vue.effectScope()
  const preview = scope.run(() => load(path.join(base, 'composables/useScenarioScriptPreview.ts')).useScenarioScriptPreview({
    scenarioId: () => state.id, contextVersion: () => state.version,
    isContextCurrent: version => state.current && version === state.version,
  }))
  life.mount.forEach(fn => fn())
  return { ...preview, state, life, doc, listeners, copied, messages, requests,
    parser: load(path.join(base, 'script-preview.ts')).readScenarioScriptPreview,
    dispose() {
      life.unmount.forEach(fn => fn()); scope.stop()
      globalThis.document = previousDoc
      if (navigatorDescriptor) Object.defineProperty(globalThis, 'navigator', navigatorDescriptor)
      else delete globalThis.navigator
    },
  }
}

test('finite parser preserves exact code/JSON strings, whitelists fields and verifies scenario/version', () => {
  const h = setup(), source = fixture(), result = h.parser(source, '01')
  assert.equal(result.script, source.data.script)
  assert.equal(result.snapshot, source.data.snapshot)
  assert.equal('ignored' in result, false)
  source.data.script = 'changed'
  assert.notEqual(result.script, source.data.script)
  assert.equal(h.parser(fixture({ snapshot: JSON.stringify({ schema_version: 2, scenario_id: 1, scenario_version: 2 }) }), '1').scenario_version, 2)
  for (const value of [null, [], { code: 400, data: fixture().data }, fixture({ scenario_version: 0 }), fixture({ snapshot_hash: 'invalid' }), fixture({ script: '' }), fixture({ snapshot: '{}' }), fixture({ snapshot: 'bad-json' }), fixture({ snapshot: JSON.stringify({ schema_version: 1, scenario_id: 2, scenario_version: 2 }) }), fixture({ snapshot: JSON.stringify({ schema_version: 1, scenario_id: 1, scenario_version: 3 }) })])
    assert.throws(() => h.parser(value, '1'))
  h.dispose()
})

test('open/retry coalesce the current physical read and only its finalizer clears loading', async () => {
  const pending = deferred(), h = setup({ read: () => pending.promise })
  const first = h.open(), second = h.open(), third = h.reload()
  assert.equal(h.requests.length, 1)
  assert.equal(h.loading.value, true)
  pending.resolve(fixture())
  assert.deepEqual(await Promise.all([first, second, third]), [true, true, true])
  assert.equal(h.loading.value, false)
  assert.equal(h.preview.value.scenario_version, 2)
  h.dispose()
})

test('close/reopen discards late success and errors without closing or unlocking the newer read', async () => {
  const requests = [], h = setup({ read: () => { const item = deferred(); requests.push(item); return item.promise } })
  const first = h.open(); h.close(); const second = h.open()
  requests[0].reject(new Error('stale failure'))
  assert.equal(await first, false)
  assert.equal(h.visible.value, true)
  assert.equal(h.loading.value, true)
  assert.equal(h.error.value, false)
  requests[1].resolve(fixture())
  assert.equal(await second, true)
  assert.equal(h.preview.value.scenario_version, 2)
  h.dispose()
})

test('malformed/failed read remains in the drawer with local retry and no copyable stale content', async () => {
  let response = { code: 400, data: fixture().data }
  const h = setup({ read: () => response })
  assert.equal(await h.open(), false)
  assert.equal(h.visible.value, true)
  assert.equal(h.error.value, true)
  assert.equal(h.loading.value, false)
  assert.equal(h.preview.value, null)
  assert.equal(await h.copy(), false)
  response = fixture()
  assert.equal(await h.reload(), true)
  assert.equal(h.error.value, false)
  assert.equal(h.preview.value.scenario_version, 2)
  h.dispose()
})

test('context/id A-B-A clears sensitive preview immediately and rejects an old in-flight response', async () => {
  const pending = deferred(), h = setup({ read: () => pending.promise })
  const first = h.open()
  h.state.version = 1; h.state.version = 0
  assert.equal(h.visible.value, false)
  pending.resolve(fixture())
  assert.equal(await first, false)
  assert.equal(h.preview.value, null)
  assert.equal(await h.open(), true)
  h.state.id = '2'; h.state.id = '1'
  assert.equal(h.visible.value, false)
  assert.equal(h.preview.value, null)
  h.dispose()
})

test('copy uses the selected exact script or snapshot, handles missing clipboard and can retry after rejection', async () => {
  let fail = true
  const h = setup({ copy: () => { if (fail) throw new Error('fixture') } })
  await h.open()
  assert.equal(await h.copy(), false)
  assert.equal(h.copying.value, false)
  assert.equal(h.preview.value.script, fixture().data.script)
  fail = false
  assert.equal(await h.copy(), true)
  h.activeTab.value = 'snapshot'
  assert.equal(await h.copy(), true)
  assert.deepEqual(h.copied, [fixture().data.script, fixture().data.script, fixture().data.snapshot])
  h.dispose()
  const missing = setup({ noClipboard: true })
  await missing.open()
  assert.equal(await missing.copy(), false)
  assert.equal(missing.messages[0][0], 'error')
  assert.equal(missing.copying.value, false)
  missing.dispose()
})

test('physical clipboard lock survives closing and opening; stale completion gives no new-window toast', async () => {
  const pending = deferred(), h = setup({ copy: () => pending.promise })
  await h.open()
  const first = h.copy()
  assert.equal(h.copying.value, true)
  assert.equal(await h.copy(), false)
  h.close(); await h.open()
  assert.equal(h.copying.value, true)
  assert.equal(await h.copy(), false)
  pending.resolve()
  assert.equal(await first, false)
  assert.equal(h.copying.value, false)
  assert.deepEqual(h.messages, [])
  h.dispose()
})

test('tab A-B-A and context expiration suppress pending copy feedback without restarting a write', async () => {
  const pending = deferred(), h = setup({ copy: () => pending.promise })
  await h.open()
  const first = h.copy()
  h.activeTab.value = 'snapshot'; h.activeTab.value = 'script'
  pending.resolve()
  assert.equal(await first, false)
  assert.equal(h.copied.length, 1)
  assert.deepEqual(h.messages, [])
  h.dispose()
})

test('background and KeepAlive pause close preview, ignore late reads and permit explicit reopen after resume', async () => {
  const pending = deferred(), h = setup({ read: () => pending.promise })
  const first = h.open()
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  assert.equal(h.visible.value, false)
  assert.equal(await h.open(), false)
  pending.resolve(fixture())
  assert.equal(await first, false)
  h.doc.visibilityState = 'visible'
  assert.equal(await h.open(), true)
  h.life.deactivate.forEach(fn => fn())
  assert.equal(h.preview.value, null)
  assert.equal(await h.open(), false)
  h.life.activate.forEach(fn => fn())
  assert.equal(await h.open(), true)
  h.dispose()
})

test('unmount clears listeners/state and prevents later reads, copy feedback or reopening', async () => {
  const pending = deferred(), h = setup({ copy: () => pending.promise })
  await h.open()
  const first = h.copy()
  assert.equal(h.listeners.size, 1)
  h.dispose()
  assert.equal(h.listeners.size, 0)
  pending.resolve()
  assert.equal(await first, false)
  assert.equal(await h.open(), false)
  assert.equal(h.preview.value, null)
  assert.deepEqual(h.messages, [])
})

test('invalid route ID or expired context never opens a blank drawer or sends requests', async () => {
  const h = setup()
  for (const id of ['', '0', '-1', '1.5', '1,2', '9007199254740992']) {
    h.state.id = id
    assert.equal(await h.open(), false)
    assert.equal(h.visible.value, false)
  }
  h.state.id = '1'; h.state.current = false
  assert.equal(await h.open(), false)
  assert.equal(h.requests.length, 0)
  h.dispose()
})

test('actual parent opens preview without saving and identity change closes it synchronously', async () => {
  const route = vue.reactive({ path: '/perf/scenario/details', query: { id: '1' } })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 })
  let saves = 0
  const h = harness('index', 'scriptPreviewVisible,scriptPreview,openScriptPreview', { base, modules: {
    'vue-router': { useRoute: () => route, useRouter: () => ({}) },
    '@/store/modules/user': { default: () => user },
    '@/api/perf': { getPerfScenarioScriptPreview: async () => fixture(), savePerfScenarioConfiguration: async () => { saves++ } },
  } })
  assert.equal(await h.openScriptPreview(), true)
  assert.equal(saves, 0)
  assert.equal(h.scriptPreview.value.scenario_version, 2)
  user.roleId = 2
  assert.equal(h.scriptPreviewVisible.value, false)
  assert.equal(h.scriptPreview.value, null)
  h.close()
})

test('parent SFC compiles and the preview parser passes strict TypeScript', () => {
  const filename = path.join(base, 'index.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: filename })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  const program = ts.createProgram(['types.ts', 'script-preview.ts'].map(file => path.join(base, file)), {
    noEmit: true, strict: true, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
    moduleResolution: ts.ModuleResolutionKind.NodeJs, types: [], skipLibCheck: true,
  })
  const diagnostics = ts.getPreEmitDiagnostics(program)
  assert.equal(diagnostics.length, 0, ts.formatDiagnosticsWithColorAndContext(diagnostics, {
    getCanonicalFileName: value => value, getCurrentDirectory: () => process.cwd(), getNewLine: () => '\n',
  }))
})
