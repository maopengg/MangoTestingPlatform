import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/gray/config-file')
const yaml = () => ({ kind: 'yaml', id: 11, ownerId: 2, label: 'Example config' })
const binding = () => ({ kind: 'binding', id: 21, ownerId: 11, label: 'config/example.yml' })
function writes(api = {}, applied = async () => true) {
  const hooks = { deactivate: [], activate: [], unmount: [] },
    dialogs = [],
    messages = [],
    calls = []
  const defaults = {
    putGrayYamlFile: async (p) => {
      calls.push(['yaml-status', p])
      return { code: 200, data: { ...p, project_product: 2 } }
    },
    putGrayYamlFileBinding: async (p) => {
      calls.push(['binding-status', p])
      return { code: 200, data: { ...p, yaml_file: 11 } }
    },
    deleteGrayYamlFile: async (id) => {
      calls.push(['yaml-delete', id])
      return { code: 200 }
    },
    deleteGrayYamlFileBinding: async (id) => {
      calls.push(['binding-delete', id])
      return { code: 200 }
    },
  }
  const f = harness('YamlContentDrawer', '', {
    base,
    api: { ...defaults, ...api },
    modules: {
      vue: {
        ...vue,
        onDeactivated: (fn) => hooks.deactivate.push(fn),
        onActivated: (fn) => hooks.activate.push(fn),
        onBeforeUnmount: (fn) => hooks.unmount.push(fn),
      },
      '@arco-design/web-vue': {
        Message: {
          success: (m) => messages.push(['success', m]),
          error: (m) => messages.push(['error', m]),
        },
        Modal: {
          confirm(options) {
            const dialog = {
              options,
              closed: false,
              close() {
                this.closed = true
                options.onClose?.()
              },
            }
            dialogs.push(dialog)
            return dialog
          },
        },
      },
    },
  })
  const scope = vue.effectScope(),
    context = vue.ref('one'),
    blocked = vue.ref(false),
    appliedCalls = []
  const { useYamlMutations } = f.load('composables/useYamlMutations.ts')
  const result = scope.run(() =>
    useYamlMutations({
      contextKey: () => context.value,
      blocked: () => blocked.value,
      applied: async (...args) => {
        appliedCalls.push(args)
        return applied(...args)
      },
    })
  )
  return {
    ...result,
    context,
    blocked,
    dialogs,
    messages,
    calls,
    appliedCalls,
    hooks,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      scope.stop()
      f.close()
    },
  }
}

for (const [kind, factory, putApi, deleteApi, ownerKey] of [
  ['yaml', yaml, 'putGrayYamlFile', 'deleteGrayYamlFile', 'project_product'],
  ['binding', binding, 'putGrayYamlFileBinding', 'deleteGrayYamlFileBinding', 'yaml_file'],
]) {
  for (const checked of [true, false])
    test(`${kind} status preserves controlled-switch semantics and white-listed payload ${checked}`, async () => {
      const w = writes(),
        target = factory()
      assert.equal(await w.changeStatus(target, checked), false)
      assert.deepEqual(w.calls, [[`${kind}-status`, { id: target.id, status: checked ? 1 : 0 }]])
      assert.deepEqual(w.appliedCalls, [[target, checked ? 1 : 0]])
      assert.equal(w.pending.value, null)
      w.cleanup()
    })
  test(`${kind} status physical lock freezes the target and blocks concurrent status or delete`, async () => {
    const pending = deferred(),
      target = factory(),
      calls = []
    const w = writes({
      [putApi]: (p) => {
        calls.push(p)
        return pending.promise
      },
    })
    const work = w.changeStatus(target, true)
    target.id = 99
    target.ownerId = 88
    await w.changeStatus(factory(), false)
    w.confirmDelete(factory())
    assert.equal(calls.length, 1)
    assert.equal(w.dialogs.length, 0)
    assert.equal(w.pending.value.id, factory().id)
    pending.resolve({
      code: 200,
      data: { id: factory().id, status: 1, [ownerKey]: factory().ownerId },
    })
    await work
    assert.deepEqual(w.appliedCalls, [[factory(), 1]])
    w.cleanup()
  })
  for (const [field, value] of [
    ['id', 99],
    ['status', 7],
    [ownerKey, 99],
  ])
    test(`${kind} status rejects wrong ${field} acknowledgment`, async () => {
      const target = factory()
      const w = writes({
        [putApi]: async (p) => ({
          code: 200,
          data: { ...p, [ownerKey]: target.ownerId, [field]: value },
        }),
      })
      await w.changeStatus(target, true)
      assert.equal(w.appliedCalls.length, 0)
      assert.equal(w.pending.value, null)
      assert.equal(w.messages[0][0], 'error')
      w.cleanup()
    })
  test(`${kind} failed status unlocks for retry`, async () => {
    let calls = 0
    const target = factory(),
      w = writes({
        [putApi]: async (p) => {
          if (++calls === 1) throw Error('Network')
          return { code: 200, data: { ...p, [ownerKey]: target.ownerId } }
        },
      })
    await w.changeStatus(target, true)
    assert.equal(w.pending.value, null)
    await w.changeStatus(target, true)
    assert.equal(w.appliedCalls.length, 1)
    w.cleanup()
  })
  test(`${kind} delete fixes ID before confirmation and explicitly closes after success without invented count fields`, async () => {
    const target = factory(),
      expected = factory(),
      w = writes()
    w.confirmDelete(target)
    target.id = 99
    target.ownerId = 88
    w.confirmDelete(factory())
    assert.equal(w.dialogs.length, 1)
    assert.equal(w.confirming.value, true)
    assert.equal(await w.dialogs[0].options.onBeforeOk(), false)
    assert.deepEqual(w.calls, [[`${kind}-delete`, expected.id]])
    assert.deepEqual(w.appliedCalls, [[expected]])
    assert.equal(w.dialogs[0].closed, true)
    assert.equal(w.confirming.value, false)
    assert.equal(w.pending.value, null)
    w.cleanup()
  })
  test(`${kind} delete guards duplicate confirmation, cancel and other writes until actual request settles`, async () => {
    const pending = deferred(),
      calls = []
    const w = writes({
      [deleteApi]: (id) => {
        calls.push(id)
        return pending.promise
      },
    })
    w.confirmDelete(factory())
    const dialog = w.dialogs[0],
      work = dialog.options.onBeforeOk()
    await dialog.options.onBeforeOk()
    await w.changeStatus(factory(), true)
    assert.equal(dialog.options.onBeforeCancel(), false)
    assert.equal(calls.length, 1)
    assert.deepEqual(w.calls, [])
    pending.resolve({ code: 200 })
    await work
    assert.equal(dialog.closed, true)
    w.cleanup()
  })
  test(`${kind} delete failure retains its confirmation for a successful retry`, async () => {
    let calls = 0
    const w = writes({
      [deleteApi]: async () => {
        if (++calls === 1) throw Error('Network')
        return { code: 200 }
      },
    })
    w.confirmDelete(factory())
    const dialog = w.dialogs[0]
    await dialog.options.onBeforeOk()
    assert.equal(dialog.closed, false)
    assert.equal(w.pending.value, null)
    assert.equal(w.confirming.value, true)
    await dialog.options.onBeforeOk()
    assert.equal(dialog.closed, true)
    assert.equal(w.appliedCalls.length, 1)
    w.cleanup()
  })
  test(`${kind} negative delete acknowledgment does not close or report success`, async () => {
    const w = writes({ [deleteApi]: async () => ({ code: 400 }) })
    w.confirmDelete(factory())
    await w.dialogs[0].options.onBeforeOk()
    assert.equal(w.dialogs[0].closed, false)
    assert.equal(w.appliedCalls.length, 0)
    assert.equal(
      w.messages.some(([type]) => type === 'success'),
      false
    )
    w.cleanup()
  })
  for (const action of ['status', 'delete'])
    test(`${kind} ${action} stale completion is isolated and physical lock survives A-B-A context`, async () => {
      const pending = deferred(),
        w = writes({ [action === 'status' ? putApi : deleteApi]: () => pending.promise })
      let work
      if (action === 'status') work = w.changeStatus(factory(), true)
      else {
        w.confirmDelete(factory())
        work = w.dialogs[0].options.onBeforeOk()
      }
      w.context.value = 'two'
      w.context.value = 'one'
      assert.ok(w.pending.value)
      await w.changeStatus(factory(), false)
      w.confirmDelete(factory())
      assert.equal(w.dialogs.length, action === 'delete' ? 1 : 0)
      pending.resolve({
        code: 200,
        data: { id: factory().id, status: 1, [ownerKey]: factory().ownerId },
      })
      await work
      assert.equal(w.appliedCalls.length, 0)
      assert.equal(w.messages.length, 0)
      assert.equal(w.pending.value, null)
      w.cleanup()
    })
  for (const action of ['status', 'delete'])
    test(`${kind} ${action} keeps success distinct from refresh failure`, async () => {
      const w = writes({}, async () => false)
      if (action === 'status') await w.changeStatus(factory(), true)
      else {
        w.confirmDelete(factory())
        await w.dialogs[0].options.onBeforeOk()
        assert.equal(w.dialogs[0].closed, true)
      }
      assert.equal(w.messages[0][0], 'success')
      assert.match(w.messages[1][1], /列表读取失败/)
      assert.equal(w.pending.value, null)
      w.cleanup()
    })
}

test('changing context closes an idle confirmation and its old callback becomes inert', async () => {
  const w = writes()
  w.confirmDelete(yaml())
  const dialog = w.dialogs[0]
  w.context.value = 'next'
  assert.equal(dialog.closed, true)
  assert.equal(w.confirming.value, false)
  await dialog.options.onBeforeOk()
  assert.deepEqual(w.calls, [])
  w.cleanup()
})
test('external editor/saving guard blocks writes including an already-open confirmation', async () => {
  const w = writes()
  w.blocked.value = true
  await w.changeStatus(yaml(), true)
  w.confirmDelete(yaml())
  assert.equal(w.dialogs.length, 0)
  w.blocked.value = false
  w.confirmDelete(yaml())
  w.blocked.value = true
  await w.dialogs[0].options.onBeforeOk()
  assert.deepEqual(w.calls, [])
  w.cleanup()
})
for (const hook of ['deactivate', 'unmount'])
  test(`${hook} discards late status while actual request lock survives and activation resumes`, async () => {
    const pending = deferred()
    let calls = 0
    const w = writes({
      putGrayYamlFile: async (p) => {
        if (++calls === 1) return pending.promise
        return { code: 200, data: { ...p, project_product: 2 } }
      },
    })
    const work = w.changeStatus(yaml(), true)
    w.hooks[hook].forEach((fn) => fn())
    w.hooks.activate.forEach((fn) => fn())
    await w.changeStatus(yaml(), false)
    assert.equal(calls, 1)
    pending.resolve({ code: 200, data: { id: 11, status: 1, project_product: 2 } })
    await work
    assert.equal(w.appliedCalls.length, 0)
    if (hook === 'deactivate') {
      await w.changeStatus(yaml(), false)
      assert.equal(calls, 2)
      assert.deepEqual(w.appliedCalls, [[yaml(), 0]])
    }
    w.cleanup()
  })
test('invalid identity cannot issue a mutation', async () => {
  const w = writes()
  await w.changeStatus({ ...yaml(), id: 0 }, true)
  w.confirmDelete({ ...yaml(), ownerId: 0 })
  assert.deepEqual(w.calls, [])
  assert.equal(w.dialogs.length, 0)
  w.cleanup()
})
