import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/gray/config-file')
const row = (id = 21, yamlId = 11) => ({
  id,
  yaml_file: yamlId,
  repository: { id: 31, name: 'Example repository', branch: 'main', test_env: 0 },
  file_path: 'config/example.yml',
  status: 0,
})
const page = (rows = [row()], total = rows.length) => ({ code: 200, data: rows, totalSize: total })
function manager(api) {
  const hooks = { deactivate: [], activate: [], unmount: [] }
  const f = harness('YamlContentDrawer', '', {
    base,
    api: { getGrayYamlFileBinding: api || (async () => page()) },
    modules: {
      vue: {
        ...vue,
        onDeactivated: (fn) => hooks.deactivate.push(fn),
        onActivated: (fn) => hooks.activate.push(fn),
        onBeforeUnmount: (fn) => hooks.unmount.push(fn),
      },
    },
  })
  const context = vue.ref('one'),
    blocked = vue.ref(false),
    scope = vue.effectScope()
  const { useYamlBindings } = f.load('composables/useYamlBindings.ts')
  const result = scope.run(() =>
    useYamlBindings({ contextKey: () => context.value, blocked: () => blocked.value })
  )
  return {
    ...result,
    context,
    blocked,
    hooks,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      scope.stop()
      f.close()
    },
  }
}

test('binding manager owns a minimal configuration snapshot and typed read rows', async () => {
  const calls = [],
    source = { id: 11, name: 'Example config', bindings: [], project_product: 2 }
  const m = manager(async (p) => {
    calls.push(p)
    return page([
      { ...row(), audit: 'Readonly', repository: { ...row().repository, access_token: 'masked' } },
    ])
  })
  m.open(source)
  source.id = 99
  source.name = 'Changed'
  assert.equal(m.drawer.visible, true)
  assert.equal(m.drawer.loading, true)
  assert.deepEqual(m.drawer.record, { id: 11, name: 'Example config' })
  await flush()
  assert.deepEqual(calls, [{ yaml_file: 11, page: 1, pageSize: 200 }])
  assert.deepEqual(m.drawer.dataList, [row()])
  assert.equal(m.drawer.error, false)
  assert.equal(m.drawer.loading, false)
  m.cleanup()
})

test('binding manager loads subsequent pages without silently omitting bindings beyond 200', async () => {
  const calls = [],
    rows = Array.from({ length: 201 }, (_, i) => row(i + 1))
  const m = manager(async (p) => {
    calls.push(p)
    return page(p.page === 1 ? rows.slice(0, 200) : rows.slice(200), 201)
  })
  m.open({ id: 11, name: 'Example config' })
  await flush()
  assert.equal(m.drawer.dataList.length, 201)
  assert.deepEqual(
    calls.map((p) => p.page),
    [1, 2]
  )
  assert.equal(m.drawer.loading, false)
  m.cleanup()
})

test('zero bindings is a successful empty result', async () => {
  const m = manager(async () => page([]))
  m.open({ id: 11, name: 'Example config' })
  await flush()
  assert.deepEqual(m.drawer.dataList, [])
  assert.equal(m.drawer.error, false)
  m.cleanup()
})

test('generic CRUD empty response can omit totalSize', async () => {
  const m = manager(async () => ({ code: 200, data: [] }))
  m.open({ id: 11, name: 'Example config' })
  await flush()
  assert.deepEqual(m.drawer.dataList, [])
  assert.equal(m.drawer.error, false)
  assert.equal(m.drawer.loading, false)
  m.cleanup()
})

test('failed reload retains current rows and retry clears the error', async () => {
  let calls = 0
  const m = manager(async () => {
    if (++calls === 2) throw Error('Network')
    return page()
  })
  m.open({ id: 11, name: 'Example config' })
  await flush()
  assert.equal(await m.loadBindings(), false)
  assert.equal(m.drawer.error, true)
  assert.deepEqual(m.drawer.dataList, [row()])
  assert.equal(m.drawer.loading, false)
  assert.equal(await m.loadBindings(), true)
  assert.equal(m.drawer.error, false)
  m.cleanup()
})

for (const invalid of [
  { ...row(), yaml_file: 12 },
  { ...row(), id: null },
  { ...row(), status: 7 },
  { ...row(), file_path: null },
  { ...row(), repository: null },
]) {
  test(`binding manager rejects invalid ownership or fields ${JSON.stringify(
    invalid
  )}`, async () => {
    const m = manager(async () => page([invalid]))
    m.open({ id: 11, name: 'Example config' })
    await flush()
    assert.equal(m.drawer.error, true)
    assert.equal(m.drawer.loading, false)
    assert.deepEqual(m.drawer.dataList, [])
    m.cleanup()
  })
}

for (const invalid of [
  { code: 400, data: [row()], totalSize: 1 },
  { code: 200, data: null, totalSize: 0 },
  { code: 200, data: [], totalSize: -1 },
  { code: 200, data: [], totalSize: 1 },
  page([row(), row()]),
  page([row()], 0),
]) {
  test(`binding manager exposes retry for malformed or incomplete pagination ${JSON.stringify(
    invalid
  )}`, async () => {
    const m = manager(async () => invalid)
    m.open({ id: 11, name: 'Example config' })
    await flush()
    assert.equal(m.drawer.error, true)
    assert.deepEqual(m.drawer.dataList, [])
    m.cleanup()
  })
}

test('changing totals between pages rejects the partial read rather than combining inconsistent pages', async () => {
  let calls = 0
  const m = manager(async () => (++calls === 1 ? page([row()], 2) : page([row(22)], 3)))
  m.open({ id: 11, name: 'Example config' })
  await flush()
  assert.equal(calls, 2)
  assert.equal(m.drawer.error, true)
  assert.deepEqual(m.drawer.dataList, [])
  m.cleanup()
})

test('switching configurations isolates pending data and loading from the old read', async () => {
  const first = deferred(),
    second = deferred()
  const m = manager((p) => (p.yaml_file === 11 ? first.promise : second.promise))
  m.open({ id: 11, name: 'First' })
  m.open({ id: 12, name: 'Second' })
  first.resolve(page())
  await flush()
  assert.equal(m.drawer.record.id, 12)
  assert.deepEqual(m.drawer.dataList, [])
  assert.equal(m.drawer.loading, true)
  second.resolve(page([row(22, 12)]))
  await flush()
  assert.deepEqual(m.drawer.dataList, [row(22, 12)])
  assert.equal(m.drawer.loading, false)
  m.cleanup()
})

test('old configuration ID cannot redirect a reload', async () => {
  let calls = 0
  const m = manager(async () => {
    calls++
    return page()
  })
  m.open({ id: 11, name: 'Example config' })
  await flush()
  assert.equal(await m.loadBindings(12), false)
  assert.equal(calls, 1)
  m.cleanup()
})

test('closing clears the manager and late failure cannot reopen or mark a new window', async () => {
  const pending = deferred(),
    m = manager(() => pending.promise)
  m.open({ id: 11, name: 'Example config' })
  m.onVisibleChange(false)
  pending.reject(Error('Late failure'))
  await flush()
  assert.equal(m.drawer.visible, false)
  assert.equal(m.drawer.record, null)
  assert.equal(m.drawer.loading, false)
  assert.equal(m.drawer.error, false)
  m.cleanup()
})

test('physical write or child editor guard blocks ordinary close and retargeting but not context invalidation', async () => {
  const m = manager()
  m.blocked.value = true
  m.open({ id: 11, name: 'Example config' })
  assert.equal(m.drawer.visible, false)
  m.blocked.value = false
  m.open({ id: 11, name: 'Example config' })
  await flush()
  m.blocked.value = true
  m.onVisibleChange(false)
  m.open({ id: 12, name: 'Next config' })
  assert.equal(m.drawer.visible, true)
  assert.equal(m.drawer.record.id, 11)
  m.context.value = 'two'
  assert.equal(m.drawer.visible, false)
  assert.equal(m.drawer.record, null)
  m.cleanup()
})

test('A-B-A context changes reject an older read even after the textual context returns', async () => {
  const pending = deferred(),
    m = manager(() => pending.promise)
  m.open({ id: 11, name: 'Example config' })
  m.context.value = 'two'
  m.context.value = 'one'
  pending.resolve(page())
  await flush()
  assert.equal(m.drawer.visible, false)
  assert.deepEqual(m.drawer.dataList, [])
  m.cleanup()
})

for (const hook of ['deactivate', 'unmount']) {
  test(`${hook} discards pending reads and deactivation can later resume with a fresh open`, async () => {
    const pending = deferred()
    let calls = 0
    const m = manager(() => (++calls === 1 ? pending.promise : Promise.resolve(page())))
    m.open({ id: 11, name: 'Example config' })
    m.hooks[hook].forEach((fn) => fn())
    m.open({ id: 11, name: 'Example config' })
    assert.equal(calls, 1)
    pending.resolve(page())
    await flush()
    assert.equal(m.drawer.visible, false)
    assert.deepEqual(m.drawer.dataList, [])
    if (hook === 'deactivate') {
      m.hooks.activate.forEach((fn) => fn())
      m.open({ id: 11, name: 'Example config' })
      await flush()
      assert.deepEqual(m.drawer.dataList, [row()])
    }
    m.cleanup()
  })
}

test('new retry owns loading and data after an older pending retry resolves', async () => {
  const first = deferred(),
    second = deferred()
  let calls = 0
  const m = manager(() => (++calls === 1 ? first.promise : second.promise))
  m.open({ id: 11, name: 'Example config' })
  const retry = m.loadBindings()
  first.resolve(page([row(21)]))
  await flush()
  assert.equal(m.drawer.loading, true)
  assert.deepEqual(m.drawer.dataList, [])
  second.resolve(page([row(22)]))
  assert.equal(await retry, true)
  assert.deepEqual(m.drawer.dataList, [row(22)])
  m.cleanup()
})

test('acknowledged binding status invalidates older reads before refresh and remains if refresh fails', async () => {
  const pending = deferred()
  let reads = 0
  const m = manager(async () => {
    if (++reads === 1) return page()
    if (reads === 2) return pending.promise
    throw Error('Reload failed')
  })
  m.open({ id: 11, name: 'Example config' })
  await flush()
  const old = m.loadBindings()
  m.applyMutation(21, 1)
  assert.equal(await m.loadBindings(), false)
  pending.resolve(page())
  assert.equal(await old, false)
  assert.equal(m.drawer.dataList[0].status, 1)
  assert.equal(m.drawer.error, true)
  m.applyMutation(21)
  assert.deepEqual(m.drawer.dataList, [])
  m.cleanup()
})
