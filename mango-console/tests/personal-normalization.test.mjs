import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync, readdirSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush as flushVue, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/personal')
const success = data => ({ code: 200, data })
const profile = (id = 1, patch = {}) => success([{ id, name: 'Fixture user', username: 'user@example.com', role: { name: 'Member' }, departments: [], ip: null, requires_email_login_migration: false, ...patch }])
async function flush() { await flushVue(); await new Promise(resolve => setImmediate(resolve)) }
function setup(component = 'index', api = {}, initialProps = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-token', selected_environment: 0 })
  const route = vue.reactive({ path: '/personal/info' }), life = { mount: [], activate: [], deactivate: [], unmount: [] }
  const reads = [], writes = [], messages = [], confirmations = [], listeners = new Set()
  const previousDocument = globalThis.document, previousWindow = globalThis.window
  const doc = Object.assign(new EventTarget(), { hidden: false })
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (type, fn) => { listeners.add(fn); add(type, fn) }
  doc.removeEventListener = (type, fn) => { listeners.delete(fn); remove(type, fn) }
  globalThis.document = doc
  let reloads = 0, logouts = 0
  globalThis.window = { localStorage: { removeItem() {} }, location: { reload() { reloads++ } } }
  user.logout = async () => { logouts++; if (api.logout) return api.logout(user); user.userId = 0; user.token = '' }
  let context = 0
  const exposed = component === 'index' ? 'profile,loading,failed,loggingOut,passwordDialog,resetPasswordDialog,contextVersion,isContextCurrent,loadProfile,openPassword,openResetPassword,handlePasswordChanged,handlePasswordReset' :
    component === 'PasswordChangeDialog' ? 'draft,visible,submitting,formRef,visibleFields,open,closeDialog:close,confirm' :
    component === 'PasswordResetDialog' ? 'visible,submitting,open,closeDialog:close,confirm' :
    ''
  const h = harness(component, exposed, { base, props: { userId: 1, requiresEmailMigration: false, contextVersion: 0, isContextCurrent: version => version === context && !doc.hidden && route.path === '/personal/info', ...initialProps }, modules: {
    vue: { ...vue, onMounted: fn => life.mount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn), onBeforeUnmount: fn => life.unmount.push(fn) },
    'vue-router': { useRoute: () => route },
    '@/store/modules/user': { default: () => user },
    '@arco-design/web-vue': { Message: { success: value => messages.push(['success', value]), error: value => messages.push(['error', value]), warning: value => messages.push(['warning', value]) }, Modal: { confirm: options => {
      const modal = { options, closed: false, close() { modal.closed = true } }; confirmations.push(modal); return modal
    } } },
    '@/api/user/user': {
      getUserInfo: query => { reads.push(query); return api.read ? api.read(query) : Promise.resolve(profile(query.id)) },
      postUserPassword: payload => { writes.push(payload); return api.write ? api.write(payload) : Promise.resolve(success(null)) },
      resetOwnPassword: (...args) => { writes.push(args); return api.reset ? api.reset() : Promise.resolve(success(null)) },
    },
  } })
  return { ...h, user, route, doc, reads, writes, messages, confirmations, listeners,
    get logouts() { return logouts }, get reloads() { return reloads },
    boundary: h.load('records.ts'), mount() { life.mount.forEach(fn => fn()) },
    pause() { life.deactivate.forEach(fn => fn()) }, resume() { life.activate.forEach(fn => fn()) },
    hide() { doc.hidden = true; doc.dispatchEvent(new Event('visibilitychange')) }, show() { doc.hidden = false; doc.dispatchEvent(new Event('visibilitychange')) },
    invalidate() { context++; h.props.contextVersion = context },
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = previousDocument; globalThis.window = previousWindow },
  }
}
const fillPassword = h => Object.assign(h.draft, { password: 'FixtureOld#9', email: 'new@example.com', new_password: 'FixtureNew#9', confirm_password: 'FixtureNew#9' })

test('profile response is finite, detached and owned by the requested user; wrong and malformed data fail', () => {
  const h = setup(), input = profile(1, { extra: 'ignored' }), parsed = h.boundary.readPersonalProfile(input, 1)
  assert.equal(parsed.roleName, 'Member'); assert.equal(parsed.ip, null); assert.equal('extra' in parsed, false)
  input.data[0].role.name = 'Changed'; assert.equal(parsed.roleName, 'Member')
  for (const bad of [profile(2), success([]), success(null), { code: 403, data: [] }, profile(1, { role: false }), profile(1, { requires_email_login_migration: 'false' })])
    assert.throws(() => h.boundary.readPersonalProfile(bad, 1))
  assert.equal(h.boundary.readPersonalProfile(profile(1, { role: null }), 1).roleName, null)
  h.close()
})

test('profile displays department names from the existing response and an empty department as a dash', () => {
  const h = setup(), input = profile(1, { departments: [{ id: 1, name: 'Engineering' }, { id: 2, name: 'QA' }] })
  const parsed = h.boundary.readPersonalProfile(input, 1)
  input.data[0].departments[0].name = 'Changed'
  assert.deepEqual(parsed.departmentNames, ['Engineering', 'QA'])
  assert.deepEqual(h.boundary.readPersonalProfile(profile(), 1).departmentNames, [])
  for (const departments of [null, {}, [{ name: 3 }]]) assert.throws(() => h.boundary.readPersonalProfile(profile(1, { departments }), 1))
  assert.match(readFileSync(path.join(base, 'index.vue'), 'utf8'), /departmentNames\.join\('、'\) \|\| '-'/)
  h.close()
})

test('own password reset sends no target or historical password and emits success once', async () => {
  const pending = deferred(), h = setup('PasswordResetDialog', { reset: () => pending.promise })
  h.open(); const saving = h.confirm()
  assert.equal(h.submitting.value, true)
  assert.equal(await h.confirm(), false)
  assert.deepEqual(h.writes, [[]])
  pending.resolve(success(null)); assert.equal(await saving, true)
  assert.equal(h.visible.value, false)
  assert.deepEqual(h.events, [['reset', 0]])
  h.close()
})

test('password reset is retryable after failure, blocks legacy email accounts and ignores stale success', async () => {
  const pending = deferred()
  let result = { code: 300 }
  const h = setup('PasswordResetDialog', { reset: () => Promise.resolve(result) })
  h.props.requiresEmailMigration = true; h.open(); assert.equal(h.visible.value, false)
  assert.equal(await h.confirm(), false); assert.deepEqual(h.writes, [])
  h.props.requiresEmailMigration = false; h.open()
  assert.equal(await h.confirm(), false); assert.equal(h.visible.value, true); assert.equal(h.submitting.value, false)
  result = pending.promise
  const saving = h.confirm(); h.invalidate(); h.open()
  assert.equal(h.visible.value, false)
  pending.resolve(success(null)); assert.equal(await saving, false); assert.deepEqual(h.events, [])
  h.open(); assert.equal(h.visible.value, true)
  h.close()
})

test('personal reset success logs out and profile suspension closes both password windows', async () => {
  const h = setup('index')
  let changesClosed = 0, resetOpened = 0, resetClosed = 0
  h.passwordDialog.value = { close() { changesClosed++ }, open() {} }
  h.resetPasswordDialog.value = { close() { resetClosed++ }, open() { resetOpened++ } }
  h.mount(); await flush(); h.openResetPassword()
  assert.equal(changesClosed, 1); assert.equal(resetOpened, 1)
  h.hide(); assert.equal(resetClosed, 1)
  h.show(); await flush()
  await h.handlePasswordReset(h.contextVersion.value)
  assert.equal(h.logouts, 1); assert.equal(h.reloads, 1)
  assert.ok(h.messages.some(([, value]) => value.includes('随机密码已发送')))
  h.close()
})

test('password payload snapshots allowed fields, omits migration email when unnecessary and enforces required/matching input', () => {
  const h = setup(), draft = { ...h.boundary.passwordDraft(), password: 'Old#Fixture9', new_password: 'New#Fixture9', confirm_password: 'New#Fixture9', email: ' user@example.com ', extra: 'ignored' }
  const payload = h.boundary.passwordPayload(draft, 1, true)
  assert.deepEqual(payload, { id: 1, password: 'Old#Fixture9', new_password: 'New#Fixture9', confirm_password: 'New#Fixture9', email: 'user@example.com' })
  assert.equal('email' in h.boundary.passwordPayload(draft, 1, false), false)
  for (const patch of [{ password: '' }, { new_password: '' }, { confirm_password: 'Different#9' }, { email: 'invalid' }]) assert.throws(() => h.boundary.passwordPayload({ ...draft, ...patch }, 1, true))
  h.close()
})

test('profile reads coalesce and remain retryable after malformed, rejected and synchronous failures', async () => {
  let result = profile(), fail = false
  const pending = deferred(), h = setup('index', { read: () => { if (fail) throw Error('Fixture failed'); return result === 'pending' ? pending.promise : Promise.resolve(result) } })
  h.mount(); await flush(); assert.equal(h.profile.value.id, 1)
  result = 'pending'; const first = h.loadProfile(), second = h.loadProfile(); await flush()
  assert.equal(h.reads.length, 2)
  pending.resolve(profile()); await Promise.all([first, second])
  fail = true; await h.loadProfile(); assert.equal(h.failed.value, true); assert.equal(h.loading.value, false)
  fail = false; result = success([]); await h.loadProfile(); assert.equal(h.failed.value, true)
  result = profile(); await h.loadProfile(); assert.equal(h.failed.value, false)
  h.close()
})

test('profile identity A-B-A drops old data/finalizers and immediately closes the old password window', async () => {
  const pending = [deferred(), deferred(), deferred()]
  let count = 0
  const h = setup('index', { read: () => pending[count++].promise })
  let closed = 0
  h.passwordDialog.value = { open() {}, close() { closed++ } }
  h.mount(); await flush()
  h.user.roleId = 2; await flush(); h.user.roleId = 1; await flush()
  assert.equal(h.profile.value, null); assert.equal(closed, 2)
  pending[0].resolve(profile(1, { name: 'Old A' })); pending[1].reject(Error('Old B')); await flush()
  assert.equal(h.profile.value, null); assert.equal(h.loading.value, true)
  pending[2].resolve(profile(1, { name: 'Current A' })); await flush()
  assert.equal(h.profile.value.name, 'Current A')
  h.close()
})

test('profile background, route and KeepAlive pauses discard old reads, resume and remove listeners', async () => {
  const old = deferred()
  let count = 0
  const h = setup('index', { read: () => ++count === 1 ? old.promise : Promise.resolve(profile()) })
  h.mount(); await flush(); h.hide()
  old.resolve(profile(1, { name: 'Hidden' })); await flush(); assert.equal(h.profile.value, null)
  h.show(); await flush(); assert.equal(h.profile.value.id, 1)
  h.pause(); h.user.selected_environment = 1; await flush(); assert.equal(h.profile.value, null)
  const reads = h.reads.length; h.resume(); await flush(); assert.equal(h.reads.length, reads + 1)
  h.route.path = '/other'; await flush(); assert.equal(h.loading.value, false)
  h.route.path = '/personal/info'; await flush(); assert.equal(h.profile.value.id, 1)
  h.close(); assert.equal(h.listeners.size, 0)
})

test('user/token changes and profile unmount reject old records even if the visible route later returns', async () => {
  const pending = deferred(), h = setup('index', { read: query => query.id === 1 ? pending.promise : Promise.resolve(profile(query.id)) })
  h.mount(); await flush()
  h.user.userId = 2; h.user.token = 'fixture-user-two'; await flush()
  assert.equal(h.profile.value.id, 2)
  pending.resolve(profile(1)); await flush(); assert.equal(h.profile.value.id, 2)
  const late = deferred()
  h.close()
  const old = setup('index', { read: () => late.promise })
  old.mount(); await flush(); old.close()
  late.resolve(profile(1)); await flush()
  assert.equal(old.profile.value, null); assert.equal(old.loading.value, false)
})

test('current password success logs out once and reloads; stale events and a new login during logout are ignored', async () => {
  const h = setup('index')
  h.mount(); await flush()
  await h.handlePasswordChanged(h.contextVersion.value)
  assert.equal(h.logouts, 1); assert.equal(h.reloads, 1)
  await h.handlePasswordChanged(0); assert.equal(h.logouts, 1)
  h.close()
  const pending = deferred(), newer = setup('index', { logout: () => pending.promise })
  newer.mount(); await flush()
  const first = newer.handlePasswordChanged(newer.contextVersion.value), repeated = newer.handlePasswordChanged(newer.contextVersion.value)
  assert.equal(newer.logouts, 1)
  newer.user.userId = 2; newer.user.token = 'fixture-new-login'
  pending.resolve(); await Promise.all([first, repeated])
  assert.equal(newer.reloads, 0); assert.equal(newer.user.userId, 2)
  newer.close()
})

test('password window resets all secrets and renders email only for accounts requiring migration', async () => {
  const h = setup('PasswordChangeDialog')
  h.open(); fillPassword(h)
  assert.equal(h.visibleFields.value.some(field => field.key === 'email'), false)
  h.closeDialog(); assert.deepEqual({ ...h.draft }, h.boundary.passwordDraft())
  h.props.requiresEmailMigration = true; h.open()
  assert.equal(h.visibleFields.value.some(field => field.key === 'email'), true)
  h.close()
})

test('password lock covers asynchronous validation, cancel and reopening until physical validation settles', async () => {
  const pending = deferred(), h = setup('PasswordChangeDialog')
  h.formRef.value = { validate: () => pending.promise, clearValidate() {} }
  h.open(); fillPassword(h)
  const saving = h.confirm(); assert.equal(h.submitting.value, true)
  h.closeDialog(); h.open(); assert.equal(h.visible.value, false)
  assert.equal(await h.confirm(), false)
  pending.resolve(undefined); assert.equal(await saving, false)
  assert.deepEqual(h.writes, []); assert.equal(h.submitting.value, false)
  h.open(); assert.equal(h.visible.value, true)
  h.close()
})

test('password validation failures and rejected writes keep a retryable draft without ever sending invalid fields', async () => {
  const h = setup('PasswordChangeDialog', { write: () => Promise.reject(Error('Fixture error')) })
  h.formRef.value = { validate: async () => ({ password: 'Invalid' }), clearValidate() {} }
  h.open(); fillPassword(h)
  assert.equal(await h.confirm(), false); assert.deepEqual(h.writes, [])
  assert.equal(h.submitting.value, false)
  h.formRef.value.validate = async () => undefined
  assert.equal(await h.confirm(), false)
  assert.equal(h.draft.new_password, 'FixtureNew#9'); assert.equal(h.visible.value, true)
  assert.equal(h.submitting.value, false)
  h.close()
})

test('password post stays locked after cancel; reopening after settlement has an empty draft and no late event', async () => {
  const pending = deferred(), h = setup('PasswordChangeDialog', { write: () => pending.promise })
  h.formRef.value = { validate: async () => undefined, clearValidate() {} }
  h.open(); fillPassword(h)
  const saving = h.confirm(); await flush()
  h.closeDialog(); h.open()
  assert.equal(h.visible.value, false); assert.equal(h.submitting.value, true)
  pending.resolve(success(null)); assert.equal(await saving, false)
  assert.deepEqual(h.events, [])
  h.open(); assert.equal(h.visible.value, true)
  assert.deepEqual({ ...h.draft }, h.boundary.passwordDraft())
  h.close()
})

test('password request uses a detached snapshot; failed business response retries and context invalidation never emits success', async () => {
  const pending = deferred()
  let result = { code: 400 }
  const h = setup('PasswordChangeDialog', { write: () => Promise.resolve(result) })
  h.formRef.value = { validate: async () => undefined, clearValidate() {} }
  h.open(); fillPassword(h)
  assert.equal(await h.confirm(), false); assert.equal(h.visible.value, true)
  assert.equal(h.submitting.value, false)
  result = pending.promise
  const saving = h.confirm(); await flush()
  const snapshot = h.writes.at(-1)
  h.draft.new_password = 'Changed while pending'
  assert.equal(snapshot.new_password, 'FixtureNew#9')
  h.invalidate(); assert.equal(h.visible.value, false)
  pending.resolve(success(null)); assert.equal(await saving, false)
  assert.equal(h.events.length, 0); assert.equal(h.submitting.value, false)
  h.close()
})

test('successful password write closes the window and emits its original context; unmount cannot emit late success', async () => {
  const h = setup('PasswordChangeDialog')
  h.formRef.value = { validate: async () => undefined, clearValidate() {} }
  h.open(); fillPassword(h)
  assert.equal(await h.confirm(), true)
  assert.deepEqual(h.events, [['changed', 0]]); assert.equal(h.visible.value, false)
  h.close()
  const pending = deferred(), old = setup('PasswordChangeDialog', { write: () => pending.promise })
  old.formRef.value = { validate: async () => undefined, clearValidate() {} }
  old.open(); fillPassword(old); const saving = old.confirm(); await flush(); old.close()
  pending.resolve(success(null)); assert.equal(await saving, false); assert.deepEqual(old.events, [])
})

test('all personal page SFCs compile and configuration uses the actual compact configuration operation column', () => {
  for (const filename of ['index.vue', ...readdirSync(path.join(base, 'components')).map(name => `components/${name}`)]) {
    const file = path.join(base, filename), { descriptor, errors } = parse(readFileSync(file, 'utf8'), { filename: file })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    const template = compileTemplate({ source: descriptor.template.content, filename: file, id: file, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [], filename)
  }
  const h = setup(), columns = h.load('config.ts').userConfigColumns
  assert.equal(columns.at(-1).width, 120); assert.equal(columns.at(-1).fixed, 'right')
  h.close()
})
