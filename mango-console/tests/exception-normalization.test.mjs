import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import * as Vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred } from './helpers/case-details-harness.mjs'

const root = path.resolve('src/views/exception')
const read = file => readFileSync(path.join(root, file), 'utf8')

function fixture(options = {}) {
  const user = Vue.reactive({ userId: 1, roleId: 2, token: 'fixture', selected_environment: 3,
    isTokenExpire: () => !!options.expired })
  const route = Vue.reactive({ path: '/403', fullPath: '/403' })
  const permission = { homePath: '/index/home', initPermissionRoute: options.init || (async () => {}) }
  const calls = [], hashes = [], hooks = {}
  const router = { replace: async target => {
    calls.push(target)
    if (options.replace) return options.replace(target)
    route.path = route.fullPath = target.path
  } }
  const scope = Vue.effectScope()
  const originalWindow = globalThis.window
  globalThis.window = { location: { origin: 'https://example.com', pathname: '/console/', search: '?mode=test',
    replace: value => hashes.push(value) } }
  const script = parse(read('components/ExceptionStatus.vue')).descriptor.script.content
  const module = { exports: {} }
  const deps = {
    vue: { ...Vue, onActivated: fn => { hooks.activate = fn }, onDeactivated: fn => { hooks.deactivate = fn },
      onBeforeUnmount: fn => { hooks.unmount = fn } },
    'vue-router': { useRoute: () => route, useRouter: () => router },
    '@/store/modules/user': { default: () => user },
    '@/store/modules/permission': { default: () => permission },
  }
  new Function('module', 'exports', 'require', ts.transpileModule(script, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText)(module, module.exports, name => {
    if (name.endsWith('.png')) return { default: name }
    assert.ok(name in deps, name)
    return deps[name]
  })
  const props = Vue.reactive({ status: '403' })
  const state = scope.run(() => module.exports.default.setup(props))
  return { ...state, props, user, permission, route, calls, hashes, hooks,
    dispose() { hooks.unmount?.(); scope.stop(); globalThis.window = originalWindow } }
}

test('status presentation supports numeric/string values and preserves the unknown-status fallback', () => {
  const f = fixture()
  try {
    for (const status of [403, '403', 404, '404', 500, '500', 'unknown']) {
      f.props.status = status
      const expected = String(status) === '403' ? '403' : String(status) === '404' ? '404' : '500'
      assert.match(f.statusImage.value, new RegExp(`img_${expected}`))
      assert.equal(f.statusTip.value, expected === '403' ? '您没有权限访问该页面' : expected === '404' ? '您访问的页面不存在' : '您访问的页面出错啦')
    }
  } finally { f.dispose() }
})

test('return refreshes routes once, shows loading, blocks repeated clicks and uses the assigned home', async () => {
  const wait = deferred(); let count = 0
  const f = fixture({ init: async force => { assert.equal(force, true); count++; await wait.promise } })
  try {
    f.permission.homePath = '/config/product/index'
    const pending = f.backHome()
    assert.equal(f.returnPending.value, true)
    await f.backHome()
    assert.equal(count, 1)
    assert.deepEqual(f.calls, [])
    wait.resolve(); await pending
    assert.deepEqual(f.calls, [{ path: '/config/product/index' }])
    assert.deepEqual(f.hashes, [])
    assert.equal(f.returnPending.value, false)
  } finally { f.dispose() }
})

test('expired sessions go directly to login while preserving the deployment path and search', async () => {
  const f = fixture({ expired: true, init: () => { throw Error('must not refresh') } })
  try {
    await f.backHome()
    assert.deepEqual(f.hashes, ['https://example.com/console/?mode=test#/login'])
    assert.deepEqual(f.calls, [])
    assert.equal(f.returnPending.value, false)
  } finally { f.dispose() }
})

test('an assigned login home uses the existing full-page fallback', async () => {
  const f = fixture()
  try {
    f.permission.homePath = '/login'; await f.backHome()
    assert.match(f.hashes[0], /#\/login$/)
    assert.deepEqual(f.calls, [])
  } finally { f.dispose() }
})

test('permission refresh failures release loading and keep the existing fallback/retry behavior', async () => {
  let count = 0
  const f = fixture({ init: async () => { count++; throw Error('fixture rejection') } })
  try {
    await f.backHome(); await f.backHome()
    assert.equal(count, 2)
    assert.equal(f.returnPending.value, false)
    assert.equal(f.hashes.length, 2)
    assert.match(f.hashes[0], /#\/index\/home$/)
  } finally { f.dispose() }
})

test('failed or unresolved router navigation preserves the hash fallback', async () => {
  for (const replace of [async () => { throw Error('fixture failure') }, async () => undefined]) {
    const f = fixture({ replace })
    try {
      await f.backHome()
      assert.equal(f.calls.length, 1)
      assert.match(f.hashes[0], /#\/index\/home$/)
      assert.equal(f.returnPending.value, false)
    } finally { f.dispose() }
  }
})

for (const change of ['identity', 'environment', 'route', 'deactivate', 'unmount']) {
  test(`${change} invalidates pending navigation, including rejected refresh responses`, async () => {
    for (const reject of [false, true]) {
      const wait = deferred()
      const f = fixture({ init: () => wait.promise })
      try {
        const pending = f.backHome()
        if (change === 'identity') f.user.roleId++
        if (change === 'environment') f.user.selected_environment++
        if (change === 'route') f.route.path = f.route.fullPath = '/personal/info'
        if (change === 'deactivate') f.hooks.deactivate()
        if (change === 'unmount') f.hooks.unmount()
        if (reject) wait.reject(Error('late fixture rejection')); else wait.resolve()
        await pending
        assert.deepEqual(f.calls, [])
        assert.deepEqual(f.hashes, [])
        assert.equal(f.returnPending.value, false)
      } finally { f.dispose() }
    }
  })
}

test('cache activation restores navigation without starting an automatic request', async () => {
  let count = 0
  const f = fixture({ init: async () => { count++ } })
  try {
    f.hooks.deactivate(); await f.backHome(); assert.equal(count, 0)
    f.hooks.activate(); assert.equal(count, 0)
    await f.backHome(); assert.equal(count, 1)
  } finally { f.dispose() }
})

test('all exception entry points and the shared status compile without changing their route contracts', async () => {
  for (const file of ['403.vue', '404.vue', '500.vue', 'components/ExceptionStatus.vue']) {
    const { descriptor, errors } = parse(read(file), { filename: file })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    const template = compileTemplate({ source: descriptor.template.content, filename: file, id: file,
      compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [], file)
    for (const style of descriptor.styles) {
      const result = await compileStyleAsync({ source: style.content, filename: file, id: file,
        scoped: style.scoped, preprocessLang: style.lang })
      assert.deepEqual(result.errors, [], file)
    }
    if (file !== 'components/ExceptionStatus.vue') assert.match(read(file), new RegExp(`status="${file.slice(0, 3)}"`))
  }
})
