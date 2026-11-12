import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const success = (data) => ({ code: 200, data })
const item = (key = 'selected_environment', extra = {}) => ({
  key,
  name: key,
  value: 0,
  value_type: 'environment',
  description: '',
  clearable: true,
  updated_at: null,
  ...extra,
})
function setup(api = {}) {
  const hooks = { mounted: [], activated: [], deactivated: [], unmounted: [] }
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-one', selected_environment: 0 })
  const route = vue.reactive({ path: '/personal/info' })
  const confirmations = [],
    writes = [],
    messages = []
  let preferencesReloaded = 0
  const preferences = vue.reactive({ saving: false, dirty: false,
    reload: async () => { preferencesReloaded++ } })
  const documentBefore = globalThis.document
  globalThis.document = Object.assign(new EventTarget(), { hidden: false })
  const h = harness(
    'UserConfigPanel',
    'items,loading,failed,clearingKey,loadData,confirmClear,configActions',
    {
      base: path.resolve('src/views/personal'),
      modules: {
        vue: {
          ...vue,
          onMounted: (fn) => hooks.mounted.push(fn),
          onActivated: (fn) => hooks.activated.push(fn),
          onDeactivated: (fn) => hooks.deactivated.push(fn),
          onBeforeUnmount: (fn) => hooks.unmounted.push(fn),
        },
        'vue-router': { useRoute: () => route },
        '@/store/modules/user': { default: () => user },
        '@/store/modules/user-preferences': {
          default: () => preferences,
        },
        '@/store/modules/get-enum': {
          useEnum: () => ({ environment_type: [{ key: 0, title: '开发环境' }] }),
        },
        '@/api/user/user': {
          getUserConfig: () => (api.read ? api.read() : Promise.resolve(success([item()]))),
          clearUserConfig: (data) => {
            writes.push(data)
            return api.write ? api.write(data) : Promise.resolve(success({ count: 1 }))
          },
        },
        '@arco-design/web-vue': {
          Message: { success: (value) => messages.push(value) },
          Modal: {
            confirm: (options) => {
              const modal = { options, close() {} }
              confirmations.push(modal)
              return modal
            },
          },
        },
      },
    }
  )
  hooks.mounted.forEach((fn) => fn())
  return {
    ...h,
    user,
    preferences,
    confirmations,
    writes,
    messages,
    reloads: () => preferencesReloaded,
    destroy() {
      hooks.unmounted.forEach((fn) => fn())
      h.close()
      globalThis.document = documentBefore
    },
  }
}

test('personal configuration parses a flat list and preserves false/zero/null values', async () => {
  const h = setup({
    read: async () =>
      success([
        item(),
        item('flag', { value: false, value_type: 'boolean' }),
        item('empty', { value: null }),
      ]),
  })
  await flush()
  assert.equal(h.items.value[0].value, 0)
  assert.equal(h.items.value[1].value, false)
  assert.equal(h.configActions(h.items.value[1])[0].disabled, false)
  assert.equal(h.configActions(h.items.value[2])[0].disabled, false)
  h.destroy()
})

test('clearing remains available for unset and previously non-clearable records', async () => {
  const h = setup({
    read: async () => success([item('custom.setting', { value: null, clearable: false })]),
    write: async () => success({ count: 0 }),
  })
  await flush()
  const row = h.items.value[0]
  assert.equal(h.configActions(row)[0].disabled, false)
  h.confirmClear(row)
  assert.equal(h.confirmations.length, 1)
  assert.equal(await h.confirmations[0].options.onBeforeOk(), true)
  assert.deepEqual(h.writes, [{ key: 'custom.setting' }])
  h.destroy()
})

test('clearing one record sends key only and synchronizes the selected environment', async () => {
  const h = setup()
  await flush()
  h.confirmClear(h.items.value[0])
  await h.confirmations[0].options.onBeforeOk()
  assert.deepEqual(h.writes, [{ key: 'selected_environment' }])
  assert.equal(h.user.selected_environment, null)
  h.destroy()
})

test('clearing interface configuration reloads preferences without changing environment', async () => {
  const h = setup({
    read: async () =>
      success([item('interface', { value: { sideWidth: 220 }, value_type: 'json' })]),
  })
  await flush()
  h.confirmClear(h.items.value[0])
  await h.confirmations[0].options.onBeforeOk()
  assert.equal(h.reloads(), 1)
  assert.equal(h.user.selected_environment, 0)
  h.destroy()
})

test('late read/clear responses cannot change another logged-in user', async () => {
  const pending = deferred(),
    h = setup({ write: () => pending.promise })
  await flush()
  h.confirmClear(h.items.value[0])
  const saving = h.confirmations[0].options.onBeforeOk()
  h.user.userId = 2
  h.user.token = 'fixture-two'
  await flush()
  pending.resolve(success({ count: 1 }))
  assert.equal(await saving, false)
  assert.equal(h.user.selected_environment, 0)
  assert.equal(h.messages.length, 0)
  h.destroy()
})

test('clearing interface waits until automatic writes settle to avoid repopulating cleared values', async () => {
  const h = setup({ read: async () => success([item('interface', { value_type: 'json', value: {} })]) })
  await flush()
  const row = h.items.value[0]
  h.preferences.saving = true
  h.confirmClear(row)
  assert.equal(h.confirmations.length, 0)
  assert.equal(h.configActions(row)[0].disabled, true)
  h.preferences.saving = false
  h.preferences.dirty = true
  h.confirmClear(row)
  assert.equal(h.confirmations.length, 0)
  h.preferences.dirty = false
  h.confirmClear(row)
  assert.equal(h.confirmations.length, 1)
  h.destroy()
})

test('failed requests remain retryable and malformed flat records fail validation', async () => {
  let fail = true
  const h = setup({
    read: async () => {
      if (fail) throw Error('offline')
      return success([])
    },
  })
  await flush()
  assert.equal(h.failed.value, true)
  assert.equal(h.loading.value, false)
  fail = false
  await h.loadData()
  assert.equal(h.failed.value, false)
  assert.equal(h.items.value.length, 0)
  for (const data of [null, [item(), item()], [item('bad', { value_type: 'unknown' })]]) {
    assert.throws(() => h.boundary.readUserConfigItems(success(data)))
  }
  h.destroy()
})
