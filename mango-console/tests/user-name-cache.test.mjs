import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import * as pinia from 'pinia'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const ok = (data = [{ key: 1, title: 'Example user' }]) => ({ code: 200, data, msg: 'ok', totalSize: data.length })
function fixture(fetch = async () => ok()) {
  const useUser = pinia.defineStore('user-name-cache-user', { state: () => ({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }) })
  const root = pinia.createPinia(); pinia.setActivePinia(root)
  const user = useUser(root), calls = []
  const scoped = loadModule('src/utils/scoped-directory-cache.ts', { vue, '@/store/modules/user': { default: useUser } })
  const names = loadModule('src/api/user/user-name-cache.ts', { '@/utils/scoped-directory-cache': scoped })
  const api = loadModule('src/api/user/user.ts', {
    './user-name-cache': names,
    '@/api/http': Object.fromEntries(['get', 'post', 'put', 'deleted'].map(method => [method, options => {
      calls.push({ method, url: options.url })
      return fetch(method, options.url)
    }])),
  })
  return { user, root, useUser, scoped, api, names, calls, close() { user.$dispose() } }
}

test('user name consumers share requests and five-minute results, including independent copies and forced refresh', async () => {
  const originalNow = Date.now
  let now = 1000
  Date.now = () => now
  const pending = deferred()
  let count = 0
  const h = fixture(() => ++count === 1 ? pending.promise : Promise.resolve(ok()))
  try {
    const first = h.api.getUserName(), second = h.api.getUserName()
    await flush(); assert.equal(count, 1)
    pending.resolve(ok())
    const [a, b] = await Promise.all([first, second])
    a.data[0].title = 'Local edit'; assert.equal(b.data[0].title, 'Example user')
    now += 299999
    assert.equal((await h.api.getUserName()).data[0].title, 'Example user')
    assert.equal(count, 1)
    now++; await h.api.getUserName(); assert.equal(count, 2)
    await h.api.getUserName(true); assert.equal(count, 3)
  } finally { h.close(); Date.now = originalNow }
})

test('successful empty user lists are cached but errors and malformed lists are not', async () => {
  let result = ok([]), fail = false
  const h = fixture(async () => { if (fail) throw Error('offline'); return result })
  try {
    await h.api.getUserName(); await h.api.getUserName(); assert.equal(h.calls.length, 1)
    fail = true; await assert.rejects(h.api.getUserName(true)); await assert.rejects(h.api.getUserName())
    assert.equal(h.calls.length, 3)
    fail = false
    for (const bad of [{ code: 403, data: [] }, { code: 200, data: null }, ok([{ key: null, title: 'Invalid' }])]) {
      result = bad
      const count = h.calls.length
      await h.api.getUserName(); await h.api.getUserName(); assert.equal(h.calls.length, count + 2)
    }
  } finally { h.close() }
})

test('user writes invalidate names only after success, covering register, add, edit and delete', async () => {
  let fail = false
  const h = fixture(async method => { if (method !== 'get' && fail) throw Error('write failed'); return ok() })
  try {
    for (const write of [h.api.registerUser, h.api.postUserInfo, h.api.putUserInfo, h.api.deleteUserInfo]) {
      await h.api.getUserName()
      const count = h.calls.filter(call => call.method === 'get').length
      fail = true; await assert.rejects(write({ id: 1 })); await h.api.getUserName()
      assert.equal(h.calls.filter(call => call.method === 'get').length, count)
      fail = false; await write({ id: 1 }); await h.api.getUserName()
      assert.equal(h.calls.filter(call => call.method === 'get').length, count + 1)
    }
  } finally { h.close() }
})

test('identity changes reject older name responses and cannot warm the new owner cache', async () => {
  const pending = [deferred(), deferred(), deferred()]
  let count = 0
  const h = fixture(() => pending[count++]?.promise ?? Promise.resolve(ok()))
  try {
    const first = h.api.getUserName(); await flush()
    h.user.roleId = 2; const second = h.api.getUserName(); await flush()
    h.user.roleId = 1; const current = h.api.getUserName(); await flush()
    pending[0].resolve(ok()); pending[1].resolve(ok())
    assert.deepEqual((await Promise.allSettled([first, second])).map(r => r.status), ['rejected', 'rejected'])
    const joined = h.api.getUserName(); await flush(); assert.equal(count, 3)
    pending[2].resolve(ok()); await Promise.all([current, joined]); await h.api.getUserName()
    assert.equal(count, 3)
    for (const field of ['userId', 'token', 'selected_environment']) {
      h.user[field] = field === 'token' ? 'rotated' : 2
      await h.api.getUserName()
    }
    assert.equal(count, 6)
  } finally { h.close() }
})

test('user-name cache is independent from module directories and other Pinia sessions', async () => {
  const h = fixture(), otherRoot = pinia.createPinia(), other = h.useUser(otherRoot)
  try {
    pinia.setActivePinia(h.root); await h.api.getUserName()
    const moduleCache = h.scoped.createScopedDirectoryCache(() => true)
    moduleCache.invalidate(); await h.api.getUserName(); assert.equal(h.calls.length, 1)
    pinia.setActivePinia(otherRoot); await h.api.getUserName(); assert.equal(h.calls.length, 2)
    pinia.setActivePinia(h.root); await h.api.getUserName(); assert.equal(h.calls.length, 2)
  } finally { other.$dispose(); h.close() }
})
