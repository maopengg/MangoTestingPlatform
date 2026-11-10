import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import * as vueRouter from 'vue-router'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush as flushVue } from './helpers/case-details-harness.mjs'

const filename = path.resolve('src/views/redirect/default-route.vue')
const source = readFileSync(filename, 'utf8'),
  descriptor = parse(source).descriptor
async function flush() {
  await flushVue()
  await new Promise((resolve) => setImmediate(resolve))
}
function setup({ replace, realRouter } = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const route = realRouter
    ? Object.fromEntries(['path', 'fullPath', 'name', 'query', 'hash'].map((key) => [key, null]))
    : vue.reactive({
        path: '/asset',
        fullPath: '/asset?ids=0&ids=2#part',
        name: 'defaultRouteName',
        query: { ids: ['0', '2'], empty: null },
        hash: '#part',
        matched: ['old'],
        meta: { old: true },
      })
  if (realRouter)
    for (const key of Object.keys(route))
      Object.defineProperty(route, key, { get: () => realRouter.currentRoute.value[key] })
  const calls = [],
    life = { mount: [], unmount: [], activate: [], deactivate: [] }
  let fallback = true
  const router = realRouter ?? {
    hasRoute: () => fallback,
    removeRoute(name) {
      calls.push(['remove', name])
      fallback = false
    },
    replace(target) {
      calls.push(['replace', target])
      return replace
        ? replace(target, route)
        : Promise.resolve().then(() => {
            route.name = 'Actual'
            return undefined
          })
    },
  }
  const oldDocument = globalThis.document,
    doc = Object.assign(new EventTarget(), { hidden: false }),
    listeners = new Set()
  const add = doc.addEventListener.bind(doc),
    remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (type, fn) => {
    listeners.add(fn)
    add(type, fn)
  }
  doc.removeEventListener = (type, fn) => {
    listeners.delete(fn)
    remove(type, fn)
  }
  globalThis.document = doc
  const modules = {
      vue: {
        ...vue,
        onMounted: (fn) => life.mount.push(fn),
        onBeforeUnmount: (fn) => life.unmount.push(fn),
        onActivated: (fn) => life.activate.push(fn),
        onDeactivated: (fn) => life.deactivate.push(fn),
      },
      'vue-router': { ...vueRouter, useRouter: () => router, useRoute: () => route },
      '@/store/modules/user': { default: () => user },
    },
    exports = {}
  new Function(
    'exports',
    'require',
    ts.transpileModule(descriptor.script.content, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
  )(exports, (id) => {
    if (!(id in modules)) { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error('Unexpected dependency ' + id) }
    return modules[id]
  })
  const scope = vue.effectScope(),
    bindings = scope.run(() => exports.default.setup())
  return {
    ...bindings,
    user,
    route,
    calls,
    router,
    listeners,
    mount() {
      life.mount.forEach((fn) => fn())
    },
    pause() {
      life.deactivate.forEach((fn) => fn())
    },
    resume() {
      life.activate.forEach((fn) => fn())
    },
    hide() {
      doc.hidden = true
      doc.dispatchEvent(new Event('visibilitychange'))
    },
    show() {
      doc.hidden = false
      doc.dispatchEvent(new Event('visibilitychange'))
    },
    close() {
      life.unmount.forEach((fn) => fn())
      scope.stop()
      globalThis.document = oldDocument
    },
  }
}

test('temporary matcher is removed once and navigation carries only address fields, with query array/null and hash intact', async () => {
  const h = setup()
  h.mount()
  await flush()
  assert.deepEqual(h.calls, [
    ['remove', 'defaultRouteName'],
    ['replace', { path: '/asset', query: { ids: ['0', '2'], empty: null }, hash: '#part' }],
  ])
  assert.equal(h.failed.value, false)
  h.close()
})

test('same navigation coalesces, has visible loading and rejected Promise exposes retry', async () => {
  const pending = deferred()
  let failure = true
  const h = setup({ replace: () => (failure ? pending.promise : Promise.resolve()) })
  const task = h.redirect()
  assert.equal(h.redirect(), task)
  assert.equal(h.loading.value, true)
  await flush()
  pending.reject(Error('chunk failure'))
  await task
  assert.equal(h.failed.value, true)
  assert.equal(h.loading.value, false)
  failure = false
  await h.redirect()
  assert.equal(h.failed.value, false)
  assert.equal(h.calls.filter((call) => call[0] === 'remove').length, 1)
  h.close()
})

test('navigation snapshots query arrays before asynchronous work and never shares mutable route arrays', async () => {
  const h = setup(),
    task = h.redirect()
  h.route.query.ids.push('later')
  await task
  assert.deepEqual(h.calls.find((call) => call[0] === 'replace')[1].query.ids, ['0', '2'])
  h.close()
})

test('synchronous router failures also release the pending slot and can retry', async () => {
  let fail = true
  const h = setup({
    replace: () => {
      if (fail) throw Error('sync failure')
      return Promise.resolve()
    },
  })
  await h.redirect()
  assert.equal(h.failed.value, true)
  assert.equal(h.loading.value, false)
  fail = false
  await h.redirect()
  assert.equal(h.failed.value, false)
  assert.equal(h.calls.filter((call) => call[0] === 'replace').length, 2)
  h.close()
})

test('mount plus initial KeepAlive activation does not automatically retry an aborted navigation', async () => {
  const h = setup({ replace: () => Promise.reject(Error('failure')) })
  h.mount()
  h.resume()
  await flush()
  assert.equal(h.calls.filter((call) => call[0] === 'replace').length, 1)
  assert.equal(h.failed.value, true)
  h.close()
})

test('leaving before deferred work starts never removes routes or navigates another page', async () => {
  const h = setup()
  h.mount()
  h.route.fullPath = '/elsewhere'
  h.route.name = 'Other'
  await flush()
  assert.deepEqual(h.calls, [])
  h.close()
})

test('route A-B-A before work begins resumes for the original entry only', async () => {
  const h = setup()
  h.mount()
  const old = h.route.fullPath
  h.route.fullPath = '/other'
  h.route.fullPath = old
  await flush()
  assert.equal(h.calls.filter((call) => call[0] === 'replace').length, 1)
  h.close()
})

test('a reused temporary route rematches the latest query/hash instead of staying on an endless spinner', async () => {
  const h = setup()
  h.mount()
  h.route.query = { id: 'updated' }
  h.route.hash = '#latest'
  h.route.fullPath = '/asset?id=updated#latest'
  await flush()
  assert.deepEqual(h.calls.find((call) => call[0] === 'replace')?.[1], {
    path: '/asset',
    query: { id: 'updated' },
    hash: '#latest',
  })
  h.close()
})

test('identity/role/token/environment A-B-A ignores old failure and resolves fresh through the router guard', async () => {
  for (const key of ['userId', 'roleId', 'token', 'selected_environment']) {
    const pending = [deferred(), deferred()]
    let i = 0
    const h = setup({ replace: () => pending[i++].promise })
    h.mount()
    await flush()
    const old = h.user[key]
    h.user[key] = typeof old === 'number' ? old + 1 : old + '-b'
    h.user[key] = old
    pending[0].reject(Error('old'))
    await flush()
    assert.equal(h.failed.value, false)
    assert.equal(h.loading.value, true)
    assert.equal(h.calls.filter((call) => call[0] === 'replace').length, 2)
    h.route.name = 'Actual'
    pending[1].resolve()
    await flush()
    assert.equal(h.failed.value, false)
    h.close()
  }
})

test('background and cached deactivation pause work, returning resumes, and unmount removes listeners', async () => {
  const h = setup({ replace: () => Promise.reject(Error('failure')) })
  h.mount()
  h.hide()
  await flush()
  assert.deepEqual(h.calls, [])
  h.show()
  await flush()
  assert.equal(h.failed.value, true)
  h.pause()
  const count = h.calls.length
  await h.redirect()
  assert.equal(h.calls.length, count)
  h.resume()
  await flush()
  assert.equal(h.calls.filter((call) => call[0] === 'replace').length, 2)
  assert.equal(h.listeners.size, 1)
  h.close()
  assert.equal(h.listeners.size, 0)
})

test('late failure after unmount has no state effect or navigation retry', async () => {
  const pending = deferred(),
    h = setup({ replace: () => pending.promise })
  h.mount()
  await flush()
  h.close()
  pending.reject(Error('late'))
  await flush()
  assert.equal(h.failed.value, false)
  assert.equal(h.calls.filter((call) => call[0] === 'replace').length, 1)
})

async function memoryRouter(path = '/asset') {
  const router = vueRouter.createRouter({
    history: vueRouter.createMemoryHistory(),
    routes: [
      { path, name: 'defaultRouteName', component: {} },
      { path: '/404', name: '404', component: {} },
      { path: '/403', name: '403', component: {} },
    ],
  })
  await router.push(path + '?id=0&id=2#section')
  await router.isReady()
  return router
}

test('real Vue Router rematches a newly registered dynamic page and preserves deep-link query/hash', async () => {
  const router = await memoryRouter()
  router.addRoute({
    path: '/asset',
    name: 'Actual',
    component: {},
    meta: { permissionKey: 'fixture.read' },
  })
  const h = setup({ realRouter: router })
  await h.redirect()
  assert.equal(router.hasRoute('defaultRouteName'), false)
  assert.equal(router.currentRoute.value.name, 'Actual')
  assert.deepEqual(router.currentRoute.value.query.id, ['0', '2'])
  assert.equal(router.currentRoute.value.hash, '#section')
  assert.equal(router.currentRoute.value.meta.permissionKey, 'fixture.read')
  h.close()
})

test('real router keeps global not-found and access-denied redirects effective', async () => {
  for (const denied of [false, true]) {
    const router = await memoryRouter()
    if (denied) {
      router.addRoute({
        path: '/asset',
        name: 'Actual',
        component: {},
        meta: { permissionKey: 'fixture' },
      })
      router.beforeEach((to) => (to.meta.permissionKey ? '/403' : true))
    } else router.addRoute({ path: '/:pathMatch(.*)*', redirect: '/404' })
    const h = setup({ realRouter: router })
    await h.redirect()
    assert.equal(router.currentRoute.value.path, denied ? '/403' : '/404')
    assert.equal(h.failed.value, false)
    h.close()
  }
})

test('real aborted and rejected navigation stop loading and remain retryable', async () => {
  for (const rejected of [false, true]) {
    const router = await memoryRouter()
    router.addRoute({ path: '/asset', name: 'Actual', component: {} })
    let block = true
    router.onError(() => {})
    router.beforeEach(() => {
      if (!block) return true
      if (rejected) throw Error('fixture failure')
      return false
    })
    const h = setup({ realRouter: router })
    await h.redirect()
    assert.equal(h.failed.value, true)
    assert.equal(h.loading.value, false)
    block = false
    await h.redirect()
    assert.equal(router.currentRoute.value.name, 'Actual')
    h.close()
  }
})

test('real router cancellation by newer navigation never pulls the user back to the original entry', async () => {
  const router = await memoryRouter()
  router.addRoute({ path: '/asset', name: 'Actual', component: {} })
  router.addRoute({ path: '/other', name: 'Other', component: {} })
  const pending = deferred()
  router.beforeEach((to) => (to.name === 'Actual' ? pending.promise : true))
  const h = setup({ realRouter: router }),
    task = h.redirect()
  await flush()
  await router.push('/other')
  pending.resolve(true)
  await task
  assert.equal(router.currentRoute.value.name, 'Other')
  assert.equal(h.failed.value, false)
  h.close()
})

test('Options API SFC and template compile, retaining a single technical component without empty configuration', () => {
  assert.equal(compileScript(descriptor, { id: 'default-route' }).lang, 'ts')
  assert.deepEqual(
    compileTemplate({ id: 'default-route', filename, source: descriptor.template.content }).errors,
    []
  )
})
