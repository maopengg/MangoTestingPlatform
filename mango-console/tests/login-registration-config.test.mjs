import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = 'src/views/login/index.vue'
const source = readFileSync(new URL('../src/views/login/index.vue', import.meta.url), 'utf8')
const handler = source.slice(source.indexOf('  async function loadRegistrationConfig()'), source.indexOf('  function returnToLogin()'))
const { outputText } = ts.transpileModule(handler, { compilerOptions: { target: ts.ScriptTarget.ES2020 } })

test('registration submit has a themed gap after the email field without changing login spacing', () => {
  assert.match(source, /\.form-content > \.item-wrapper \+ \.login-btn\s*\{\s*margin-top: var\(--m-space-lg\);/)
  const register = source.slice(source.indexOf('<div v-else class="form-content">'), source.indexOf('<div class="links-wrapper">'))
  assert.match(register, /v-model="baseData.email"[\s\S]*?<\/div>\s*<a-button[\s\S]*?@click="onRegister"/)
  const login = source.slice(source.indexOf('<div v-if="baseData.isLogin === true"'), source.indexOf('<div v-else class="form-content">'))
  assert.match(login, /class="remember-forgot"[\s\S]*?<\/div>\s*<a-button/)
})

function harness(get) {
  const state = { loading: false, configLoading: true, showAuthor: false }, form = { isLogin: true }, info = [], errors = []
  const { click, load } = new Function('branding', 'registrationState', 'baseData', 'Message', `let registrationConfigRequest; ${outputText}; return { click: register1, load: loadRegistrationConfig }`)(
    { loadPublicConfig: async () => (await get({ url: '/user/registration-config', timeout: 10_000 })).data },
    state, form, { info: message => info.push(message), error: message => errors.push(message) }
  )
  return { state, form, info, errors, click, load }
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

test('the public config controls author visibility independently of registration', async () => {
  for (const visible of [true, false]) {
    const h = harness(async () => ({ data: {
      allow_registration: false, disabled_message: '注册关闭', show_author_info: visible,
    } }))
    await h.load()
    assert.equal(h.state.showAuthor, visible)
    assert.equal(h.state.configLoading, false)
    assert.equal(h.form.isLogin, true)
    assert.deepEqual(h.info, [])
  }
})

test('page initialization and a concurrent register click share one config request', async () => {
  let resolve, calls = 0
  const h = harness(() => { calls++; return new Promise(done => { resolve = done }) })
  const initial = h.load()
  const click = h.click()
  assert.equal(calls, 1)
  resolve({ data: { allow_registration: true, disabled_message: '', show_author_info: true } })
  await Promise.all([initial, click])
  assert.equal(h.state.showAuthor, true)
  assert.equal(h.form.isLogin, false)
})
