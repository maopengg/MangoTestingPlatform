import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush as flushVue, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/pytest/case'), response = data => ({ code: 200, data })
const record = (id = 1, patch = {}) => ({ id, name: 'Fixture ' + id, project_product: { id: 50, project_product: { id: 10, name: 'Product', project: { id: 20, name: 'Project' } } }, module: { id: 30 }, publication_status: 'unpublished', asset_status: 0, level: 0, scenario_layer: 0, scenario_type: 0, scenario_tags: ['regression'], scenario_description: '', case_people: { id: 2 }, ...patch })
async function flush() { await flushVue(); await new Promise(resolve => setImmediate(resolve)) }
function setup(kind = 'editor', api = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/pytest/case/index' })
  const projects = vue.reactive({ projectPytest2: [{ value: 20, label: 'Project', children: [{ value: 50, label: 'Product', project_product_id: 10 }, { value: 51, label: 'Other', project_product_id: 11 }] }], optionErrors: { pytest: false },
    getPytestProjectProductId(id) { return this.projectPytest2.flatMap(p => p.children).find(p => String(p.value) === String(id))?.project_product_id ?? null },
    projectPytestName: () => api.projects ? api.projects(projects) : Promise.resolve(),
  })
  const reads = [], writes = [], messages = [], life = { mount: [], unmount: [], activate: [], deactivate: [] }
  const oldDocument = globalThis.document, doc = Object.assign(new EventTarget(), { hidden: false }), listeners = new Set()
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (type, fn) => { listeners.add(fn); add(type, fn) }
  doc.removeEventListener = (type, fn) => { listeners.delete(fn); remove(type, fn) }
  globalThis.document = doc
  const bindings = kind === 'editor' ? 'visible,saving,record,draft,projectLoading,projectFailed,userLoading,userFailed,userOptions,realProductId,assetOptions,open,closeDialog:close,loadProjects,loadUsers,changeProject,save' : 'visible,syncing,loading,failed,draft,open,closeDialog:close,loadProjects,confirm'
  const h = harness(kind === 'editor' ? 'PytestCaseEditor' : 'PytestCaseSyncDialog', bindings, { base, modules: {
    vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/get-project': { useProject: () => projects },
    '@/store/modules/get-enum': { useEnum: () => ({ pytest_asset_status: [0, 1, 2, 3, 4].map(key => ({ key, title: String(key) })) }) },
    '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(key => [key, value => messages.push([key, value])])) },
    '@/api/user/user': { getUserName: () => { reads.push('users'); return api.users ? api.users() : Promise.resolve(response([{ key: 2, title: 'Fixture' }])) } },
    '@/api/pytest/case': {
      putPytestCase: payload => { writes.push(payload); return api.save ? api.save(payload) : Promise.resolve(response({ id: payload.id })) },
      postPytestCaseUpdate: id => { writes.push(id); return api.sync ? api.sync(id) : Promise.resolve(response({ created_count: 0 })) },
    },
  } })
  return { ...h, user, route, projects, reads, writes, messages, listeners, boundary: h.load('editor.ts'),
    mount() { life.mount.forEach(fn => fn()) }, pause() { life.deactivate.forEach(fn => fn()) }, resume() { life.activate.forEach(fn => fn()) },
    hide() { doc.hidden = true; doc.dispatchEvent(new Event('visibilitychange')) }, show() { doc.hidden = false; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = oldDocument },
  }
}

test('metadata boundary detaches tags, keeps zero/null, distinguishes Pytest and real products and whitelists payload', () => {
  const h = setup(), input = record(), parsed = h.boundary.caseEditorRecord(input), draft = h.boundary.caseDraft(parsed)
  input.scenario_tags.push('other'); assert.deepEqual(draft.scenario_tags, ['regression'])
  assert.equal(parsed.pytestProjectId, 50); assert.equal(parsed.projectProductId, 10)
  assert.equal(h.boundary.caseEditorRecord(record(1, { module: null })).module, null)
  const payload = h.boundary.caseEditorPayload({ ...draft, audit: 'ignored' }, parsed, h.projects.projectPytest2)
  assert.equal(payload.project_product, 50); assert.equal(payload.level, 0); assert.equal(payload.scenario_layer, 0)
  assert.deepEqual(Object.keys(payload).sort(), ['id', 'project_product', 'name', 'module', 'asset_status', 'level', 'scenario_layer', 'scenario_type', 'scenario_tags', 'scenario_description', 'case_people'].sort())
  for (const patch of [{ project_product: null }, { project_product: 20 }, { project_product: 999 }, { module: null }, { case_people: null }, { scenario_tags: [] }, { name: '  ' }]) assert.throws(() => h.boundary.caseEditorPayload({ ...draft, ...patch }, parsed, h.projects.projectPytest2))
  assert.equal(h.boundary.selectedPytestProject([20, 50], h.projects.projectPytest2), 50)
  h.close()
})

test('editing is synchronous and record-owned: open A-B-A never shares drafts or selected-file IDs', async () => {
  const h = setup(), input = record()
  h.open(input); await flush(); h.draft.name = 'Discard'; h.draft.scenario_tags.push('discard')
  h.open(record(2, { publication_status: 'published', asset_status: 1 })); await flush()
  assert.equal(h.record.value.id, 2); assert.deepEqual(h.assetOptions.value.map(x => x.key), [1])
  h.open(input); await flush(); assert.equal(h.record.value.id, 1); assert.equal(h.draft.name, 'Fixture 1')
  assert.deepEqual(h.draft.scenario_tags, ['regression']); assert.equal(h.realProductId.value, 10)
  h.changeProject([20, 51]); assert.equal(h.draft.project_product, 51); assert.equal(h.draft.module, null); assert.equal(h.realProductId.value, 11)
  assert.equal(await h.save(), false); assert.equal(h.writes.length, 0)
  h.close()
})

test('old user-option success or failure and finalizer cannot overwrite a reopened window; retries work', async () => {
  const pending = [deferred(), deferred()]; let index = 0
  const h = setup('editor', { users: () => pending[index++].promise })
  h.open(record()); h.closeDialog(); h.open(record(2)); await flush()
  pending[0].resolve(response([{ key: 99, title: 'Old' }])); await flush()
  assert.deepEqual(h.userOptions.value, []); assert.equal(h.userLoading.value, true)
  pending[1].reject(Error('failure')); await flush(); assert.equal(h.userFailed.value, true); assert.equal(h.userLoading.value, false)
  index = 0; pending[0] = deferred(); const read = h.loadUsers(); pending[0].resolve(response([{ key: 2, title: 'Current' }]))
  await read; assert.equal(h.userFailed.value, false); assert.equal(h.userOptions.value[0].title, 'Current')
  h.close()
})

test('shared project store reports errors without rejecting; both dialogs detect that and permit retry', async () => {
  for (const kind of ['editor', 'sync']) {
    const h = setup(kind, { projects: store => { store.optionErrors.pytest = true; return Promise.resolve() } })
    h.open(record()); await flush()
    assert.equal(kind === 'editor' ? h.projectFailed.value : h.failed.value, true)
    assert.equal(await (kind === 'editor' ? h.save() : h.confirm()), false); assert.equal(h.writes.length, 0)
    h.projects.projectPytestName = () => { h.projects.optionErrors.pytest = false; return Promise.resolve() }
    await h.loadProjects(); assert.equal(kind === 'editor' ? h.projectFailed.value : h.failed.value, false)
    h.close()
  }
})

test('metadata saves captured whitelist once, retains draft on failure and can retry', async () => {
  const pending = deferred(); let fail = true
  const h = setup('editor', { save: () => fail ? pending.promise : Promise.resolve(response({ id: 1 })) })
  h.open(record()); await flush(); const task = h.save(); assert.equal(h.saving.value, true)
  h.draft.name = 'Later'; h.draft.scenario_tags.push('later'); assert.equal(await h.save(), false)
  assert.equal(h.writes.length, 1); assert.equal(h.writes[0].name, 'Fixture 1'); assert.deepEqual(h.writes[0].scenario_tags, ['regression'])
  pending.reject(Error('fail')); assert.equal(await task, false); assert.equal(h.saving.value, false)
  assert.equal(h.visible.value, true); assert.equal(h.draft.name, 'Later'); fail = false
  assert.equal(await h.save(), true); assert.deepEqual(h.events.at(-1), ['saved', 1]); assert.equal(h.visible.value, false)
  h.close()
})

test('cancel does not release the physical metadata/sync lock; late success never emits or closes a new window', async () => {
  for (const kind of ['editor', 'sync']) {
    const pending = deferred(), h = setup(kind, { save: () => pending.promise, sync: () => pending.promise })
    h.open(record()); await flush(); if (kind === 'sync') h.draft.projectId = [20, 50]
    const task = kind === 'editor' ? h.save() : h.confirm(); h.closeDialog(); h.open(record(2))
    assert.equal(h.visible.value, false); assert.equal(kind === 'editor' ? h.saving.value : h.syncing.value, true)
    pending.resolve(response({ created_count: 0 })); assert.equal(await task, false)
    assert.equal(h.events.length, 0); assert.equal(h.messages.filter(x => x[0] === 'success').length, 0)
    h.open(record(2)); await flush(); assert.equal(h.visible.value, true)
    h.close()
  }
})

test('sync only submits a leaf Pytest product ID, does not guess a count, and rejects duplicate and failed submissions', async () => {
  let fail = true
  const h = setup('sync', { sync: () => Promise.resolve(fail ? { code: 403 } : response({ created_count: 0 })) })
  h.open(); await flush(); h.draft.projectId = 20; assert.equal(await h.confirm(), false)
  h.draft.projectId = [20, 50]; assert.equal(await h.confirm(), false); assert.equal(h.visible.value, true)
  fail = false; assert.equal(await h.confirm(), true); assert.deepEqual(h.writes, [50, 50]); assert.deepEqual(h.events.at(-1), ['synced', 50])
  h.close()
})

test('both dialogs synchronously invalidate on user/role/token/environment/route A-B-A', async () => {
  for (const kind of ['editor', 'sync']) for (const key of ['userId', 'roleId', 'token', 'selected_environment', 'fullPath']) {
    const pending = deferred(), h = setup(kind, { save: () => pending.promise, sync: () => pending.promise })
    h.open(record()); await flush(); if (kind === 'sync') h.draft.projectId = 50
    const task = kind === 'editor' ? h.save() : h.confirm(), target = key === 'fullPath' ? h.route : h.user, old = target[key]
    target[key] = typeof old === 'number' ? old + 1 : old + '-b'; target[key] = old
    assert.equal(h.visible.value, false); pending.resolve(response({})); assert.equal(await task, false); assert.equal(h.events.length, 0)
    h.close()
  }
})

test('background, KeepAlive and unmount clear drafts, refuse inactive opens and remove listeners', async () => {
  for (const kind of ['editor', 'sync']) {
    const h = setup(kind); h.mount(); assert.equal(h.listeners.size, 1)
    h.open(record()); await flush(); h.hide(); assert.equal(h.visible.value, false)
    h.open(record()); assert.equal(h.visible.value, false); h.show(); h.open(record()); await flush()
    h.pause(); assert.equal(h.visible.value, false); h.open(record()); assert.equal(h.visible.value, false)
    h.resume(); h.open(record()); await flush(); assert.equal(h.visible.value, true)
    h.close(); assert.equal(h.listeners.size, 0); h.open(record()); assert.equal(h.visible.value, false)
  }
})

test('sync waits for options and holds a physical lock until the request settles', async () => {
  const options = deferred(), pending = deferred(), h = setup('sync', { projects: () => options.promise, sync: () => pending.promise })
  h.open(); h.draft.projectId = 50
  assert.equal(h.loading.value, true); assert.equal(await h.confirm(), false); assert.equal(h.writes.length, 0)
  options.resolve(); await flush()
  const task = h.confirm(); assert.equal(h.syncing.value, true)
  assert.equal(await h.confirm(), false); assert.deepEqual(h.writes, [50])
  pending.reject(Error('fail')); assert.equal(await task, false); assert.equal(h.syncing.value, false)
  assert.equal(h.visible.value, true); assert.equal(h.draft.projectId, 50)
  h.close()
})

test('invalid user responses are errors, and a synchronous read failure still allows retry', async () => {
  let value = response([{ key: 2, title: false }]), fail = false
  const h = setup('editor', { users: () => { if (fail) throw Error('sync'); return Promise.resolve(value) } })
  h.open(record()); await flush(); assert.equal(h.userFailed.value, true); assert.deepEqual(h.userOptions.value, [])
  assert.equal(await h.save(), false); fail = true; await h.loadUsers(); assert.equal(h.userLoading.value, false)
  fail = false; value = response([{ key: 2, title: 'Fixture' }]); await h.loadUsers(); assert.equal(h.userFailed.value, false)
  assert.equal(await h.save(), true)
  h.close()
})

test('main and related editor SFCs compile with actual templates', () => {
  for (const file of ['index.vue', 'components/PytestCaseEditor.vue', 'components/PytestCaseSyncDialog.vue']) {
    const filename = path.join(base, file), source = readFileSync(filename, 'utf8'), parsed = parse(source, { filename })
    assert.deepEqual(parsed.errors, [])
    const script = compileScript(parsed.descriptor, { id: file })
    const template = compileTemplate({ source: parsed.descriptor.template.content, filename, id: file, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
  }
})
