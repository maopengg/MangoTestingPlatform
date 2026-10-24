import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = 'src/views/login/index.vue'
const source = readFileSync(new URL('../src/views/login/index.vue', import.meta.url), 'utf8')
const handler = source.slice(source.indexOf('  async function register1()'), source.indexOf('  function returnToLogin()'))
const { outputText } = ts.transpileModule(handler, { compilerOptions: { target: ts.ScriptTarget.ES2020 } })

function harness(get) {
  const state = { loading: false }, form = { isLogin: true }, info = [], errors = []
  const click = new Function('get', 'registrationState', 'baseData', 'Message', `${outputText}; return register1`)(
    get, state, form, { info: message => info.push(message), error: message => errors.push(message) }
  )
  return { state, form, info, errors, click }
}

test('registration is controlled by the public database configuration, not build-time env', async () => {
  let request
  const h = harness(async options => {
    request = options
    return { data: { allow_registration: true, disabled_message: '注册关闭' } }
  })
  await h.click()
  assert.equal(request.url, '/user/registration-config')
  assert.equal(request.timeout, 10_000)
  assert.equal(h.form.isLogin, false)
  assert.equal(h.state.loading, false)
  assert.doesNotMatch(source, /VITE_ALLOW_HOME_REGISTRATION|VITE_REGISTRATION_DISABLED_MESSAGE/)
})

test('disabled registration shows the administrator configured message and preserves the login form', async () => {
  const h = harness(async () => ({ data: { allow_registration: false, disabled_message: '请向管理员申请' } }))
  await h.click()
  assert.equal(h.form.isLogin, true)
  assert.deepEqual(h.info, ['请向管理员申请'])
  assert.equal(h.state.loading, false)
})

test('every registration entry click refreshes configuration instead of caching an old switch', async () => {
  let enabled = true, calls = 0
  const h = harness(async () => {
    calls++
    return { data: { allow_registration: enabled, disabled_message: '注册关闭' } }
  })
  await h.click()
  h.form.isLogin = true
  enabled = false
  await h.click()
  assert.equal(calls, 2)
  assert.equal(h.form.isLogin, true)
  assert.deepEqual(h.info, ['注册关闭'])
})

test('loading blocks duplicate requests and keeps the register entry in a local loading state', async () => {
  let resolve, calls = 0
  const h = harness(() => { calls++; return new Promise(done => { resolve = done }) })
  const first = h.click()
  assert.equal(h.state.loading, true)
  await h.click()
  assert.equal(calls, 1)
  resolve({ data: { allow_registration: true, disabled_message: '' } })
  await first
  assert.equal(h.state.loading, false)
  assert.match(source, /:loading="registrationState.loading"/)
  assert.match(source, /:disabled="registrationState.loading"/)
})

test('request failure and malformed configuration do not open registration, and allow retry', async () => {
  for (const get of [
    async () => { throw new Error('offline') },
    async () => ({ data: null }),
    async () => ({ data: { allow_registration: 'false', disabled_message: '' } }),
  ]) {
    const h = harness(get)
    await h.click()
    assert.equal(h.form.isLogin, true)
    assert.equal(h.state.loading, false)
    assert.deepEqual(h.errors, ['注册配置加载失败，请稍后重试'])
  }
})

test('login script and template compile with the async registration entry', () => {
  const { descriptor } = parse(source, { filename })
  const script = compileScript(descriptor, { id: 'login-registration-config' })
  const template = compileTemplate({
    source: descriptor.template.content, filename, id: 'login-registration-config',
    compilerOptions: { bindingMetadata: script.bindings },
  })
  assert.deepEqual(template.errors, [])
})
