import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

function load(filename, dependencies = {}) {
  const exports = {}
  const source = ts.transpileModule(readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  new Function('exports', 'require', source)(exports, (key) => dependencies[key] || {})
  return exports
}

test('configuration adapters use one route, flat updates and optional exact-key reads', async () => {
  const calls = []
  const record = (method) => async (options) => {
    calls.push({ method, url: options.url, data: options.data() })
    return { code: 200 }
  }
  const api = load('src/api/user/user.ts', {
    '@/api/http': { get: record('GET'), put: record('PUT'), deleted: record('DELETE') },
  })
  await api.getUserConfig()
  await api.getUserConfig('interface')
  await api.updateUserConfig([{ key: 'selected_environment', value: 0 }])
  await api.clearUserConfig({ key: 'interface' })
  assert.deepEqual(calls, [
    { method: 'GET', url: '/user/info/config', data: {} },
    { method: 'GET', url: '/user/info/config', data: { key: 'interface' } },
    { method: 'PUT', url: '/user/info/config', data: [{ key: 'selected_environment', value: 0 }] },
    { method: 'DELETE', url: '/user/info/config', data: { key: 'interface' } },
  ])
  assert.equal(api.putUserEnvironment, undefined)
})

function environmentSetup(write) {
  const user = vue.reactive({
    userId: 4,
    token: 'fixture-user',
    selected_environment: 1,
    selected_environment_title: '',
  })
  const calls = []
  const types = load('src/store/types.ts')
  const h = harness('testing-environment', 'handleSelect,switching', {
    filename: path.resolve('src/layouts/avatar/testing-environment.vue'),
    modules: {
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': {
        useEnum: () => ({
          environment_type: [
            { key: 0, title: '开发环境' },
            { key: 1, title: '预发环境' },
          ],
        }),
      },
      '@/store/types': types,
      '@/api/user/user': {
        updateUserConfig: (payload) => {
          calls.push(payload)
          return write(payload)
        },
      },
    },
  })
  return { ...h, user, calls }
}

test('environment selection submits a flat key/value and only changes state after successful response', async () => {
  const pending = deferred(),
    h = environmentSetup(() => pending.promise)
  const saving = h.handleSelect(0)
  await h.handleSelect(0)
  assert.equal(h.calls.length, 1)
  assert.deepEqual(h.calls[0], [{ key: 'selected_environment', value: 0 }])
  assert.equal(h.user.selected_environment, 1)
  pending.resolve({ code: 200, msg: 'saved', data: [{ key: 'selected_environment', value: 0 }] })
  await saving
  assert.equal(h.user.selected_environment, 0)
  assert.equal(h.user.selected_environment_title, '开发环境')
  assert.equal(h.switching.value, false)
  h.close()
})

test('late environment responses cannot change another account or leave a stuck loading state', async () => {
  const pending = deferred(),
    h = environmentSetup(() => pending.promise)
  const saving = h.handleSelect(0)
  h.user.userId = 8
  h.user.token = 'fixture-other'
  await flush()
  pending.resolve({ code: 200, data: [{ key: 'selected_environment', value: 0 }] })
  await saving
  assert.equal(h.user.selected_environment, 1)
  assert.equal(h.switching.value, false)
  h.close()
})
