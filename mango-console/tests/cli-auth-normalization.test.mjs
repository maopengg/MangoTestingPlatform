import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/cli-auth')
const params = (extra = {}) => ({
  redirect_uri: 'http://127.0.0.1:42001/callback',
  state: 'example-state',
  code_challenge: 'example-challenge',
  version: 'example-version',
  ...extra,
})
const result = (extra = {}) => ({ data: { code: 'example-once-code', expires_in: 60, ...extra } })
function page(api = {}, options = {}) {
  const route = vue.reactive({
    path: '/cli-auth',
    query: params(options.query),
    fullPath: '/cli-auth?flow=first',
  })
  const user = vue.reactive({
      token: options.token === undefined ? 'example-session' : options.token,
    }),
    lifecycle = {},
    replacements = [],
    assignments = []
  const originalWindow = globalThis.window
  globalThis.window = {
    location: {
      assign: (value) => {
        if (options.assignError) throw Error('example navigation failed')
        assignments.push(value)
      },
    },
  }
  const state = harness('index', 'authorize,status,statusText,errorMessage,deactivate', {
    base,
    api,
    modules: {
      vue: {
        ...vue,
        onMounted: (fn) => {
          lifecycle.mount = fn
        },
        onActivated: (fn) => {
          lifecycle.activate = fn
        },
        onDeactivated: (fn) => {
          lifecycle.deactivate = fn
        },
        onBeforeUnmount: (fn) => {
          lifecycle.unmount = fn
        },
      },
      'vue-router': {
        useRoute: () => route,
        useRouter: () => ({
          replace: async (target) => {
            replacements.push(target)
            if (options.replace) return options.replace(target)
          },
        }),
      },
      '@/store/modules/user': { default: () => user },
    },
  })
  return {
    ...state,
    route,
    user,
    lifecycle,
    replacements,
    assignments,
    close() {
      lifecycle.unmount()
      state.close()
      if (originalWindow === undefined) delete globalThis.window
      else globalThis.window = originalWindow
    },
  }
}
test('CLI authorization page compiles script, template and scoped layout', () => {
  const filename = path.join(base, 'index.vue'),
    { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: filename })
  assert.deepEqual(
    compileTemplate({
      filename,
      id: filename,
      source: descriptor.template.content,
      compilerOptions: { bindingMetadata: script.bindings },
    }).errors,
    []
  )
})
test('callback retains existing loopback, path, scheme and explicit port limits', () => {
  const state = page(),
    { validatedCallback } = state.load('params.ts')
  assert.equal(validatedCallback('http://127.0.0.1:42001/callback').hostname, '127.0.0.1')
  for (const value of [
    '',
    'invalid',
    'https://127.0.0.1:42001/callback',
    'http://localhost:42001/callback',
    'http://example.com:42001/callback',
    'http://[::1]:42001/callback',
    'http://127.0.0.1/callback',
    'http://127.0.0.1:42001/other',
    'http://user:password@127.0.0.1:42001/callback',
    'http://127.0.0.1:42001/callback?next=example',
    'http://127.0.0.1:42001/callback#example',
  ])
    assert.equal(validatedCallback(value), null, value)
  state.close()
})
test('query parser rejects duplicate/nonstring/missing required values and copies only authorization fields', () => {
  const state = page(),
    { authorizationParams } = state.load('params.ts'),
    source = params({ unrelated: 'ignored' })
  const parsed = authorizationParams(source)
  assert.deepEqual(parsed, params())
  source.state = 'changed'
  assert.equal(parsed.state, 'example-state')
  for (const key of ['redirect_uri', 'state', 'code_challenge', 'version'])
    for (const value of [undefined, null, '', [], ['duplicate'], 42])
      assert.equal(authorizationParams(params({ [key]: value })), null)
  state.close()
})
test('response validation rejects malformed results and error messages are narrowed from unknown', () => {
  const state = page(),
    { isAuthorizationResult, authorizationErrorMessage } = state.load('params.ts')
  for (const value of [
    null,
    [],
    {},
    'code',
    { code: undefined, expires_in: 60 },
    { code: '', expires_in: 60 },
    { code: 'example', expires_in: 0 },
    { code: 'example', expires_in: -1 },
    { code: 'example', expires_in: '60' },
  ])
    assert.equal(isAuthorizationResult(value), false)
  assert.equal(isAuthorizationResult(result().data), true)
  assert.equal(authorizationErrorMessage({ message: 'example failure' }), 'example failure')
  assert.equal(authorizationErrorMessage('unknown'), '授权失败，请重试。')
  state.close()
})
test('API wrapper keeps original endpoint, silent error mode and fixed payload without session token', async () => {
  const source = readFileSync('src/api/cli-auth.ts', 'utf8'),
    exports = {},
    requests = []
  new Function(
    'exports',
    'require',
    ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
  )(exports, () => ({
    post: (options) => {
      requests.push(options)
      return Promise.resolve(result())
    },
  }))
  const payload = { ...params(), token: 'example-ignored', unrelated: 'ignored' }
  await exports.authorizeCli(payload)
  payload.state = 'changed'
  assert.equal(requests[0].url, '/cli/auth/authorize')
  assert.equal(requests[0].silentError, true)
  assert.deepEqual(requests[0].data, params())
  assert.equal('token' in requests[0].data, false)
})
test('unauthenticated visit redirects to login with exact original path and never authorizes', async () => {
  let requests = 0
  const state = page(
    {
      authorizeCli: async () => {
        requests++
        return result()
      },
    },
    { token: '' }
  )
  await state.authorize()
  assert.deepEqual(state.replacements, [
    { path: '/login', query: { redirect: state.route.fullPath } },
  ])
  assert.equal(requests, 0)
  assert.deepEqual(state.assignments, [])
  state.close()
})
test('login navigation rejection and aborted navigation become retryable errors', async () => {
  for (const replace of [
    async () => {
      throw Error('example router failed')
    },
    async () => ({ type: 'aborted' }),
  ]) {
    const state = page({}, { token: '', replace })
    await state.authorize()
    assert.equal(state.status.value, 'error')
    assert.ok(state.errorMessage.value)
    state.close()
  }
})
test('invalid parameters do not send a request or redirect', async () => {
  let requests = 0
  const state = page(
    {
      authorizeCli: async () => {
        requests++
        return result()
      },
    },
    { query: { redirect_uri: 'https://example.com/callback' } }
  )
  await state.authorize()
  assert.equal(state.status.value, 'error')
  assert.match(state.errorMessage.value, /参数无效/)
  assert.equal(requests, 0)
  assert.deepEqual(state.assignments, [])
  state.close()
})
test('authorization prevents duplicates, sends a snapshot and returns only code/state to original callback', async () => {
  const pending = deferred(),
    requests = [],
    state = page({
      authorizeCli: (payload) => {
        requests.push(payload)
        return pending.promise
      },
    })
  const task = state.authorize()
  await state.authorize()
  assert.equal(requests.length, 1)
  assert.deepEqual(requests[0], params())
  assert.equal(state.status.value, 'loading')
  pending.resolve(result({ code: 'example+code/&' }))
  await task
  assert.equal(state.status.value, 'success')
  assert.equal(state.assignments.length, 1)
  const url = new URL(state.assignments[0])
  assert.equal(url.hostname, '127.0.0.1')
  assert.equal(url.port, '42001')
  assert.equal(url.searchParams.get('code'), 'example+code/&')
  assert.equal(url.searchParams.get('state'), 'example-state')
  assert.deepEqual([...url.searchParams.keys()], ['code', 'state'])
  await state.authorize()
  assert.equal(requests.length, 1)
  state.close()
})
test('request failure preserves error and allows explicit retry', async () => {
  let fail = true,
    calls = 0
  const state = page({
    authorizeCli: async () => {
      calls++
      if (fail) throw Error('example business error')
      return result()
    },
  })
  await state.authorize()
  assert.equal(state.status.value, 'error')
  assert.equal(state.errorMessage.value, 'example business error')
  fail = false
  await state.authorize()
  assert.equal(calls, 2)
  assert.equal(state.status.value, 'success')
  state.close()
})
test('malformed successful response does not redirect', async () => {
  for (const data of [
    undefined,
    null,
    {},
    [],
    { code: '', expires_in: 60 },
    { code: 'example', expires_in: 0 },
  ]) {
    const state = page({ authorizeCli: async () => ({ data }) })
    await state.authorize()
    assert.equal(state.status.value, 'error')
    assert.match(state.errorMessage.value, /有效的 CLI 授权结果/)
    assert.deepEqual(state.assignments, [])
    state.close()
  }
})
test('callback navigation failure releases pending guard for retry', async () => {
  let calls = 0
  const state = page(
    {
      authorizeCli: async () => {
        calls++
        return result()
      },
    },
    { assignError: true }
  )
  await state.authorize()
  assert.equal(state.status.value, 'error')
  await state.authorize()
  assert.equal(calls, 2)
  state.close()
})
test('mounted route parameter change ignores old code and uses new callback/state', async () => {
  const pending = [],
    state = page({
      authorizeCli: (payload) => new Promise((resolve) => pending.push({ payload, resolve })),
    })
  state.lifecycle.mount()
  assert.equal(pending.length, 1)
  state.route.query = params({
    redirect_uri: 'http://127.0.0.1:42002/callback',
    state: 'next-state',
  })
  state.route.fullPath = '/cli-auth?flow=next'
  await flush()
  assert.equal(pending.length, 2)
  pending[0].resolve(result({ code: 'old-code' }))
  await flush()
  assert.deepEqual(state.assignments, [])
  assert.equal(state.status.value, 'loading')
  pending[1].resolve(result({ code: 'new-code' }))
  await flush()
  const url = new URL(state.assignments[0])
  assert.equal(url.port, '42002')
  assert.equal(url.searchParams.get('state'), 'next-state')
  assert.equal(url.searchParams.get('code'), 'new-code')
  state.close()
})
test('session identity change rejects old result and begins a request for current identity', async () => {
  const pending = [],
    state = page({ authorizeCli: () => new Promise((resolve) => pending.push(resolve)) })
  state.lifecycle.mount()
  state.user.token = 'next-example-session'
  await flush()
  assert.equal(pending.length, 2)
  pending[0](result({ code: 'old-code' }))
  await flush()
  assert.deepEqual(state.assignments, [])
  pending[1](result({ code: 'new-code' }))
  await flush()
  assert.equal(new URL(state.assignments[0]).searchParams.get('code'), 'new-code')
  state.close()
})
test('logout redirects to login and old authorization cannot send code', async () => {
  const pending = deferred(),
    state = page({ authorizeCli: () => pending.promise })
  state.lifecycle.mount()
  state.user.token = ''
  await flush()
  assert.equal(state.replacements.length, 1)
  pending.resolve(result())
  await flush()
  assert.deepEqual(state.assignments, [])
  state.close()
})
test('route leave and unmount suppress late error or redirect', async () => {
  for (const outcome of ['success', 'error']) {
    const pending = deferred(),
      state = page({ authorizeCli: () => pending.promise })
    const task = state.authorize()
    state.route.path = '/login'
    state.route.fullPath = '/login'
    state.lifecycle.unmount()
    outcome === 'success' ? pending.resolve(result()) : pending.reject(Error('late failure'))
    await task
    assert.deepEqual(state.assignments, [])
    assert.notEqual(state.errorMessage.value, 'late failure')
    state.close()
  }
})
test('KeepAlive initial activation avoids duplicates; paused authorization resumes with a fresh session', async () => {
  const pending = [],
    state = page({ authorizeCli: () => new Promise((resolve) => pending.push(resolve)) })
  state.lifecycle.mount()
  state.lifecycle.activate()
  assert.equal(pending.length, 1)
  state.lifecycle.deactivate()
  pending[0](result({ code: 'paused-code' }))
  await flush()
  assert.deepEqual(state.assignments, [])
  state.lifecycle.activate()
  assert.equal(pending.length, 2)
  pending[1](result({ code: 'resumed-code' }))
  await flush()
  assert.equal(state.assignments.length, 1)
  state.lifecycle.deactivate()
  state.lifecycle.activate()
  assert.equal(pending.length, 2)
  state.close()
})

test('a changed flow while cached resets completed state and authorizes only after reactivation', async () => {
  const pending = [],
    state = page({ authorizeCli: () => new Promise((resolve) => pending.push(resolve)) })
  state.lifecycle.mount()
  pending[0](result({ code: 'first-code' }))
  await flush()
  assert.equal(state.status.value, 'success')
  state.lifecycle.deactivate()
  state.route.query = params({ state: 'next-state' })
  state.route.fullPath = '/cli-auth?flow=second'
  await flush()
  assert.equal(pending.length, 1)
  assert.equal(state.status.value, 'loading')
  state.lifecycle.activate()
  assert.equal(pending.length, 2)
  pending[1](result({ code: 'second-code' }))
  await flush()
  assert.equal(new URL(state.assignments[1]).searchParams.get('state'), 'next-state')
  state.close()
})
