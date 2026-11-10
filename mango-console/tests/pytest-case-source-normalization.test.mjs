import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush as flushVue, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/pytest/case'), response = data => ({ code: 200, data })
const record = (id = 1, patch = {}) => ({ id, name: 'Fixture ' + id, source_status: 0, asset_status: 0, feature_file_path: 'tests/fixture.feature', ...patch })
const source = (type = 'py', patch = {}) => response({ path: type === 'py' ? 'tests/test_fixture.py' : 'tests/fixture.feature', content: type === 'py' ? 'def test_fixture():\n    pass\n' : 'Feature: Fixture\n', commit_hash: 'fixture-commit', content_hash: 'fixture-content-' + type, ...patch })
const node = (patch = {}) => ({ nodeid: 'tests/test_fixture.py::TestFixture::test_fixture', node_type: 'method', class_name: 'TestFixture', method_name: 'test_fixture', parameter_id: null, line_number: 1, ...patch })
async function flush() { await flushVue(); await new Promise(resolve => setImmediate(resolve)) }
function setup(api = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/pytest/case/index' }), reads = [], methodReads = [], writes = [], runs = [], messages = [], confirmations = []
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }
  const oldDocument = globalThis.document, doc = Object.assign(new EventTarget(), { hidden: false }), listeners = new Set()
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (type, fn) => { listeners.add(fn); add(type, fn) }
  doc.removeEventListener = (type, fn) => { listeners.delete(fn); remove(type, fn) }
  globalThis.document = doc
  const h = harness('PytestCaseCodeDrawer', 'visible,target,fileType,saving,files,featureAbsent,nodes,methodsLoading,methodsFailed,running,confirmationOpen,hasFeature,activeFile,canSave,lineActions,open,closeDialog:close,readFile,loadMethods,changeFile,requestSave,runMethod', { base, props: { contextKey: 'fixture' }, modules: {
    vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user },
    '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(key => [key, value => messages.push([key, value])])), Modal: { confirm: options => {
      const modal = { options, closed: false, close() { modal.closed = true; options.onClose?.() } }; confirmations.push(modal); return modal
    } } },
    '@/api/pytest/case': {
      getPytestCaseRead: (id, type, silent) => { reads.push([id, type, silent]); return api.read ? api.read(id, type, silent) : Promise.resolve(source(type)) },
      getPytestCaseMethodNodes: id => { methodReads.push(id); return api.methods ? api.methods(id) : Promise.resolve(response([node()])) },
      postPytestCaseWrite: (...args) => { writes.push(args); return api.save ? api.save(...args) : Promise.resolve(source(args[2], { content: args[1] })) },
      getPytestCaseTest: (...args) => { runs.push(args); return api.run ? api.run(...args) : Promise.resolve(response({ status: 2 })) },
    },
  } })
  return { ...h, user, route, reads, methodReads, writes, runs, messages, confirmations, listeners, boundary: h.load('source.ts'),
    mount() { life.mount.forEach(fn => fn()) }, pause() { life.deactivate.forEach(fn => fn()) }, resume() { life.activate.forEach(fn => fn()) },
    hide() { doc.hidden = true; doc.dispatchEvent(new Event('visibilitychange')) }, show() { doc.hidden = false; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = oldDocument },
  }
}

test('source boundary keeps empty content, nullable commit and finite fields; missing hashes/content are errors', () => {
  const h = setup()
  assert.deepEqual(h.boundary.sourceSnapshot(source('py', { content: '', commit_hash: null, extra: 'ignored' })), { path: 'tests/test_fixture.py', content: '', commitHash: null, contentHash: 'fixture-content-py' })
  for (const value of [{ code: 403 }, response('legacy string'), source('py', { content: false }), source('py', { content: undefined }), source('py', { content_hash: '' }), source('py', { path: null }), source('py', { commit_hash: false })]) assert.throws(() => h.boundary.sourceSnapshot(value))
  assert.equal(h.boundary.executionEnvironment(0), 0); assert.equal(h.boundary.executionEnvironment('0'), 0)
  for (const value of [null, undefined, false, '', -1, 1.5]) assert.throws(() => h.boundary.executionEnvironment(value))
  h.close()
})

test('method boundary strips extras and keeps nullable fields, rejecting duplicate nodes and bad lines', () => {
  const h = setup(), input = node({ extra: true })
  const mapped = h.boundary.methodNodes(response([input]))[0]
  assert.equal('extra' in mapped, false); assert.equal(mapped.parameter_id, null)
  assert.deepEqual(Object.keys(h.boundary.methodTarget(mapped)).sort(), ['nodeid', 'node_type', 'class_name', 'method_name', 'parameter_id'].sort())
  for (const value of [response(null), response([node(), node()]), response([node({ line_number: 0 })]), response([node({ node_type: 'unknown' })]), response([node({ method_name: false })])]) assert.throws(() => h.boundary.methodNodes(value))
  assert.equal(h.boundary.codeTarget(record(1, { asset_status: 0 })).executable, true)
  assert.equal(h.boundary.codeTarget(record(1, { source_status: 2 })).executable, false)
  assert.equal(h.boundary.unboundFeature({ code: 32001 }), true)
  for (const value of [Error('network'), { code: 403 }, { code: 32013 }, null]) assert.equal(h.boundary.unboundFeature(value), false)
  h.close()
})

test('source, optional feature and methods load independently and duplicate reads coalesce', async () => {
  const py = deferred(), feature = deferred(), methods = deferred()
  const h = setup({ read: (_, type) => type === 'py' ? py.promise : feature.promise, methods: () => methods.promise })
  h.open(record()); await flush(); const first = h.readFile('py'), second = h.readFile('py')
  assert.equal(first, second); assert.equal(h.reads.length, 2); assert.equal(h.methodReads.length, 1)
  py.resolve(source()); await first
  assert.equal(h.files.py.loading, false); assert.equal(h.files.feature.loading, true); assert.equal(h.methodsLoading.value, true)
  assert.equal(h.canSave.value, true)
  methods.resolve(response([node()])); feature.resolve(source('feature')); await flush()
  assert.equal(h.lineActions.value.length, 1); assert.equal(h.files.feature.loading, false)
  h.close()
})

test('switching Python/Feature retains independent drafts and version snapshots without fetching over edits', async () => {
  const h = setup(); h.open(record()); await flush()
  h.files.py.draft = 'changed Python'; h.changeFile('feature'); h.files.feature.draft = 'changed Feature'; h.changeFile('py')
  assert.equal(h.activeFile.value.draft, 'changed Python'); assert.equal(h.files.feature.draft, 'changed Feature')
  assert.equal(h.files.py.snapshot.contentHash, 'fixture-content-py'); assert.equal(h.files.feature.snapshot.contentHash, 'fixture-content-feature')
  assert.equal(h.reads.length, 2); h.changeFile('invalid'); assert.equal(h.fileType.value, 'py')
  h.close()
})

test('record A-B-A ignores old read successes/failures/finalizers including late method results', async () => {
  const pending = Array.from({ length: 3 }, () => ({ py: deferred(), feature: deferred(), methods: deferred() })); let index = -1
  const h = setup({ read: (_, type) => pending[index][type].promise, methods: () => pending[index].methods.promise })
  for (const id of [1, 2, 1]) { index++; h.open(record(id)); await flush() }
  pending[0].py.resolve(source('py', { content: 'Old A' })); pending[0].feature.reject(Error('Old feature')); pending[0].methods.resolve(response([node({ nodeid: 'old' })]))
  pending[1].py.reject(Error('Old B')); pending[1].feature.resolve(source('feature')); pending[1].methods.reject(Error('Old methods')); await flush()
  assert.equal(h.files.py.draft, ''); assert.equal(h.files.py.loading, true); assert.equal(h.methodsLoading.value, true); assert.deepEqual(h.nodes.value, [])
  pending[2].py.resolve(source('py', { content: 'Current A' })); pending[2].feature.resolve(source('feature')); pending[2].methods.resolve(response([node()])); await flush()
  assert.equal(h.files.py.draft, 'Current A'); assert.equal(h.files.py.loading, false); assert.equal(h.methodsFailed.value, false)
  h.close()
})

test('known unbound Feature is absent; network/auth/bad responses remain failures with a retry', async () => {
  let error = { code: 32001 }
  const h = setup({ read: (_, type) => type === 'feature' && error ? Promise.reject(error) : Promise.resolve(source(type)) })
  h.open(record()); h.changeFile('feature'); await flush()
  assert.equal(h.featureAbsent.value, true); assert.equal(h.hasFeature.value, false); assert.equal(h.fileType.value, 'py'); assert.equal(h.files.feature.failed, false)
  for (error of [Error('network'), { code: 403 }, { code: 32013 }]) {
    h.open(record()); await flush(); assert.equal(h.hasFeature.value, true); assert.equal(h.files.feature.failed, true); assert.equal(h.featureAbsent.value, false)
  }
  error = null; assert.equal(await h.readFile('feature'), true); assert.equal(h.files.feature.failed, false); assert.equal(h.hasFeature.value, true)
  h.close()
})

test('failed or malformed initial source/method reads never permit blank saves and can recover', async () => {
  let fail = true
  const h = setup({ read: (_, type) => { if (fail && type === 'py') throw Error('sync'); return Promise.resolve(source(type)) }, methods: () => Promise.resolve(fail ? response({}) : response([node()])) })
  h.open(record()); await flush(); assert.equal(h.files.py.failed, true); assert.equal(h.canSave.value, false); assert.equal(h.methodsFailed.value, true)
  h.requestSave(); assert.equal(h.confirmations.length, 0); assert.equal(await h.runMethod(node()), false)
  fail = false; await Promise.all([h.readFile('py'), h.loadMethods()]); assert.equal(h.files.py.failed, false); assert.equal(h.methodsFailed.value, false); assert.equal(h.canSave.value, true)
  h.close()
})

test('save confirmation captures current file, record, draft and version before async confirmation', async () => {
  const pending = deferred(), h = setup({ save: () => pending.promise })
  h.open(record()); await flush(); h.files.py.draft = 'Captured'; h.requestSave(); h.requestSave()
  assert.equal(h.confirmations.length, 1); assert.equal(h.confirmationOpen.value, true); h.changeFile('feature'); assert.equal(h.fileType.value, 'py')
  h.files.py.draft = 'Later'; h.files.py.snapshot.contentHash = 'Later hash'
  const task = h.confirmations[0].options.onBeforeOk(); assert.equal(h.saving.value, true)
  assert.equal(await h.confirmations[0].options.onBeforeOk(), false)
  assert.deepEqual(h.writes[0], [1, 'Captured', 'py', 'fixture-commit', 'fixture-content-py'])
  pending.resolve(source('py', { content: 'Captured' })); assert.equal(await task, true)
  assert.equal(h.visible.value, false); assert.deepEqual(h.events.at(-1), ['saved', 1]); assert.equal(h.saving.value, false)
  h.close()
})

test('Feature saves its own hash and payload, supports empty content and nullable commit', async () => {
  const h = setup({ read: (_, type) => Promise.resolve(source(type, { commit_hash: null })) })
  h.open(record()); await flush(); h.changeFile('feature'); h.files.feature.draft = ''; h.requestSave()
  assert.equal(await h.confirmations[0].options.onBeforeOk(), true)
  assert.deepEqual(h.writes[0], [1, '', 'feature', undefined, 'fixture-content-feature'])
  h.close()
})

test('save failure and wrong-file responses keep the draft for retry; cancel/reopen cannot release a live write', async () => {
  const pending = deferred(); let first = true
  const h = setup({ save: (_, content, type) => first ? pending.promise : Promise.resolve(source(type, { content })) })
  h.open(record()); await flush(); h.files.py.draft = 'Retry'; h.requestSave()
  const task = h.confirmations[0].options.onBeforeOk(); pending.resolve(source('py', { path: 'wrong.py' }))
  assert.equal(await task, false); assert.equal(h.visible.value, true); assert.equal(h.files.py.draft, 'Retry'); assert.equal(h.saving.value, false)
  first = false; assert.equal(await h.confirmations[0].options.onBeforeOk(), true)
  h.close()
  const write = deferred(), next = setup({ save: () => write.promise }); next.open(record()); await flush(); next.requestSave()
  const old = next.confirmations[0].options.onBeforeOk(); next.closeDialog(); next.open(record(2)); assert.equal(next.visible.value, false); assert.equal(next.saving.value, true)
  write.resolve(source()); assert.equal(await old, false); assert.equal(next.events.length, 0)
  next.open(record(2)); await flush(); assert.equal(next.target.value.id, 2); assert.equal(next.visible.value, true)
  next.close()
})

test('stale save confirmations cannot submit in a new window; cancel continues editing', async () => {
  const h = setup(); h.open(record()); await flush(); h.files.py.draft = 'Keep'; h.requestSave()
  h.confirmations[0].options.onCancel(); assert.equal(h.visible.value, true); assert.equal(h.files.py.draft, 'Keep'); assert.equal(h.confirmationOpen.value, false)
  h.requestSave(); const old = h.confirmations[1]; h.closeDialog(); h.open(record(2)); await flush()
  assert.equal(old.closed, true); assert.equal(await old.options.onBeforeOk(), false); assert.equal(h.writes.length, 0); assert.equal(h.target.value.id, 2)
  h.close()
})

test('method execution accepts only owned nodes, captures record/environment including zero and prevents duplicates', async () => {
  const pending = deferred(), h = setup({ run: () => pending.promise }); h.open(record()); await flush()
  assert.equal(await h.runMethod(node({ nodeid: 'foreign' })), false)
  const task = h.runMethod(node({ method_name: 'injected', secret: 'ignored' })); assert.equal(await h.runMethod(node()), false)
  assert.equal(h.runs.length, 1); assert.deepEqual(h.runs[0], [1, 0, { nodeid: node().nodeid, node_type: 'method', class_name: 'TestFixture', method_name: 'test_fixture', parameter_id: null }])
  assert.equal(h.lineActions.value[0].loading, true)
  pending.resolve(response({})); assert.equal(await task, true); assert.deepEqual(h.events.at(-1), ['started', 1]); assert.equal(h.lineActions.value[0].loading, false)
  h.close()
})

test('method execute failure retries, prohibited assets remain blocked, and cancellation keeps pending-run lock', async () => {
  const pending = deferred(), h = setup({ run: () => pending.promise }); h.open(record(1, { asset_status: 2 })); await flush()
  assert.equal(await h.runMethod(node()), false); assert.equal(h.runs.length, 0)
  h.open(record()); await flush(); const task = h.runMethod(node()); h.closeDialog(); h.open(record()); await flush()
  assert.equal(await h.runMethod(node()), false); assert.equal(h.runs.length, 1)
  pending.reject(Error('fail')); assert.equal(await task, false); assert.equal(h.events.length, 0); assert.equal(h.running.value.size, 0)
  const retry = h.runMethod(node()); assert.equal(h.runs.length, 2); assert.equal(await retry, false); assert.equal(h.running.value.size, 0)
  h.close()
})

test('an old method finalizer cannot clear another record run or emit success into its window', async () => {
  const pending = [deferred(), deferred()]; let index = 0
  const h = setup({ run: () => pending[index++].promise }); h.open(record()); await flush()
  const old = h.runMethod(node()); h.closeDialog(); h.open(record(2)); await flush()
  const current = h.runMethod(node()); assert.equal(h.running.value.size, 2); assert.equal(h.lineActions.value[0].loading, true)
  pending[0].resolve(response({})); assert.equal(await old, false); assert.equal(h.running.value.size, 1)
  assert.equal(h.lineActions.value[0].loading, true); assert.equal(h.events.length, 0)
  pending[1].resolve(response({})); assert.equal(await current, true); assert.equal(h.running.value.size, 0)
  assert.deepEqual(h.events.at(-1), ['started', 2]); h.close()
})

test('identity/route/context A-B-A invalidates live writes and background/KeepAlive clean up the window', async () => {
  for (const key of ['userId', 'roleId', 'token', 'selected_environment', 'fullPath', 'contextKey']) {
    const pending = deferred(), h = setup({ save: () => pending.promise }); h.open(record()); await flush(); h.requestSave()
    const task = h.confirmations[0].options.onBeforeOk(), owner = key === 'fullPath' ? h.route : key === 'contextKey' ? h.props : h.user, old = owner[key]
    owner[key] = typeof old === 'number' ? old + 1 : old + '-b'; owner[key] = old
    assert.equal(h.visible.value, false); pending.resolve(source()); assert.equal(await task, false); assert.equal(h.events.length, 0); h.close()
  }
  const h = setup(); h.mount(); h.open(record()); await flush(); h.requestSave(); h.hide()
  assert.equal(h.confirmations[0].closed, true); assert.equal(h.visible.value, false); h.open(record()); assert.equal(h.visible.value, false)
  h.show(); h.open(record()); await flush(); h.pause(); assert.equal(h.visible.value, false); h.open(record()); assert.equal(h.visible.value, false)
  h.resume(); h.open(record()); await flush(); h.close(); assert.equal(h.listeners.size, 0); assert.equal(h.visible.value, false); h.open(record()); assert.equal(h.visible.value, false)
})

test('actual source drawer and main templates compile', () => {
  for (const file of ['index.vue', 'components/PytestCaseCodeDrawer.vue']) {
    const filename = path.join(base, file), parsed = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(parsed.errors, []); const script = compileScript(parsed.descriptor, { id: file })
    const template = compileTemplate({ source: parsed.descriptor.template.content, filename, id: file, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
  }
})
