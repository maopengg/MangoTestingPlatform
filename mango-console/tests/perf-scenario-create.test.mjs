import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/scenario')
function setup(api = {}) {
  let version = 0
  const messages = [], requests = [], life = { mount: [], unmount: [], deactivate: [] }
  const previousDoc = globalThis.document
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = doc
  const h = harness('ScenarioCreateDialog', 'draft,visible,submitting,formRef,confirm', {
    base, props: { contextVersion: 0, isContextCurrent: captured => captured === version },
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      '@arco-design/web-vue': { Message: { success: text => messages.push(['success', text]), error: text => messages.push(['error', text]), warning: text => messages.push(['warning', text]) } },
      '@/api/perf': { createPerfScenario: async payload => { requests.push(payload); return api.create ? api.create(payload) : { code: 200, data: { id: 12 } } } },
    },
  })
  h.formRef.value = { validate: async () => undefined, clearValidate() {} }
  life.mount.forEach(fn => fn())
  return { ...h, doc, life, requests, messages, boundary: h.load('create.ts'),
    open: h.exposed.open, cancel: h.exposed.close, expire: () => version++,
    close: () => { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = previousDoc },
  }
}
const selection = { projectProduct: 10, module: 20 }
async function ready(h) { await h.open(selection); h.draft.name = 'Example' }

test('every open resets description and draft while retaining valid navigation defaults', async () => {
  const h = setup()
  await ready(h)
  assert.equal(h.draft.project_product, 10)
  assert.equal(h.draft.module, 20)
  h.draft.description = 'Unsaved description'; h.draft.default_executor_count = 7
  h.cancel(); await h.open(selection)
  assert.equal(h.draft.description, '')
  assert.equal(h.draft.default_executor_count, 1)
  assert.deepEqual(h.events, [])
  await h.open()
  assert.equal(h.draft.project_product, null)
  assert.equal(h.draft.module, null)
  h.close()
})

test('all load models serialize detached whitelist and use authoritative backend base targets', async () => {
  const h = setup()
  for (const type of ['concurrency', 'arrival_rate', 'iteration_rate']) {
    await ready(h)
    h.draft.project_product = ['1', '10']; h.draft.load_type = type; h.draft.ignored = 'extra'
    assert.equal(await h.confirm(), true)
    const payload = h.requests.at(-1)
    assert.equal(payload.project_product, 10)
    assert.equal(payload.module, 20)
    assert.equal('ignored' in payload, false)
    assert.equal(payload.target_rate, type === 'concurrency' ? null : 10)
    assert.equal(payload.target_users, type === 'concurrency' ? 10 : null)
    assert.equal(payload.max_vus, type === 'concurrency' ? null : 100)
    assert.equal(h.visible.value, false)
    assert.deepEqual(h.events.at(-1), ['created', 12, 0])
  }
  h.close()
})

test('cleared counts, invalid selections and invalid enumerations do not send HTTP', async () => {
  const h = setup()
  for (const patch of [
    { name: ' ' }, { name: 'x'.repeat(129) }, { default_executor_count: undefined },
    { default_executor_count: 0 }, { default_executor_count: 101 }, { default_executor_count: 1.5 },
    { project_product: [] }, { project_product: 'invalid' }, { module: null },
    { engine: 'invalid' }, { load_type: 'invalid' }, { description: 'x'.repeat(1001) },
  ]) {
    await ready(h); Object.assign(h.draft, patch)
    assert.equal(await h.confirm(), false)
    assert.equal(h.submitting.value, false)
  }
  assert.deepEqual(h.requests, [])
  h.close()
})

test('submission locks before async form validation; cancel and reopen cannot release it early', async () => {
  const h = setup(), validation = deferred()
  await ready(h)
  h.formRef.value.validate = () => validation.promise
  const first = h.confirm()
  assert.equal(h.submitting.value, true)
  h.cancel(); await ready(h)
  assert.equal(await h.confirm(), false)
  validation.resolve(undefined)
  assert.equal(await first, false)
  assert.deepEqual(h.requests, [])
  assert.equal(h.visible.value, true)
  assert.equal(h.submitting.value, false)
  h.close()
})

test('pending create captures payload, keeps physical lock and cannot close or navigate a reopened window', async () => {
  const response = deferred(), h = setup({ create: () => response.promise })
  await ready(h)
  const first = h.confirm()
  await flush()
  h.cancel(); await ready(h)
  h.draft.name = 'New draft'
  assert.equal(h.submitting.value, true)
  assert.equal(await h.confirm(), false)
  assert.equal(h.requests[0].name, 'Example')
  response.resolve({ code: 200, data: { id: 12 } })
  assert.equal(await first, false)
  assert.equal(h.visible.value, true)
  assert.deepEqual(h.events, [])
  assert.deepEqual(h.messages, [])
  h.close()
})

test('business errors and malformed IDs keep draft and allow explicit retry', async () => {
  let response = { code: 400, data: { id: 12 } }
  const h = setup({ create: async () => response })
  await ready(h)
  for (const fixture of [{ code: 400, data: { id: 12 } }, { code: 200, data: { id: 0 } }, { code: 200, data: { id: '12' } }, null]) {
    response = fixture
    assert.equal(await h.confirm(), false)
    assert.equal(h.visible.value, true)
    assert.equal(h.draft.name, 'Example')
    assert.equal(h.submitting.value, false)
    assert.deepEqual(h.events, [])
  }
  response = { code: 200, data: { id: 12 } }
  assert.equal(await h.confirm(), true)
  h.close()
})

test('parent identity invalidation is checked before child props render and before sending HTTP', async () => {
  const h = setup(), validation = deferred()
  await ready(h)
  h.formRef.value.validate = () => validation.promise
  const first = h.confirm()
  h.expire()
  assert.equal(h.props.contextVersion, 0)
  validation.resolve(undefined)
  assert.equal(await first, false)
  assert.deepEqual(h.requests, [])
  assert.equal(await h.open(selection), false)
  h.close()
})

test('background, KeepAlive and unmount close the editor and discard late create effects', async () => {
  for (const pause of [h => { h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange')) }, h => h.life.deactivate.forEach(fn => fn()), h => h.life.unmount.forEach(fn => fn())]) {
    const pending = deferred(), h = setup({ create: () => pending.promise })
    await ready(h)
    const first = h.confirm()
    await flush()
    pause(h)
    pending.resolve({ code: 200, data: { id: 12 } })
    assert.equal(await first, false)
    assert.equal(h.visible.value, false)
    assert.deepEqual(h.events, [])
    h.close()
  }
})

test('scenario list and create SFCs compile; pure create boundary passes strict TypeScript', () => {
  for (const relative of ['index.vue', 'components/ScenarioCreateDialog.vue']) {
    const filename = path.join(base, relative), { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: relative })
    const template = compileTemplate({ source: descriptor.template.content, filename, id: relative, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
  }
  const program = ts.createProgram(['create.ts', 'list.ts'].map(file => path.join(base, file)), {
    noEmit: true, strict: true, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
    moduleResolution: ts.ModuleResolutionKind.NodeJs, types: [], skipLibCheck: true,
    baseUrl: process.cwd(), paths: { '@/*': ['src/*'] },
  })
  const diagnostics = ts.getPreEmitDiagnostics(program).filter(item => item.file?.fileName.startsWith(base))
  assert.deepEqual(diagnostics.map(item => ts.flattenDiagnosticMessageText(item.messageText, '\n')), [])
})

test('actual parent passes navigation defaults and rejects stale created events after identity A-B-A', async () => {
  const route = vue.reactive({ path: '/perf/scenario/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const navigations = [], opened = []
  const h = harness('index', 'navigationCreateRef,createDialogRef,openCreate,onCreated,createContextVersion', {
    base, modules: {
      'vue-router': { useRoute: () => route, useRouter: () => ({ push: value => navigations.push(value) }) },
      '@/store/modules/user': { default: () => user },
      '@/hooks/table': { usePagination: () => vue.reactive({ page: 1, pageSize: 20, setTotalSize() {} }) },
    },
  })
  h.navigationCreateRef.value = { getCreateDefaults: () => selection }
  h.createDialogRef.value = { open: async value => opened.push(value), close() {} }
  await h.openCreate()
  assert.deepEqual(opened, [selection])
  const old = h.createContextVersion.value
  user.token = 'fixture-b'; user.token = 'fixture-a'
  h.onCreated(12, old)
  assert.deepEqual(navigations, [])
  h.onCreated(12, h.createContextVersion.value)
  assert.deepEqual(navigations, [{ path: '/perf/scenario/details', query: { id: 12 } }])
  h.close()
})
