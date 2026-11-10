import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { md5 } from 'js-md5'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const config = { allow_registration: true, disabled_message: '注册关闭', show_author_info: true }
const account = { userId: 1, roleId: null, token: 'fixture-token', userName: 'person@example.com', name: 'Example', selected_environment: 0, roles: [{ roleId: null, roleName: null, description: null }], is_super_admin: false }
function setup(overrides = {}) {
  const hooks = { mounted: [], activated: [], deactivated: [], unmounted: [] }
  const route = vue.reactive({ path: '/login', fullPath: '/login', query: {} })
  const user = vue.reactive({ userId: 0, roleId: 0, token: '', saveUser(info) { Object.assign(this, info); return Promise.resolve(info) } })
  const calls = [], messages = [], navigation = [], sockets = []
  const api = {
    loginAccount: async (...args) => { calls.push(['login', ...args]); return { code: 200, data: account } },
    registerAccount: async (...args) => { calls.push(['register', ...args]); return { code: 200, msg: '已注册' } },
    resetAccountPassword: async (...args) => { calls.push(['reset', ...args]); return { code: 200, msg: '已发送' } },
    ...overrides.api,
  }
  const permission = { homePath: '/index/home', initPermissionRoute: async () => {}, ...overrides.permission }
  const h = harness('index', 'mode,loginForm,registrationForm,submission,busy,registrationState,resetPassword,onLogin,onRegister,register1,returnToLogin,forgotPassword,cancelPasswordReset,resetPasswordByEmail,loadRegistrationConfig', {
    base: path.resolve('src/views/login'),
    modules: {
      vue: { ...vue, onMounted: fn => hooks.mounted.push(fn), onActivated: fn => hooks.activated.push(fn), onDeactivated: fn => hooks.deactivated.push(fn), onBeforeUnmount: fn => hooks.unmounted.push(fn) },
      'vue-router': { useRoute: () => route, useRouter: () => ({ replace: async target => { navigation.push(target); return overrides.navigate?.(target) } }) },
      'js-md5': { md5 },
      '@/api/user/authentication': api,
      '@/store/modules/user': { default: () => user },
      '@/store/modules/permission': { default: () => permission },
      '@/store/modules/platform-branding': { default: () => ({ loadPublicConfig: overrides.config || (async () => config) }) },
      '@/store/modules/app-config': { default: () => ({ applyCurrentThemePreset() {} }) },
      '@/hooks/useAppInfo': { default: () => ({ version: 'fixture' }) },
      '@/assets/logo.svg': { default: '' }, '@/assets/login-code-texture.jpg': { default: '' },
      '@/utils/socket': { markWebSocketLoginSession: () => sockets.push('mark'), connectWebSocket: (...args) => sockets.push(args) },
      '@arco-design/web-vue/es/icon': new Proxy({}, { get: () => ({}) }),
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning', 'info'].map(key => [key, value => messages.push([key, value])])) },
    },
  })
  hooks.mounted.forEach(fn => fn())
  h.loginForm.username = 'person@example.com'; h.loginForm.password = ' secret '
  return { ...h, hooks, route, user, calls, messages, navigation, sockets }
}
function dispose(h) { h.hooks.unmounted.forEach(fn => fn()); h.close() }

test('login submits only the existing double digest protocol and allows null role and zero environment', async () => {
  const h = setup(); await flush(); await h.onLogin()
  assert.deepEqual(h.calls[0], ['login', 'person@example.com', md5(md5('secret'))])
  assert.equal(h.user.roleId, null); assert.equal(h.user.selected_environment, 0)
  assert.deepEqual(h.navigation, ['/index/home']); assert.equal(h.messages.at(-1)[0], 'success')
  assert.equal(h.submission.value, null); dispose(h)
})
test('empty credentials and actuator-only account never submit', async () => {
  const h = setup(); h.loginForm.username = ''; await h.onLogin(); h.loginForm.username = 'open'; await h.onLogin()
  assert.equal(h.calls.length, 0); dispose(h)
})
test('physical login lock survives deactivate/reactivate and releases on failure for retry', async () => {
  const pending = deferred(); let count = 0
  const h = setup({ api: { loginAccount: () => { count++; return count === 1 ? pending.promise : Promise.resolve({ code: 200, data: account }) } } })
  const first = h.onLogin(); h.hooks.deactivated.forEach(fn => fn()); h.hooks.activated.forEach(fn => fn())
  h.loginForm.password = 'secret'; await h.onLogin(); assert.equal(count, 1)
  pending.reject(new Error('offline')); await first; assert.equal(h.messages.length, 0)
  await h.onLogin(); assert.equal(count, 2); dispose(h)
})
test('route A-B-A and identity changes invalidate late login before saving user', async () => {
  for (const change of [h => { h.route.fullPath = '/elsewhere'; h.route.fullPath = '/login' }, h => { h.user.token = 'another-session'; h.user.token = '' }]) {
    const pending = deferred(); const h = setup({ api: { loginAccount: () => pending.promise } })
    const job = h.onLogin(); change(h); pending.resolve({ code: 200, data: account }); await job
    assert.equal(h.user.userId, 0); assert.equal(h.navigation.length, 0); assert.equal(h.sockets.length, 0); dispose(h)
  }
})
test('menu completion after identity switch cannot navigate or open socket', async () => {
  const pending = deferred(); let valid
  const h = setup({ permission: { initPermissionRoute: (_force, guard) => { valid = guard; return pending.promise } } })
  const job = h.onLogin(); await flush(); assert.equal(valid(), true)
  h.user.token = 'other-session'; assert.equal(valid(), false); pending.resolve(); await job
  assert.equal(h.navigation.length, 0); assert.equal(h.sockets.length, 0); dispose(h)
})
test('login rejects malformed or unsuccessful responses and permits retry', async () => {
  for (const response of [{ code: 300, data: account }, { code: 200, data: {} }]) {
    const h = setup({ api: { loginAccount: async () => response } }); await h.onLogin()
    assert.equal(h.user.userId, 0); assert.equal(h.submission.value, null); assert.equal(h.messages.at(-1)[0], 'error'); dispose(h)
  }
})
test('redirect remains internal and navigation rejection cannot report login success', async () => {
  for (const [redirect, expected] of [['//example.com', '/index/home'], ['/report/index', '/report/index']]) {
    const h = setup({ navigate: () => ({ type: 4 }) }); h.route.query.redirect = redirect; await h.onLogin()
    assert.deepEqual(h.navigation, [expected]); assert.equal(h.messages.some(([type]) => type === 'success'), false); dispose(h)
  }
})
test('initial config and registration entry share request; duplicate entry is blocked', async () => {
  const pending = deferred(); let count = 0
  const h = setup({ config: () => { count++; return pending.promise } })
  const job = h.register1(); await h.register1(); assert.equal(count, 1); assert.equal(h.registrationState.loading, true)
  pending.resolve(config); await job; assert.equal(h.mode.value, 'register'); assert.equal(h.registrationState.showAuthor, true); dispose(h)
})
test('registration rechecks server switch and shows administrator message', async () => {
  let enabled = true; const h = setup({ config: async () => ({ ...config, allow_registration: enabled }) }); await flush()
  await h.register1(); h.returnToLogin(); enabled = false; await h.register1()
  assert.equal(h.mode.value, 'login'); assert.deepEqual(h.messages.at(-1), ['info', '注册关闭']); dispose(h)
})
test('configuration failure/malformed response does not open registration and supports retry', async () => {
  for (const value of [null, { allow_registration: 'false', disabled_message: '' }]) {
    let failed = true; const h = setup({ config: async () => failed ? value : config }); await flush(); await h.register1()
    assert.equal(h.mode.value, 'login'); assert.equal(h.registrationState.loading, false)
    failed = false; await h.register1(); assert.equal(h.mode.value, 'register'); dispose(h)
  }
})
test('configuration that settles after unmount does not open registration or show author', async () => {
  const pending = deferred(); const h = setup({ config: () => pending.promise }); const job = h.register1()
  h.hooks.unmounted.forEach(fn => fn()); pending.resolve(config); await job
  assert.equal(h.mode.value, 'login'); assert.equal(h.registrationState.showAuthor, false); h.close()
})
test('environment change invalidates pending registration entry even when restored synchronously', async () => {
  const pending = deferred(); const h = setup({ config: () => pending.promise }); const job = h.register1()
  h.user.selected_environment = 2; h.user.selected_environment = undefined
  pending.resolve(config); await job
  assert.equal(h.mode.value, 'login'); assert.equal(h.registrationState.loading, false); dispose(h)
})
test('non-success registration and password reset retain drafts and release submission', async () => {
  const h = setup({ api: { registerAccount: async () => ({ code: 300 }), resetAccountPassword: async () => ({ code: 300 }) } })
  await flush(); await h.register1(); Object.assign(h.registrationForm, { name: 'Example', email: 'person@example.com' })
  await h.onRegister(); assert.equal(h.mode.value, 'register'); assert.equal(h.submission.value, null)
  h.returnToLogin(); h.forgotPassword(); h.resetPassword.email = 'person@example.com'
  assert.equal(await h.resetPasswordByEmail(), false); assert.equal(h.resetPassword.email, 'person@example.com'); assert.equal(h.submission.value, null); dispose(h)
})
test('register failure retains draft and retry success maps only name/email and clears draft', async () => {
  let failed = true; const h = setup({ api: { registerAccount: async (...args) => { h.calls.push(['register', ...args]); if (failed) throw new Error('offline'); return { code: 200, msg: 'ok' } } } }); await flush(); await h.register1()
  Object.assign(h.registrationForm, { name: ' Example ', email: ' Person@Example.COM ' }); await h.onRegister()
  assert.equal(h.mode.value, 'register'); assert.equal(h.registrationForm.name, ' Example ')
  failed = false; await h.onRegister(); assert.deepEqual(h.calls.at(-1), ['register', 'Example', 'person@example.com'])
  assert.equal(h.mode.value, 'login'); assert.equal(h.loginForm.username, 'person@example.com'); assert.equal(h.loginForm.password, '')
  assert.deepEqual({ ...h.registrationForm }, { name: '', email: '' }); dispose(h)
})
test('registration physically locks duplicate requests and return while pending', async () => {
  const pending = deferred(); let count = 0; const h = setup({ api: { registerAccount: () => { count++; return pending.promise } } }); await flush(); await h.register1()
  Object.assign(h.registrationForm, { name: 'Example', email: 'person@example.com' }); const job = h.onRegister(); h.returnToLogin(); await h.onRegister()
  assert.equal(count, 1); assert.equal(h.mode.value, 'register'); pending.resolve({ code: 200, msg: 'ok' }); await job; dispose(h)
})
test('reset validates, blocks duplicate/cancel while pending, retains failed email and supports retry', async () => {
  const pending = deferred(); let count = 0; const h = setup({ api: { resetAccountPassword: () => { count++; return count === 1 ? pending.promise : Promise.resolve({ code: 200, msg: 'sent' }) } } })
  h.forgotPassword(); h.resetPassword.email = 'bad'; assert.equal(await h.resetPasswordByEmail(), false); assert.equal(count, 0)
  h.resetPassword.email = ' Person@Example.COM '; const job = h.resetPasswordByEmail()
  assert.equal(h.cancelPasswordReset(), false); assert.equal(await h.resetPasswordByEmail(), false); assert.equal(count, 1)
  pending.reject(new Error('offline')); assert.equal(await job, false); assert.equal(h.resetPassword.email, ' Person@Example.COM ')
  assert.equal(await h.resetPasswordByEmail(), true); assert.equal(h.resetPassword.email, ''); dispose(h)
})
test('late reset response cannot close or clear newly opened context', async () => {
  const pending = deferred(); const h = setup({ api: { resetAccountPassword: () => pending.promise } })
  h.forgotPassword(); h.resetPassword.email = 'person@example.com'; const job = h.resetPasswordByEmail()
  h.user.token = 'different'; h.resetPassword.email = 'new@example.com'; pending.resolve({ code: 200, msg: 'sent' })
  assert.equal(await job, false); assert.equal(h.resetPassword.email, 'new@example.com'); assert.equal(h.messages.length, 0); dispose(h)
})
test('cancel and reopen discard reset draft; registration return and reentry use fresh drafts', async () => {
  const h = setup(); h.forgotPassword(); h.resetPassword.email = 'old@example.com'; h.cancelPasswordReset(); h.forgotPassword(); assert.equal(h.resetPassword.email, '')
  await flush(); await h.register1(); h.registrationForm.name = 'old'; h.returnToLogin(); await h.register1(); assert.equal(h.registrationForm.name, ''); dispose(h)
})
test('login script and template compile; register button keeps separation after email', () => {
  const filename = 'src/views/login/index.vue'; const source = readFileSync(filename, 'utf8'); const { descriptor } = parse(source, { filename }); const script = compileScript(descriptor, { id: 'login-normalization' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'login-normalization', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  assert.match(source, /\.form-content > \.item-wrapper \+ \.login-btn\s*\{\s*margin-top: var\(--m-space-lg\);/)
})
