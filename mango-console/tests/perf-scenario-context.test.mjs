import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/scenario/details')
const envelope = data => ({ code: 200, data })
const source = { release_id: 2, case_id: 7, name: 'Example', title: 'Example V1', disabled: false,
  compatible: true, incompatible_reasons: [], version_label: 'V1', revision_no: 1, module_full_path: 'Group / Module', steps: [] }
const record = (id = 1, patch = {}) => envelope({
  id, name: `Scenario ${id}`, engine: 'k6', project_product: 10, version: 3,
  source_case_release_id: 2, source_case: source, default_executor_count: 1,
  node_failure_policy: 'strict', min_ready_nodes: null, load_type: 'concurrency',
  load_config: { name: 'Example load', profile: 'constant_concurrency', duration_seconds: 60, target_users: 10 },
  performance_goal: null, ...patch,
})

function setup(api = {}, initialId = '1') {
  const route = vue.reactive({ path: '/perf/scenario/details', query: { id: initialId } })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }
  const previousDoc = globalThis.document
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const listeners = new Set(), add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (name, fn) => { listeners.add(fn); add(name, fn) }
  doc.removeEventListener = (name, fn) => { listeners.delete(fn); remove(name, fn) }
  globalThis.document = doc
  const requests = [], saved = [], messages = []
  const h = harness('index', 'id,form,sourceCase,scenarioRecord,caseItems,caseDetailVisible,loading,caseLoading,detailError,caseError,refreshBeforeWrite,refresh:load,loadCases,save,saving,validateConfig,validating,loadDialogRef,executeDialogRef', {
    base, modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn),
        onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      'vue-router': { useRoute: () => route, useRouter: () => ({}) },
      '@/store/modules/user': { default: () => user },
      '@arco-design/web-vue': { Message: { warning: message => messages.push(['warning', message]), success: message => messages.push(['success', message]), error: message => messages.push(['error', message]) } },
      '@/api/perf': {
        getPerfScenario: async id => { requests.push(id); return api.read ? api.read(id) : record(Number(id)) },
        getPerfScenarioSourceCases: async id => api.options ? api.options(id) : envelope([]),
        savePerfScenarioConfiguration: async (id, payload) => { saved.push({ id, payload }); return api.save ? api.save(id, payload) : envelope({ id: Number(id), version: 4 }) },
        validatePerfScenario: async id => api.validate ? api.validate(id) : envelope({ valid: true, step_count: 1, duration_seconds: 60 }),
      },
    },
  })
  return { ...h, route, user, life, doc, listeners, requests, saved, messages,
    mount: () => life.mount.forEach(fn => { void fn() }),
    pause: () => life.deactivate.forEach(fn => fn()),
    resume: () => life.activate.forEach(fn => fn()),
    hide: () => { doc.visibilityState = 'hidden'; doc.dispatchEvent(new Event('visibilitychange')) },
    show: () => { doc.visibilityState = 'visible'; doc.dispatchEvent(new Event('visibilitychange')) },
    close: () => { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = previousDoc },
  }
}

test('route ID A-B-A clears previous data synchronously and rejects old reads and failures', async () => {
  const reads = [deferred(), deferred(), deferred()]
  let index = 0
  const h = setup({ read: () => reads[index++].promise })
  const first = h.refresh()
  h.route.query.id = '2'
  const second = h.refresh()
  h.route.query.id = '1'
  const third = h.refresh()
  assert.equal(h.form.name, '')
  assert.equal(h.scenarioRecord.value, null)
  reads[0].resolve(record(1, { name: 'Old A' })); reads[1].reject(new Error('Old B'))
  await Promise.all([first, second])
  assert.equal(h.loading.value, true)
  assert.equal(h.detailError.value, false)
  reads[2].resolve(record(1, { name: 'New A' }))
  await third
  assert.equal(h.form.name, 'New A')
  assert.deepEqual(h.requests, ['1', '2', '1'])
  h.close()
})

test('user, role, token and environment A-B-A clear drafts and invalidate earlier identity reads', async () => {
  for (const key of ['userId', 'roleId', 'token', 'selected_environment']) {
    const pending = deferred(), h = setup({ read: () => pending.promise })
    h.form.name = 'Old identity draft'; h.caseDetailVisible.value = true
    const request = h.refresh(), previous = h.user[key]
    h.user[key] = typeof previous === 'string' ? 'fixture-b' : previous + 1
    h.user[key] = previous
    assert.equal(h.form.name, '')
    assert.equal(h.caseDetailVisible.value, false)
    pending.resolve(record())
    await request
    assert.equal(h.scenarioRecord.value, null)
    assert.equal(h.loading.value, false)
    h.close()
  }
})

test('save retains physical lock across scene change and cannot update the new scene version or feedback', async () => {
  const pending = deferred(), h = setup({ save: () => pending.promise })
  await h.refresh()
  const saving = h.save()
  h.route.query.id = '2'
  await h.refresh()
  assert.equal(h.saving.value, true)
  assert.equal(await h.save(), false)
  pending.resolve(envelope({ id: 1, version: 4 }))
  assert.equal(await saving, false)
  assert.equal(h.form.version, 3)
  assert.equal(h.form.name, 'Scenario 2')
  assert.equal(h.saving.value, false)
  assert.deepEqual(h.messages, [])
  h.close()
})

test('late validation neither starts in a changed context nor publishes an old validation success', async () => {
  const pending = deferred(), h = setup({ validate: () => pending.promise })
  await h.refresh()
  const validation = h.validateConfig()
  await flush()
  assert.equal(h.validating.value, true)
  h.user.roleId = 2
  pending.resolve(envelope({ valid: true, step_count: 1, duration_seconds: 60 }))
  await validation
  assert.equal(h.validating.value, false)
  assert.equal(h.messages.some(([, message]) => message.startsWith('校验通过')), false)
  h.close()
})

test('KeepAlive pause discards pending initial read and resumes it; established drafts survive later pause', async () => {
  const pending = deferred()
  let count = 0
  const h = setup({ read: () => ++count === 1 ? pending.promise : record() })
  h.mount()
  h.pause()
  pending.resolve(record(1, { name: 'Stale' }))
  await flush()
  assert.equal(h.form.name, '')
  h.resume()
  await flush()
  assert.equal(h.form.name, 'Scenario 1')
  assert.equal(count, 2)
  h.form.name = 'Unsaved'
  h.pause(); h.resume()
  await flush()
  assert.equal(h.form.name, 'Unsaved')
  assert.equal(count, 2)
  h.close()
})

test('background source read resumes independently without overwriting the metadata draft', async () => {
  const pending = deferred()
  let reads = 0
  const h = setup({ options: () => ++reads === 1 ? pending.promise : envelope([source]) })
  h.mount()
  await flush()
  h.form.name = 'Unsaved'
  h.hide()
  pending.reject(new Error('stale background failure'))
  await flush()
  assert.equal(h.caseError.value, false)
  h.show()
  await flush()
  assert.equal(h.caseItems.value.length, 1)
  assert.equal(h.form.name, 'Unsaved')
  assert.equal(h.requests.length, 1)
  h.close()
})

test('interrupted save requires explicit reload without destroying draft or releasing physical lock early', async () => {
  let version = 3
  const pending = deferred(), h = setup({ save: () => pending.promise, read: () => record(1, { version }) })
  h.mount(); await flush()
  h.form.name = 'Unsaved'
  const saving = h.save()
  h.hide(); h.show()
  assert.equal(h.refreshBeforeWrite.value, true)
  assert.equal(h.form.name, 'Unsaved')
  assert.equal(h.saving.value, true)
  assert.equal(await h.save(), false)
  version = 4
  pending.resolve(envelope({ id: 1, version: 4 }))
  assert.equal(await saving, false)
  assert.equal(h.form.version, 3)
  await h.refresh()
  assert.equal(h.refreshBeforeWrite.value, false)
  assert.equal(h.form.version, 4)
  assert.equal(h.requests.length, 2)
  h.close()
})

test('mounted scenario switch automatically reads its own ID and closes old configuration windows', async () => {
  const h = setup(), closed = []
  h.loadDialogRef.value = { close: () => closed.push('load') }
  h.executeDialogRef.value = { close: () => closed.push('execute') }
  h.mount(); await flush()
  h.route.query.id = '2'
  assert.equal(h.form.name, '')
  await flush()
  assert.equal(h.form.name, 'Scenario 2')
  assert.deepEqual(h.requests, ['1', '2'])
  assert.deepEqual(closed, ['load', 'execute'])
  h.close()
})

test('invalid and multivalue route IDs never reach HTTP; unmount removes all visibility listeners', async () => {
  for (const id of ['', '0', '-1', '1.5', 'x', ['1', '2'], '9007199254740992']) {
    const h = setup({}, id)
    h.mount(); await flush()
    await h.refresh()
    assert.deepEqual(h.requests, [])
    assert.equal(await h.save(), false)
    h.close()
    assert.equal(h.listeners.size, 0)
    await h.refresh()
    assert.deepEqual(h.requests, [])
  }
})

test('initial KeepAlive activation does not start source options before the in-flight metadata completes', async () => {
  const pending = deferred()
  let options = 0
  const h = setup({ read: () => pending.promise, options: async () => { options++; return envelope([]) } })
  h.mount(); h.resume()
  await flush()
  assert.equal(h.requests.length, 1)
  assert.equal(options, 0)
  pending.resolve(record())
  await flush()
  assert.equal(options, 1)
  h.close()
})

test('route departure preserves draft, blocks writes and restores the same draft on return', async () => {
  const h = setup()
  h.mount(); await flush()
  h.form.name = 'Unsaved'
  h.route.path = '/perf/run/index'
  h.route.query.id = '77'
  assert.equal(await h.save(), false)
  assert.equal(h.id.value, '1')
  h.route.query.id = '1'
  h.route.path = '/perf/scenario/details'
  await flush()
  assert.equal(h.form.name, 'Unsaved')
  assert.equal(h.requests.length, 1)
  assert.deepEqual(h.saved, [])
  h.close()
})
