import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import * as pinia from 'pinia'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'

const response = (data = []) => ({ code: 200, data, msg: 'ok', totalSize: data.length })
const tree = title => [{ key: 1, title, project_product_id: 10, children: [{ key: 2, title: 'Child', project_product_id: 10 }] }]
function fixture(fetch = async () => response(tree('Module'))) {
  const useUser = pinia.defineStore('module-cache-user', { state: () => ({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }) })
  const root = pinia.createPinia(); pinia.setActivePinia(root)
  const user = useUser(root), requests = []
  const scoped = loadModule('src/utils/scoped-directory-cache.ts', { vue, '@/store/modules/user': { default: useUser } })
  const cache = loadModule('src/api/system/module-directory-cache.ts', { '@/utils/scoped-directory-cache': scoped })
  const api = loadModule('src/api/system/module.ts', {
    './module-directory-cache': cache,
    '@/api/http': Object.fromEntries(['get', 'post', 'put', 'deleted'].map(method => [method, options => {
      const params = typeof options.data === 'function' ? options.data() : options.data
      requests.push({ method, url: options.url, params })
      return fetch(method, options.url, params)
    }])),
  })
  return { root, user, requests, cache, api, useUser, close() { user.$dispose() } }
}

test('module reads merge in flight, cache for five minutes and isolate mutable consumer results', async () => {
  const h = fixture(), pending = deferred()
  let now = 0, count = 0
  const cache = h.cache.createModuleDirectoryCache(() => now)
  const fetch = () => { count++; return count === 1 ? pending.promise : Promise.resolve(response(tree('Fresh'))) }
  try {
    const first = cache.read('tree:10', fetch), second = cache.read('tree:10', fetch)
    await flush(); assert.equal(count, 1)
    pending.resolve(response(tree('Original')))
    const [a, b] = await Promise.all([first, second]); a.data[0].title = 'Mutated'
    assert.equal(b.data[0].title, 'Original')
    now = 299999; assert.equal((await cache.read('tree:10', fetch)).data[0].title, 'Original')
    assert.equal(count, 1)
    now++; await cache.read('tree:10', fetch); assert.equal(count, 2)
    await cache.read('tree:10', fetch, true); assert.equal(count, 3)
  } finally { h.close() }
})

test('module tree/name and product keys are independent; cascading product IDs share the scalar key', async () => {
  const h = fixture()
  try {
    await h.api.getUserModuleTree([1, 10]); await h.api.getUserModuleTree('10')
    await h.api.getUserModuleTree(11); await h.api.getUserModuleName(10)
    assert.equal(h.requests.length, 3)
    assert.equal(h.requests[0].params.project_product_id, 10)
    await h.api.getUserModuleTree(); await h.api.getUserModuleTree(null)
    assert.equal(h.requests.length, 4)
  } finally { h.close() }
})

test('empty successes are cached, while rejected and malformed responses remain retryable', async () => {
  let mode = 'empty'
  const h = fixture(async () => {
    if (mode === 'error') throw Error('offline')
    return mode === 'malformed' ? response([{}]) : response()
  })
  try {
    await h.api.getUserModuleTree(10); await h.api.getUserModuleTree(10)
    assert.equal(h.requests.length, 1)
    mode = 'error'; await assert.rejects(h.api.getUserModuleTree(10, true)); await assert.rejects(h.api.getUserModuleTree(10))
    assert.equal(h.requests.length, 3)
    mode = 'malformed'; await h.api.getUserModuleTree(10); await h.api.getUserModuleTree(10)
    assert.equal(h.requests.length, 5)
  } finally { h.close() }
})

test('identity A-B-A discards earlier caches and late completions cannot evict the current pending read', async () => {
  const pending = [deferred(), deferred(), deferred()]
  let count = 0
  const h = fixture(() => pending[count++]?.promise ?? Promise.resolve(response(tree('Fresh'))))
  try {
    const old = h.api.getUserModuleTree(10); await flush()
    h.user.roleId = 2; const middle = h.api.getUserModuleTree(10); await flush()
    h.user.roleId = 1; const current = h.api.getUserModuleTree(10); await flush()
    pending[0].resolve(response(tree('Old'))); pending[1].resolve(response(tree('Middle')))
    assert.deepEqual((await Promise.allSettled([old, middle])).map(result => result.status), ['rejected', 'rejected'])
    const joined = h.api.getUserModuleTree(10); await flush(); assert.equal(count, 3)
    pending[2].resolve(response(tree('Current'))); await Promise.all([current, joined])
    assert.equal((await h.api.getUserModuleTree(10)).data[0].title, 'Current')
    assert.equal(count, 3)
    for (const key of ['userId', 'token', 'selected_environment']) {
      h.user[key] = key === 'token' ? 'rotated' : 3
      await h.api.getUserModuleTree(10); assert.equal(count, 4 + ['userId', 'token', 'selected_environment'].indexOf(key))
    }
  } finally { h.close() }
})

test('independent Pinia sessions never share module responses, even with the same identity fields', async () => {
  const h = fixture(), otherRoot = pinia.createPinia(), otherUser = h.useUser(otherRoot)
  try {
    pinia.setActivePinia(h.root); await h.api.getUserModuleTree(10)
    pinia.setActivePinia(otherRoot); await h.api.getUserModuleTree(10)
    pinia.setActivePinia(h.root); await h.api.getUserModuleTree(10)
    assert.equal(h.requests.length, 2)
  } finally { otherUser.$dispose(); h.close() }
})

test('successful module writes invalidate both directories; a failed write retains the readable cache', async () => {
  let fail = false
  const h = fixture(async method => { if (method !== 'get' && fail) throw Error('write failed'); return response(tree('Module')) })
  try {
    for (const write of [h.api.postUserModule, h.api.postUserModulePath, h.api.putUserModule, h.api.deleteUserModule]) {
      await h.api.getUserModuleTree(10); await h.api.getUserModuleName(10)
      const before = h.requests.filter(request => request.method === 'get').length
      fail = true; await assert.rejects(write({ id: 1 })); await h.api.getUserModuleTree(10)
      assert.equal(h.requests.filter(request => request.method === 'get').length, before)
      fail = false; await write({ id: 1 }); await h.api.getUserModuleTree(10); await h.api.getUserModuleName(10)
      assert.equal(h.requests.filter(request => request.method === 'get').length, before + 2)
    }
  } finally { h.close() }
})

test('navigation uses the shared module cache expiry without extending its lifetime by another five minutes', async () => {
  const originalNow = Date.now
  let now = 1000
  Date.now = () => now
  const h = fixture()
  let store
  try {
    await h.api.getUserModuleTree()
    now += 240000
    const project = loadModule('src/store/modules/get-project.ts', {
      vue, pinia, './user': { default: h.useUser },
      './project-options': loadModule('src/store/modules/project-options.ts'),
      '@/api/system/project': {}, '@/api/system/module': h.api,
      '@/api/system/module-directory-cache': h.cache,
      '@/utils/load-error': loadFeedbackModule('@/utils/load-error'),
    })
    store = project.useProject(h.root)
    await store.getAllProductModuleTree()
    assert.equal(h.requests.length, 1)
    assert.equal(store.allProductModuleTreeCache.expiresAt, 301000)
    now = 301001; await store.getAllProductModuleTree()
    assert.equal(h.requests.length, 2)
    store.invalidateAllProductModuleTreeCache()
    await h.api.getUserModuleTree(); assert.equal(h.requests.length, 3)
  } finally { store?.$dispose(); h.close(); Date.now = originalNow }
})
