import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

function module(path, modules = {}, timers = {}) {
  const source = readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8')
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  const exports = {}
  new Function('require', 'exports', 'setTimeout', 'clearTimeout', output)(
    (key) => modules[key],
    exports,
    timers.set || setTimeout,
    timers.clear || clearTimeout
  )
  return exports
}
const types = module('store/types.ts')
const preferences = module('utils/interface-preferences.ts', { '@/store/types': types })
const response = (value) => ({
  code: 200,
  data: [
    { key: 'interface', value },
    { key: 'selected_environment', value: null },
  ],
})
const tick = async () => {
  for (let i = 0; i < 5; i++) await vue.nextTick()
}
function deferred() {
  let resolve, reject
  const promise = new Promise((a, b) => {
    resolve = a
    reject = b
  })
  return { promise, resolve, reject }
}

function setup() {
  const user = vue.reactive({ userId: 1, token: 'fixture-session-a' })
  const state = vue.reactive({
    ...preferences.normalizeInterfacePreferences({ sideWidth: 250 }),
    deviceType: 'pc',
    mainHeight: 900,
  })
  const app = {
    $state: state,
    applyInterfacePreferences: (value) =>
      Object.assign(state, preferences.normalizeInterfacePreferences(value)),
  }
  const reads = [],
    writes = [],
    feedback = [],
    timers = new Map()
  let timerId = 0
  const modules = {
    vue,
    pinia: { defineStore: (_name, factory) => factory },
    './user': { default: () => user },
    './app-config': { default: () => app },
    '@/utils/interface-preferences': preferences,
    '@/utils/load-error': { reportLoadError: (...args) => feedback.push(args) },
    '@/api/user/user': {
      getUserConfig: () => {
        const request = deferred()
        reads.push(request)
        return request.promise
      },
      updateUserConfig: (payload) => {
        const request = deferred()
        writes.push({ ...request, value: payload[0].value, payload })
        return request.promise
      },
    },
  }
  const store = module('store/modules/user-preferences.ts', modules, {
    set: (fn, delay) => {
      timers.set(++timerId, { fn, delay })
      return timerId
    },
    clear: (id) => timers.delete(id),
  }).default()
  const stop = store.start()
  const runTimer = () => {
    const entry = [...timers.entries()].at(-1)
    timers.delete(entry[0])
    entry[1].fn()
    return entry[1].delay
  }
  return { store, user, state, reads, writes, feedback, timers, stop, runTimer }
}

test('only safe preferences are persisted, with 200 as the default width', () => {
  const result = preferences.normalizeInterfacePreferences({
    sideWidth: 999,
    token: 'must-not-copy',
    deviceType: 'mobile',
    actionBar: { isShowSearch: false },
  })
  assert.equal(result.sideWidth, 200)
  assert.equal(result.actionBar.isShowSearch, false)
  assert.equal('token' in result, false)
  assert.equal('deviceType' in result, false)
  assert.equal(preferences.readUserInterfacePreferences(response(null)).sideWidth, 200)
  assert.equal(result.autoScale2k, 1.15)
  assert.equal(result.autoScale4k, 1.35)
  assert.equal(
    preferences.normalizeInterfacePreferences({ autoScale2k: 1.5, autoScale4k: 1.2 }).autoScale4k,
    1.5
  )
})

test('server settings replace local settings without automatically writing on restore', async () => {
  const h = setup()
  assert.equal(h.store.loading.value, true)
  h.reads[0].resolve(
    response({ sideWidth: 220, layoutMode: 'ttb', actionBar: { isShowSearch: false } })
  )
  await tick()
  assert.equal(h.state.sideWidth, 220)
  assert.equal(h.state.layoutMode, 'ttb')
  assert.equal(h.state.actionBar.isShowSearch, false)
  assert.equal(h.store.ready.value, true)
  assert.equal(h.writes.length, 0)
  h.state.mainHeight = 800
  await tick()
  assert.equal(h.timers.size, 0)
  h.stop()
})

test('changes debounce for 500ms and writes serialize so newest preferences win', async () => {
  const h = setup()
  h.reads[0].resolve(response({}))
  await tick()
  h.state.sideWidth = 210
  await tick()
  h.state.sideWidth = 220
  await tick()
  assert.equal(h.timers.size, 1)
  assert.equal(h.runTimer(), 500)
  assert.equal(h.writes[0].value.sideWidth, 220)
  h.state.sideWidth = 230
  await tick()
  h.runTimer()
  assert.equal(h.writes.length, 1)
  h.writes[0].resolve({ code: 200 })
  await tick()
  h.runTimer()
  assert.equal(h.writes[1].value.sideWidth, 230)
  h.writes[1].resolve({ code: 200 })
  await tick()
  assert.equal(h.store.dirty.value, false)
  assert.equal(h.store.saving.value, false)
  h.stop()
})

test('density changes save immediately without a debounce, including updates during an active save', async () => {
  const h = setup()
  h.reads[0].resolve(response({ autoScale2k: 1.2, autoScale4k: 1.5 }))
  await tick()
  assert.equal(h.state.autoScale2k, 1.2)
  h.state.autoScale2k = 1.25
  await tick()
  assert.equal(h.writes.length, 1)
  assert.equal(h.writes[0].value.autoScale2k, 1.25)
  assert.equal(h.timers.size, 0)
  h.state.autoScale4k = 1.6
  await tick()
  assert.equal(h.writes.length, 1)
  h.writes[0].resolve({ code: 200 })
  await tick()
  assert.equal(h.writes.length, 2)
  assert.equal(h.writes[1].value.autoScale4k, 1.6)
  assert.equal(h.timers.size, 0)
  h.writes[1].resolve({ code: 200 })
  await tick()
  h.state.displayDensity = 'standard'
  await tick()
  assert.equal(h.writes.length, 3)
  h.writes[2].resolve({ code: 200 })
  await tick()
  h.stop()
})

test('account changes discard pending reads and old save completions', async () => {
  const h = setup()
  h.user.userId = 2
  h.user.token = 'fixture-session-b'
  const latest = h.reads.at(-1)
  h.reads[0].resolve(response({ sideWidth: 260 }))
  await tick()
  assert.equal(h.state.sideWidth, 200)
  latest.resolve(response({ sideWidth: 225 }))
  await tick()
  assert.equal(h.state.sideWidth, 225)
  h.state.sideWidth = 235
  await tick()
  h.runTimer()
  h.user.token = ''
  h.writes[0].resolve({ code: 200 })
  await tick()
  assert.equal(h.store.ready.value, false)
  assert.equal(h.state.sideWidth, 200)
  h.stop()
})

test('load/save failures use shared feedback and remain retryable', async () => {
  const h = setup()
  h.reads[0].reject(new Error('offline'))
  await tick()
  assert.equal(h.store.loading.value, false)
  assert.equal(h.store.ready.value, false)
  assert.equal(h.feedback.length, 1)
  const retry = h.store.retry()
  h.reads[1].resolve(response({}))
  await retry
  h.state.sideWidth = 240
  await tick()
  h.runTimer()
  h.writes[0].reject(new Error('offline'))
  await tick()
  assert.equal(h.store.failed.value, true)
  assert.equal(h.store.saving.value, false)
  assert.equal(h.store.dirty.value, true)
  const saving = h.store.retry()
  h.writes[1].resolve({ code: 200 })
  await saving
  assert.equal(h.store.dirty.value, false)
  h.stop()
})

test('cleared user configuration restores defaults and never immediately repopulates the server value', async () => {
  const h = setup()
  h.reads[0].resolve(response({ sideWidth: 260 }))
  await tick()
  const loading = h.store.reload()
  h.reads[1].resolve(response(null))
  await loading
  assert.equal(h.state.sideWidth, 200)
  assert.equal(h.writes.length, 0)
  h.stop()
})

test('application, settings and login templates compile with preference synchronization', () => {
  for (const path of [
    'App.vue',
    'layouts/setting/index.vue',
    'layouts/Layout.vue',
    'views/login/index.vue',
  ]) {
    const filename = new URL(`../src/${path}`, import.meta.url).pathname
    const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename })
    const script = compileScript(descriptor, { id: 'preferences' })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: 'preferences',
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
})
