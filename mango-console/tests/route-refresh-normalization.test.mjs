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

const pageFile = path.resolve('src/views/redirect/index.vue'),
  headerFile = path.resolve('src/layouts/actions/index.vue'),
  hookFile = path.resolve('src/hooks/use-route-refresh.ts')
async function flush() {
  await flushVue()
  await new Promise((resolve) => setImmediate(resolve))
}
function setup(kind = 'page', { replace, realRouter } = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 }),
    matched = [{ path: '/redirect/:path(.*)*' }]
  const route = realRouter
    ? {}
    : vue.reactive({
        path: kind === 'page' ? '/redirect/detail/a%2Fb' : '/detail/a%2Fb',
        fullPath: kind === 'page' ? '/redirect/detail/a%2Fb?id=0#part' : '/detail/a%2Fb?id=0#part',
        params: { path: ['detail', 'a/b'] },
        query: { id: ['0', '2'], empty: null },
        hash: '#part',
        matched,
      })
  if (realRouter)
    for (const key of ['path', 'fullPath', 'params', 'query', 'hash', 'matched'])
      Object.defineProperty(route, key, { get: () => realRouter.currentRoute.value[key] })
  const calls = [],
    messages = [],
    life = { mount: [], unmount: [], activate: [], deactivate: [] },
    timers = new Map()
  let timerId = 0
  const router = realRouter ?? {
    replace: (target) => {
      calls.push(target)
      return replace ? replace(target, route) : Promise.resolve()
    },
  }
  const oldDocument = globalThis.document,
    oldSet = globalThis.setTimeout,
    oldClear = globalThis.clearTimeout
  const doc = Object.assign(new EventTarget(), { hidden: false, visibilityState: 'visible' }),
    listeners = new Set(),
    add = doc.addEventListener.bind(doc),
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
  globalThis.setTimeout = (callback, delay) => {
    const id = ++timerId
    timers.set(id, { callback, delay })
    return id
  }
  globalThis.clearTimeout = (id) => timers.delete(id)
  const modules = {
    vue: {
      ...vue,
      onMounted: (fn) => life.mount.push(fn),
      onBeforeUnmount: (fn) => life.unmount.push(fn),
      onActivated: (fn) => life.activate.push(fn),
      onDeactivated: (fn) => life.deactivate.push(fn),
    },
    'vue-router': { ...vueRouter, useRoute: () => route, useRouter: () => router },
    '@/store/modules/user': { default: () => user },
    '@arco-design/web-vue': {
      Message: { error: (value) => messages.push(value) },
      Notification: { warning() {} },
    },
    '@arco-design/web-vue/es/icon': {},
    '@vueuse/core': {
      useFullscreen: () => ({
        isSupported: false,
        enter() {},
        exit() {},
        isFullscreen: vue.ref(false),
      }),
    },
    '@/hooks/useEmit': { default: () => ({ emit() {} }) },
    '@/store/modules/app-config': { default: () => ({ actionBar: {} }) },
    '@/store/modules/notification-message': {
      useNotificationMessage: () => ({ setTodoPendingCount() {} }),
    },
    '@/api/system': { getSystemWorkbenchTodos: async () => ({ data: {} }) },
    '@/components/feedback/NotificationCenter.vue': {},
  }
  function load(file, sfc = false) {
    const raw = readFileSync(file, 'utf8'),
      source = sfc ? parse(raw).descriptor.script.content : raw,
      exports = {}
    new Function(
      'exports',
      'require',
      ts.transpileModule(source, {
        compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
      }).outputText
    )(exports, (id) => {
      if (!(id in modules)) { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error('Unexpected dependency ' + id) }
      return modules[id]
    })
    return exports
  }
  modules['@/hooks/use-route-refresh'] = load(hookFile)
  const scope = vue.effectScope(),
    bindings = scope.run(() =>
      kind === 'page'
        ? load(pageFile, true).default.setup()
        : kind === 'header'
        ? load(headerFile, true).default.setup()
        : modules['@/hooks/use-route-refresh'].useRouteRefresh()
    )
  return {
    ...bindings,
    user,
    route,
    calls,
    messages,
    timers,
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
      doc.visibilityState = 'hidden'
      doc.dispatchEvent(new Event('visibilitychange'))
    },
    show() {
      doc.hidden = false
      doc.visibilityState = 'visible'
      doc.dispatchEvent(new Event('visibilitychange'))
    },
    async tick() {
      const tasks = [...timers.values()]
      timers.clear()
      for (const task of tasks) task.callback()
      await flush()
    },
    close() {
      life.unmount.forEach((fn) => fn())
      scope.stop()
      globalThis.document = oldDocument
      globalThis.setTimeout = oldSet
      globalThis.clearTimeout = oldClear
    },
  }
}

test('page restores encoded URL instead of decoded string/array params and preserves independent query/hash', async () => {
  for (const param of ['detail/a/b', ['detail', 'a/b'], undefined]) {
    const h = setup()
    h.route.params.path = param
    const task = h.redirect()
    h.route.query.id.push('later')
    await task
    assert.deepEqual(h.calls, [
      { path: '/detail/a%2Fb', query: { id: ['0', '2'], empty: null }, hash: '#part' },
    ])
    h.close()
  }
})

test('page coalesces pending navigation, releases synchronous/rejected failures and permits retry', async () => {
  for (const sync of [false, true]) {
    let fail = true
    const h = setup('page', {
      replace: () => {
        if (fail) {
          if (sync) throw Error('fixture')
          return Promise.reject(Error('fixture'))
        }
        return Promise.resolve()
      },
    })
    const task = h.redirect()
    assert.equal(h.redirect(), task)
    await task
    assert.equal(h.failed.value, true)
    assert.equal(h.loading.value, false)
    fail = false
    await h.redirect()
    assert.equal(h.failed.value, false)
    h.close()
  }
})

test('reused refresh page follows current route/query and ignores stale completion and finalizers', async () => {
  const pending = [deferred(), deferred()]
  let i = 0
  const h = setup('page', { replace: () => pending[i++].promise })
  h.mount()
  await flush()
  h.route.path = '/redirect/other'
  h.route.query = { id: 'new' }
  h.route.fullPath = '/redirect/other?id=new'
  pending[0].reject(Error('old'))
  await flush()
  assert.equal(h.failed.value, false)
  assert.equal(h.loading.value, true)
  assert.equal(h.calls[1].path, '/other')
  pending[1].resolve()
  await flush()
  h.close()
})

test('another real page even under redirect prefix cannot be captured by old component before it unmounts', async () => {
  const h = setup()
  h.mount()
  h.route.path = '/redirect/other-page'
  h.route.matched = [{ path: '/redirect/other-page' }]
  h.route.fullPath = '/redirect/other-page'
  await flush()
  assert.deepEqual(h.calls, [])
  h.close()
})

test('refresh page lifecycle pauses and resumes without an extra retry on first activation', async () => {
  const h = setup('page', { replace: () => Promise.reject(Error('failure')) })
  h.mount()
  h.resume()
  await flush()
  assert.equal(h.calls.length, 1)
  h.hide()
  const count = h.calls.length
  await h.redirect()
  assert.equal(h.calls.length, count)
  h.show()
  await flush()
  assert.equal(h.calls.length, 2)
  h.pause()
  await h.redirect()
  assert.equal(h.calls.length, 2)
  h.resume()
  await flush()
  assert.equal(h.calls.length, 3)
  h.close()
  assert.equal(h.listeners.size, 0)
})

test('queued toolbar refresh is trailing-debounced 200ms, coalesces, snapshots encoded address/query/hash', async () => {
  const h = setup('hook'),
    first = h.refresh()
  assert.equal(h.loading.value, true)
  assert.equal(h.refresh(), first)
  assert.equal(h.timers.size, 1)
  assert.equal([...h.timers.values()][0].delay, 200)
  h.route.query.id.push('later')
  await h.tick()
  await first
  assert.deepEqual(h.calls, [
    { path: '/redirect/detail/a%2Fb', query: { id: ['0', '2'], empty: null }, hash: '#part' },
  ])
  assert.equal(h.loading.value, false)
  h.close()
})

test('toolbar navigation is physically locked until settlement and failed navigation can retry', async () => {
  const pending = deferred()
  let fail = true
  const h = setup('hook', { replace: () => (fail ? pending.promise : Promise.resolve()) }),
    task = h.refresh()
  await h.tick()
  assert.equal(h.refresh(), task)
  assert.equal(h.timers.size, 0)
  assert.equal(h.calls.length, 1)
  pending.reject(Error('failure'))
  await task
  assert.equal(h.loading.value, false)
  assert.equal(h.messages.length, 1)
  fail = false
  const retry = h.refresh()
  await h.tick()
  await retry
  assert.equal(h.calls.length, 2)
  h.close()
})

test('toolbar cancels queued route/identity/environment A-B-A without refreshing the newly entered page', async () => {
  for (const key of ['fullPath', 'userId', 'roleId', 'token', 'selected_environment']) {
    const h = setup('hook'),
      task = h.refresh(),
      target = key === 'fullPath' ? h.route : h.user,
      old = target[key]
    target[key] = typeof old === 'number' ? old + 1 : old + '-b'
    target[key] = old
    await task
    await h.tick()
    assert.deepEqual(h.calls, [])
    assert.equal(h.loading.value, false)
    h.close()
  }
})

test('toolbar retains physical lock across context changes but suppresses stale failure notifications', async () => {
  const pending = deferred(),
    h = setup('hook', { replace: () => pending.promise }),
    task = h.refresh()
  await h.tick()
  h.route.fullPath = '/other'
  assert.equal(h.loading.value, true)
  assert.equal(h.refresh(), task)
  pending.reject(Error('old'))
  await task
  assert.equal(h.loading.value, false)
  assert.deepEqual(h.messages, [])
  h.close()
})

test('toolbar never stacks redirects and cancels delayed work on background, deactivation and unmount', async () => {
  for (const stop of ['hide', 'pause', 'close']) {
    const h = setup('hook')
    h.mount()
    const task = h.refresh()
    h[stop]()
    await task
    await h.tick()
    assert.deepEqual(h.calls, [])
    if (stop !== 'close') h.close()
    assert.equal(h.listeners.size, 0)
  }
  const h = setup('hook')
  h.route.path = '/redirect/asset'
  await h.refresh()
  assert.equal(h.timers.size, 0)
  h.close()
})

test('actual toolbar wires the shared refresh flow, loading and hash without running unrelated todo polling', async () => {
  const h = setup('header'),
    task = h.onRefrehRoute()
  assert.equal(h.refreshLoading.value, true)
  await h.tick()
  await task
  assert.equal(h.calls[0].hash, '#part')
  assert.equal(h.refreshLoading.value, false)
  h.close()
})

test('refresh page ignores old identity and environment responses then resumes under the current context', async () => {
  for (const key of ['userId', 'roleId', 'token', 'selected_environment']) {
    const pending = [deferred(), deferred()]
    let i = 0
    const h = setup('page', { replace: () => pending[i++].promise })
    h.mount()
    await flush()
    const old = h.user[key]
    h.user[key] = typeof old === 'number' ? old + 1 : old + '-b'
    h.user[key] = old
    pending[0].reject(Error('old'))
    await flush()
    assert.equal(h.failed.value, false)
    assert.equal(h.calls.length, 2)
    pending[1].resolve()
    await flush()
    h.close()
  }
})

async function memoryRouter() {
  const router = vueRouter.createRouter({
    history: vueRouter.createMemoryHistory(),
    routes: [
      { path: '/redirect/:path(.*)*', component: {} },
      { path: '/detail/:id', name: 'Detail', component: {} },
      { path: '/', redirect: '/home' },
      { path: '/home', name: 'Home', component: {} },
      { path: '/404', name: '404', component: {} },
      { path: '/403', name: '403', component: {} },
      { path: '/other', name: 'Other', component: {} },
      { path: '/:pathMatch(.*)*', redirect: '/404' },
    ],
  })
  await router.push('/detail/a%2Fb?id=0&id=2#section')
  await router.isReady()
  return router
}

test('real router toolbar-to-refresh-to-page round trip preserves encoded slashes, query arrays and hash', async () => {
  const router = await memoryRouter(),
    toolbar = setup('hook', { realRouter: router }),
    task = toolbar.refresh()
  await toolbar.tick()
  await task
  assert.equal(router.currentRoute.value.path, '/redirect/detail/a%2Fb')
  assert.deepEqual(router.currentRoute.value.params.path, ['detail', 'a/b'])
  toolbar.close()
  const page = setup('page', { realRouter: router })
  await page.redirect()
  assert.equal(router.currentRoute.value.path, '/detail/a%2Fb')
  assert.equal(router.currentRoute.value.params.id, 'a/b')
  assert.deepEqual(router.currentRoute.value.query.id, ['0', '2'])
  assert.equal(router.currentRoute.value.hash, '#section')
  page.close()
})

test('real refresh route preserves percent-encoded question/hash/Unicode and decodes each parameter once', async () => {
  for (const segment of ['a%3Fb', 'a%23b', '%E6%A8%A1%E5%9D%97', 'literal%252Fslash']) {
    const router = await memoryRouter()
    await router.push('/redirect/detail/' + segment)
    const h = setup('page', { realRouter: router })
    await h.redirect()
    assert.equal(router.currentRoute.value.path, '/detail/' + segment)
    h.close()
  }
})

test('real empty/root and missing-page targets continue through normal homepage and 404 routing', async () => {
  for (const [target, expected] of [
    ['/redirect', '/home'],
    ['/redirect/missing', '/404'],
  ]) {
    const router = await memoryRouter()
    await router.push(target)
    const h = setup('page', { realRouter: router })
    await h.redirect()
    assert.equal(router.currentRoute.value.path, expected)
    h.close()
  }
})

test('real target guards can deny, abort or reject and retries remain under router control', async () => {
  for (const mode of ['deny', 'abort', 'reject']) {
    const router = await memoryRouter()
    await router.push('/redirect/detail/value')
    let block = true
    router.onError(() => {})
    router.beforeEach((to) => {
      if (to.name !== 'Detail' || !block) return true
      if (mode === 'deny') return '/403'
      if (mode === 'abort') return false
      throw Error('fixture')
    })
    const h = setup('page', { realRouter: router })
    await h.redirect()
    if (mode === 'deny') assert.equal(router.currentRoute.value.path, '/403')
    else {
      assert.equal(h.failed.value, true)
      assert.equal(h.loading.value, false)
      block = false
      await h.redirect()
      assert.equal(router.currentRoute.value.name, 'Detail')
    }
    h.close()
  }
})

test('newer real navigation cancels old refresh and old component never pulls user back', async () => {
  const router = await memoryRouter()
  await router.push('/redirect/detail/value')
  const pending = deferred()
  router.beforeEach((to) => (to.name === 'Detail' ? pending.promise : true))
  const h = setup('page', { realRouter: router }),
    task = h.redirect()
  await flush()
  await router.push('/other')
  pending.resolve(true)
  await task
  assert.equal(router.currentRoute.value.name, 'Other')
  assert.equal(h.failed.value, false)
  h.close()
})

test('page and toolbar Options API SFC scripts/templates compile with global theme and density styles', () => {
  for (const filename of [pageFile, headerFile]) {
    const { descriptor } = parse(readFileSync(filename, 'utf8'))
    compileScript(descriptor, { id: filename })
    assert.deepEqual(
      compileTemplate({ id: filename, filename, source: descriptor.template.content }).errors,
      []
    )
  }
})
