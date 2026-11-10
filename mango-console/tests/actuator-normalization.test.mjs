import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { setupActuator, fakeTimers, actuator as row, readApi } from './helpers/actuator-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const page = (api = {}) =>
  setupActuator(
    'index',
    'rows,listLoading,loadError,doRefresh,onModifyStatus,onModifyDebug,statusPending,debugPending,isBusy,configPending,onConfigBusy,handleEditConfig,configRef',
    api
  )
const drawer = (api = {}) =>
  setupActuator(
    'ActuatorConfigDrawer',
    'open,close,visible,selectedActuator,configForm,loading,saving,ready,readError,reload:load,save',
    api
  )

test('page and configuration window compile; configuration has real options and local protocol', () => {
  for (const file of ['index.vue', 'components/ActuatorConfigDrawer.vue']) {
    const filename = path.resolve('src/views/equipment/actuator', file),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: file,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
  const s = page()
  try {
    const c = s.load('config.ts')
    assert.equal(c.configPollInterval, 1000)
    assert.equal(c.configPollAttempts, 20)
    assert.equal(c.browserOptions.length, 4)
    assert.equal(c.getTypeLabel('unsupported'), 'Pytest Web')
  } finally {
    s.dispose()
  }
})
test('latest list request owns rows and loading, errors keep rows and enable retry', async () => {
  const a = deferred(),
    b = deferred(),
    calls = []
  const s = page({
    getSystemSocketUserList: (p) => {
      calls.push(p)
      return calls.length === 1
        ? a.promise
        : calls.length === 2
        ? b.promise
        : Promise.reject(Error('fixture'))
    },
  })
  try {
    const first = s.doRefresh(),
      second = s.doRefresh()
    a.resolve({ data: [row('old')] })
    await first
    assert.equal(s.listLoading.value, true)
    b.resolve({ data: [row('current')] })
    await second
    assert.equal(s.rows.value[0].username, 'current')
    await s.doRefresh()
    assert.equal(s.loadError.value, true)
    assert.equal(s.listLoading.value, false)
    assert.equal(s.rows.value[0].username, 'current')
    assert.deepEqual(calls[0], { page: 1, pageSize: 100 })
  } finally {
    s.dispose()
  }
})
test('runtime switches update only after success and serialize per actuator', async () => {
  const pending = deferred(),
    calls = [],
    s = page({ getSystemSocketPutOpenStatus: (...a) => (calls.push(a), pending.promise) })
  try {
    s.rows.value = [row()]
    const change = s.onModifyStatus(true, 'worker-a')
    assert.equal(s.rows.value[0].is_open, false)
    assert.equal(s.isBusy('worker-a'), true)
    assert.equal(await s.onModifyDebug(true, 'worker-a'), false)
    pending.resolve({ code: 200, msg: 'ok' })
    assert.equal(await change, true)
    assert.equal(s.rows.value[0].is_open, true)
    assert.equal(s.isBusy('worker-a'), false)
    assert.deepEqual(calls, [['worker-a', 1]])
  } finally {
    s.dispose()
  }
})
test('failed runtime write releases lock and stale identity cannot apply status or notice', async () => {
  const pending = deferred(),
    s = page({ getSystemSocketPutDebug: () => pending.promise })
  try {
    s.rows.value = [row()]
    const change = s.onModifyDebug(true, 'worker-a')
    s.user.roleId = 2
    await flush()
    pending.resolve({ code: 200, msg: 'stale' })
    assert.equal(await change, false)
    assert.deepEqual(s.notices, [])
    assert.equal(s.debugPending.size, 0)
  } finally {
    s.dispose()
  }
})
test('cache and route invalidation discard old reads and activation resumes', async () => {
  const pending = deferred()
  let n = 0
  const s = page({
    getSystemSocketUserList: () =>
      ++n === 1 ? pending.promise : Promise.resolve({ data: [row()] }),
  })
  try {
    const first = s.doRefresh()
    s.lifecycle.deactivate()
    pending.resolve({ data: [row('old')] })
    await first
    assert.deepEqual(s.rows.value, [])
    await s.doRefresh()
    assert.equal(n, 1)
    s.lifecycle.activate()
    await flush()
    assert.equal(n, 2)
    assert.equal(s.rows.value[0].username, 'worker-a')
  } finally {
    s.dispose()
  }
})
test('reference-counted configuration locks survive overlapping old read completion', () => {
  const s = page()
  try {
    s.onConfigBusy('worker-a', 'read', true)
    s.onConfigBusy('worker-a', 'read', true)
    s.onConfigBusy('worker-a', 'read', false)
    assert.equal(s.isBusy('worker-a'), true)
    s.onConfigBusy('worker-a', 'read', false)
    assert.equal(s.isBusy('worker-a'), false)
    let captured
    s.configRef.value = { open: (r) => (captured = r), close() {} }
    s.handleEditConfig(row())
    assert.equal(captured.username, 'worker-a')
  } finally {
    s.dispose()
  }
})
test('normalization isolates drafts and whitelists fields while preserving zero and false', () => {
  const s = drawer()
  try {
    const { normalizeConfig } = s.load('form.ts'),
      source = {
        server: { host: 'https://example.com', password: 'must-not-submit' },
        ui: { web_type: 0, web_parallel: 0, web_max: false },
        pytest: { pytest_parallel: 0 },
        runtime: { is_open: false, debug: false },
        secret: 'must-not-submit',
      },
      draft = normalizeConfig(source)
    assert.equal(draft.ui.web_type, 0)
    assert.equal(draft.ui.web_parallel, 0)
    assert.equal(draft.pytest.pytest_parallel, 0)
    assert.equal(draft.runtime.is_open, false)
    assert.equal('secret' in draft, false)
    assert.equal('password' in draft.server, false)
    draft.server.host = 'changed'
    assert.equal(source.server.host, 'https://example.com')
  } finally {
    s.dispose()
  }
})
test('drawer opens immediately, reads by request ID and keeps values on cancel/reopen', async () => {
  const clock = fakeTimers(),
    ids = [],
    s = drawer({
      ...readApi({ server: { host: 'https://example.com' }, runtime: { debug: false } }),
      getSystemSocketActuatorConfigResult: async (id) => (
        ids.push(id),
        { data: { status: 'success', config: { server: { host: 'https://example.com' } } } }
      ),
    })
  try {
    s.open(row())
    assert.equal(s.visible.value, true)
    assert.equal(s.loading.value, true)
    await clock.tick()
    assert.equal(s.ready.value, true)
    assert.equal(s.configForm.server.host, 'https://example.com')
    assert.deepEqual(ids, ['read-fixture'])
    s.configForm.server.host = 'draft'
    s.exposed.close()
    assert.equal(s.visible.value, false)
    s.open(row())
    await clock.tick()
    assert.equal(s.configForm.server.host, 'https://example.com')
  } finally {
    s.dispose()
    clock.restore()
  }
})
test('close cancels a sleeping read without orphaned promise or reopening window', async () => {
  const clock = fakeTimers(),
    s = drawer(readApi())
  try {
    s.open(row())
    await flush()
    assert.equal(clock.jobs.size, 1)
    s.exposed.close()
    await flush()
    assert.equal(clock.jobs.size, 0)
    assert.equal(s.loading.value, false)
    assert.equal(s.visible.value, false)
    assert.deepEqual(
      s.events.filter((e) => e[0] === 'busy-change').map((e) => e[3]),
      [true, false]
    )
  } finally {
    s.dispose()
    clock.restore()
  }
})
test('rapidly switching actuators ignores late HTTP config reply', async () => {
  const clock = fakeTimers(),
    pending = deferred()
  let n = 0
  const s = drawer({
    ...readApi(),
    getSystemSocketActuatorConfigResult: () =>
      ++n === 1
        ? pending.promise
        : Promise.resolve({ data: { status: 'success', config: { server: { host: 'new' } } } }),
  })
  try {
    s.open(row('old'))
    await clock.tick()
    s.open(row('new'))
    await clock.tick()
    assert.equal(s.configForm.server.host, 'new')
    pending.resolve({ data: { status: 'success', config: { server: { host: 'old' } } } })
    await flush()
    assert.equal(s.configForm.server.host, 'new')
    assert.equal(s.selectedActuator.value.username, 'new')
  } finally {
    s.dispose()
    clock.restore()
  }
})
test('failed or expired read is visible and explicit retry can load without stale draft', async () => {
  const clock = fakeTimers()
  let fail = true
  const s = drawer({
    ...readApi(),
    getSystemSocketActuatorConfigResult: async () => ({
      data: fail ? { status: 'expired' } : { status: 'success', config: { ui: { web_type: 0 } } },
    }),
  })
  try {
    s.open(row())
    await clock.tick()
    assert.match(s.readError.value, /超时/)
    assert.equal(s.loading.value, false)
    fail = false
    const retry = s.reload()
    await clock.tick()
    assert.equal(await retry, true)
    assert.equal(s.ready.value, true)
    assert.equal(s.readError.value, '')
  } finally {
    s.dispose()
    clock.restore()
  }
})
test('local polling has bounded attempts, handles pending and validates response owner', async () => {
  const clock = fakeTimers()
  let calls = 0
  const s = drawer({
    ...readApi(),
    getSystemSocketActuatorConfigResult: async () => {
      calls++
      return { data: { status: 'pending' } }
    },
  })
  try {
    s.open(row())
    for (let i = 0; i < 20; i++) await clock.tick()
    assert.equal(calls, 20)
    assert.match(s.readError.value, /超时/)
    assert.equal(s.loading.value, false)
    assert.equal(clock.jobs.size, 0)
  } finally {
    s.dispose()
    clock.restore()
  }
})
test('mismatched response identity is rejected before configuration assignment', async () => {
  const clock = fakeTimers(),
    s = drawer({
      ...readApi(),
      getSystemSocketActuatorConfigResult: async () => ({
        data: {
          status: 'success',
          username: 'other-worker',
          config: { server: { host: 'wrong' } },
        },
      }),
    })
  try {
    s.open(row())
    await clock.tick()
    assert.match(s.readError.value, /不匹配/)
    assert.equal(s.ready.value, false)
    assert.equal(s.configForm.server.host, '')
  } finally {
    s.dispose()
    clock.restore()
  }
})
test('save freezes username and payload, waits for acknowledgement and rejects repeat click', async () => {
  const clock = fakeTimers(),
    pending = deferred(),
    calls = [],
    s = drawer({
      ...readApi(),
      putSystemSocketActuatorConfig: (...a) => (
        calls.push(a), Promise.resolve({ data: { request_id: 'save-fixture' } })
      ),
      getSystemSocketActuatorConfigSaveResult: () => pending.promise,
    })
  try {
    s.open(row())
    await clock.tick()
    s.configForm.server.host = 'https://example.com'
    const saving = s.save()
    assert.equal(await s.save(), false)
    await clock.tick()
    assert.equal(s.saving.value, true)
    s.configForm.server.host = 'later'
    pending.resolve({ data: { status: 'success' } })
    assert.equal(await saving, true)
    assert.equal(calls.length, 1)
    assert.equal(calls[0][0], 'worker-a')
    assert.equal(calls[0][1].server.host, 'https://example.com')
    assert.equal(s.visible.value, false)
    assert.equal(s.events.filter((e) => e[0] === 'saved').length, 1)
  } finally {
    s.dispose()
    clock.restore()
  }
})
test('save failure retains draft and releases lock for explicit retry', async () => {
  const clock = fakeTimers()
  let fail = true
  const s = drawer({
    ...readApi(),
    putSystemSocketActuatorConfig: async () => ({ data: { request_id: 'save-fixture' } }),
    getSystemSocketActuatorConfigSaveResult: async () => ({
      data: fail ? { status: 'failed', message: 'fixture failed' } : { status: 'success' },
    }),
  })
  try {
    s.open(row())
    await clock.tick()
    s.configForm.server.host = 'draft'
    const first = s.save()
    await clock.tick()
    assert.equal(await first, false)
    assert.equal(s.configForm.server.host, 'draft')
    assert.equal(s.saving.value, false)
    fail = false
    const second = s.save()
    await clock.tick()
    assert.equal(await second, true)
  } finally {
    s.dispose()
    clock.restore()
  }
})
test('closing pending save keeps operation lock until acknowledgement but suppresses stale UI', async () => {
  const clock = fakeTimers(),
    pending = deferred(),
    s = drawer({
      ...readApi(),
      putSystemSocketActuatorConfig: () => pending.promise,
      getSystemSocketActuatorConfigSaveResult: async () => ({ data: { status: 'success' } }),
    })
  try {
    s.open(row())
    await clock.tick()
    const saving = s.save()
    s.exposed.close()
    s.open(row('other'))
    assert.equal(s.visible.value, false)
    assert.equal(s.saving.value, true)
    pending.resolve({ data: { request_id: 'save-fixture' } })
    await clock.tick()
    assert.equal(await saving, false)
    assert.equal(s.saving.value, false)
    assert.deepEqual(s.notices, [])
    s.open(row('other'))
    await clock.tick()
    assert.equal(s.selectedActuator.value.username, 'other')
  } finally {
    s.dispose()
    clock.restore()
  }
})
test('identity change and cache stop clear timers without stale success; reopening reads fresh config', async () => {
  const clock = fakeTimers(),
    pending = deferred(),
    s = drawer({ ...readApi(), putSystemSocketActuatorConfig: () => pending.promise })
  try {
    s.open(row())
    await clock.tick()
    const saving = s.save()
    s.user.roleId = 2
    pending.resolve({ data: { request_id: 'save-fixture' } })
    await flush()
    assert.equal(await saving, false)
    assert.equal(s.visible.value, false)
    assert.equal(s.saving.value, false)
    assert.deepEqual(s.notices, [])
    s.open(row())
    await flush()
    s.lifecycle.deactivate()
    await flush()
    assert.equal(clock.jobs.size, 0)
    s.lifecycle.activate()
    assert.equal(s.visible.value, false)
  } finally {
    s.dispose()
    clock.restore()
  }
})
