import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync, readdirSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush as flushVue, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/personal')
const success = data => ({ code: 200, data })
const profile = (id = 1, patch = {}) => success([{ id, name: 'Fixture user', username: 'user@example.com', role: { name: 'Member' }, last_login_time: null, ip: null, requires_email_login_migration: false, ...patch }])
const cacheItem = (key = 'selected_environment', patch = {}) => ({ cache_key: key, title: key, value: 0, display_value: 'Fixture environment', value_type: 'environment', description: '', clearable: true, updated_at: null, has_value: true, ...patch })
const cacheGroup = (key = 'preferences', items = [cacheItem()]) => ({ group_key: key, title: key, count: items.length, value_count: items.filter(item => item.has_value).length, items })
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
  const exposed = component === 'index' ? 'profile,loading,failed,loggingOut,passwordDialog,contextVersion,isContextCurrent,loadProfile,openPassword,handlePasswordChanged' :
    component === 'PasswordChangeDialog' ? 'draft,visible,submitting,formRef,visibleFields,open,closeDialog:close,confirm' :
    'groups,loading,failed,clearingKey,loadData,confirmDeleteGroup,confirmDeleteItem,cacheActions'
  const h = harness(component, exposed, { base, props: { userId: 1, requiresEmailMigration: false, contextVersion: 0, isContextCurrent: version => version === context && !doc.hidden && route.path === '/personal/info', ...initialProps }, modules: {
    vue: { ...vue, onMounted: fn => life.mount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn), onBeforeUnmount: fn => life.unmount.push(fn) },
    'vue-router': { useRoute: () => route },
    '@/store/modules/user': { default: () => user },
    '@arco-design/web-vue': { Message: { success: value => messages.push(['success', value]), error: value => messages.push(['error', value]), warning: value => messages.push(['warning', value]) }, Modal: { confirm: options => {
      const modal = { options, closed: false, close() { modal.closed = true } }; confirmations.push(modal); return modal
    } } },
    '@/api/user/user': {
      getUserInfo: query => { reads.push(query); return api.read ? api.read(query) : Promise.resolve(profile(query.id)) },
      getUserCacheData: () => { reads.push({ cache: true }); return api.read ? api.read() : Promise.resolve(success([cacheGroup()])) },
      postUserPassword: payload => { writes.push(payload); return api.write ? api.write(payload) : Promise.resolve(success(null)) },
      clearUserCacheData: payload => { writes.push(payload); return api.write ? api.write(payload) : Promise.resolve(success({ count: 1 })) },
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

test('cache mapping preserves zero, false, null and nested JSON with detached whitelist values', () => {
  const h = setup(), items = [cacheItem(), cacheItem('boolean', { value: false, display_value: false, value_type: 'boolean' }), cacheItem('json', { value: { rows: [0, false, null] }, display_value: { rows: [0, false, null] }, value_type: 'json' }), cacheItem('empty', { value: null, display_value: null, has_value: false })]
  const parsed = h.boundary.readCacheGroups(success([cacheGroup('preferences', items)]))[0]
  assert.equal(parsed.value_count, 3)
  assert.equal(parsed.items[0].value, 0); assert.equal(parsed.items[1].value, false)
  items[2].value.rows.push('changed'); assert.deepEqual(parsed.items[2].value, { rows: [0, false, null] })
  assert.equal(h.boundary.formatDisplayValue(false), '否'); assert.equal(h.boundary.formatDisplayValue(0), '0')
  assert.equal(h.boundary.formatDisplayValue({ a: 1 }), '{"a":1}')
  for (const value of [success(null), success([{ ...cacheGroup(), count: 2 }]), success([cacheGroup('preferences', [cacheItem(), cacheItem()])]), success([cacheGroup('preferences', [cacheItem('bad', { value_type: 'unknown' })])]), success([cacheGroup('preferences', [cacheItem('bad', { value: null, has_value: true })])])]) assert.throws(() => h.boundary.readCacheGroups(value))
  assert.equal(h.boundary.clearedCacheCount(success({ count: 0 })), 0)
  assert.throws(() => h.boundary.clearedCacheCount(success({ count: false })))
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

test('cache reads coalesce, distinguish failed/empty data and retry synchronous failures without leaking a rejected promise', async () => {
  let result = success([cacheGroup()]), throwing = false
  const h = setup('UserCachePanel', { read: () => { if (throwing) throw Error('Fixture error'); return Promise.resolve(result) } })
  h.mount(); await flush(); assert.equal(h.groups.value.length, 1)
  throwing = true; await h.loadData(); assert.equal(h.failed.value, true); assert.equal(h.groups.value.length, 1)
  throwing = false; result = success(null); await h.loadData(); assert.equal(h.failed.value, true)
  result = success([]); await h.loadData(); assert.equal(h.failed.value, false); assert.deepEqual(h.groups.value, [])
  h.close()
})

test('cache simultaneous reads coalesce and a response after unmount never repopulates cleared groups', async () => {
  const pending = deferred(), h = setup('UserCachePanel', { read: () => pending.promise })
  h.mount(); const first = h.loadData(), second = h.loadData(); await flush()
  assert.equal(h.reads.length, 1)
  h.close()
  pending.resolve(success([cacheGroup()])); await Promise.all([first, second])
  assert.deepEqual(h.groups.value, []); assert.equal(h.loading.value, false)
})

test('cache deletion confirmation waits for Promise, enforces a physical lock and retries after failure', async () => {
  const pending = deferred()
  let response = { code: 400 }
  const h = setup('UserCachePanel', { write: () => Promise.resolve(response) })
  h.mount(); await flush()
  const group = h.groups.value[0], item = group.items[0]
  h.confirmDeleteItem(group, item)
  const dialog = h.confirmations.at(-1)
  assert.equal(dialog.options.onOk, undefined)
  assert.equal(dialog.options.okButtonProps.status, 'danger')
  assert.equal(await dialog.options.onBeforeOk(), false); assert.equal(h.clearingKey.value, '')
  response = pending.promise
  const clearing = dialog.options.onBeforeOk()
  assert.equal(h.clearingKey.value, 'preferences:selected_environment')
  assert.equal(await dialog.options.onBeforeOk(), false)
  h.confirmDeleteGroup(group); assert.equal(h.confirmations.length, 1)
  pending.resolve(success({ count: 1 })); assert.equal(await clearing, true)
  assert.equal(h.clearingKey.value, ''); assert.equal(h.user.selected_environment, null)
  assert.deepEqual(h.writes.at(-1), { group_key: 'preferences', cache_key: 'selected_environment' })
  h.close()
})

test('unrelated group deletion does not reset the environment; protected and empty cache items cannot be deleted', async () => {
  const group = cacheGroup('other', [cacheItem('saved', { value_type: 'number', value: 0, display_value: 0 }), cacheItem('protected', { clearable: false }), cacheItem('empty', { has_value: false, value: null, display_value: null })])
  const h = setup('UserCachePanel', { read: async () => success([group]) })
  h.mount(); await flush()
  h.confirmDeleteItem(h.groups.value[0], h.groups.value[0].items[1]); h.confirmDeleteItem(h.groups.value[0], h.groups.value[0].items[2])
  assert.equal(h.confirmations.length, 0)
  h.confirmDeleteGroup(h.groups.value[0]); assert.equal(await h.confirmations.at(-1).options.onBeforeOk(), true)
  assert.deepEqual(h.writes[0], { group_key: 'other' })
  assert.equal(h.user.selected_environment, 0)
  h.close()
})

test('zero-count environment clear leaves the selected environment unchanged and stale confirmation cannot submit', async () => {
  const h = setup('UserCachePanel', { write: async () => success({ count: 0 }) })
  h.mount(); await flush(); h.confirmDeleteGroup(h.groups.value[0])
  const old = h.confirmations.at(-1)
  h.confirmDeleteGroup(h.groups.value[0]); assert.equal(old.closed, true)
  assert.equal(await old.options.onBeforeOk(), false); assert.deepEqual(h.writes, [])
  assert.equal(await h.confirmations.at(-1).options.onBeforeOk(), true)
  assert.equal(h.user.selected_environment, 0)
  h.close()
})

test('deleting a different preferences item leaves environment intact; protected environment is never synchronized', async () => {
  const h = setup('UserCachePanel', { read: async () => success([cacheGroup('preferences', [cacheItem('selected_environment', { clearable: false }), cacheItem('other', { value_type: 'boolean', value: false, display_value: false })])]) })
  h.mount(); await flush()
  h.confirmDeleteItem(h.groups.value[0], h.groups.value[0].items[1])
  assert.equal(await h.confirmations.at(-1).options.onBeforeOk(), true)
  assert.equal(h.user.selected_environment, 0)
  h.confirmDeleteGroup(h.groups.value[0])
  assert.equal(await h.confirmations.at(-1).options.onBeforeOk(), true)
  assert.equal(h.user.selected_environment, 0)
  h.close()
})

test('cache successful delete followed by failed reload closes confirmation but exposes stale data as failed and disabled', async () => {
  let fail = false
  const h = setup('UserCachePanel', { read: async () => { if (fail) throw Error('Refresh failed'); return success([cacheGroup('other')]) } })
  h.mount(); await flush(); h.confirmDeleteItem(h.groups.value[0], h.groups.value[0].items[0])
  fail = true
  assert.equal(await h.confirmations.at(-1).options.onBeforeOk(), true)
  assert.equal(h.failed.value, true); assert.equal(h.loading.value, false)
  assert.equal(h.clearingKey.value, '')
  assert.equal(h.cacheActions(h.groups.value[0], h.groups.value[0].items[0])[0].disabled, true)
  h.close()
})

test('stale cache delete cannot reset a new identity, show success or release the physical lock before its request finishes', async () => {
  const pending = deferred(), h = setup('UserCachePanel', { write: () => pending.promise })
  h.mount(); await flush(); h.confirmDeleteGroup(h.groups.value[0])
  const dialog = h.confirmations.at(-1), clearing = dialog.options.onBeforeOk()
  h.user.roleId = 2; h.user.roleId = 1; await flush()
  assert.equal(dialog.closed, true); assert.equal(h.clearingKey.value, 'preferences')
  h.confirmDeleteGroup(h.groups.value[0]); assert.equal(h.confirmations.length, 1)
  pending.resolve(success({ count: 1 })); assert.equal(await clearing, false)
  assert.equal(h.user.selected_environment, 0)
  assert.equal(h.messages.some(message => message[0] === 'success'), false)
  assert.equal(h.clearingKey.value, '')
  h.close()
})

test('cache identity A-B-A, background and KeepAlive never publish old groups; resumed reads remove listeners on unmount', async () => {
  const pending = [deferred(), deferred(), deferred()]
  let index = 0
  const h = setup('UserCachePanel', { read: () => index < 3 ? pending[index++].promise : Promise.resolve(success([cacheGroup()])) })
  h.mount(); await flush(); h.user.roleId = 2; await flush(); h.user.roleId = 1; await flush()
  pending[0].resolve(success([cacheGroup('old')])); pending[1].reject(Error('Old failure')); await flush()
  assert.deepEqual(h.groups.value, []); assert.equal(h.loading.value, true)
  pending[2].resolve(success([cacheGroup()])); await flush(); assert.equal(h.groups.value[0].group_key, 'preferences')
  h.hide(); assert.equal(h.loading.value, false); h.show(); await flush()
  h.pause(); h.user.selected_environment = 1; await flush(); assert.deepEqual(h.groups.value, [])
  h.resume(); await flush(); assert.equal(h.groups.value.length, 1)
  h.close(); assert.equal(h.listeners.size, 0)
})

test('all personal page SFCs compile and configuration uses the actual compact cache operation column', () => {
  for (const filename of ['index.vue', ...readdirSync(path.join(base, 'components')).map(name => `components/${name}`)]) {
    const file = path.join(base, filename), { descriptor, errors } = parse(readFileSync(file, 'utf8'), { filename: file })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    const template = compileTemplate({ source: descriptor.template.content, filename: file, id: file, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [], filename)
  }
  const h = setup(), columns = h.load('config.ts').cacheColumns
  assert.equal(columns.at(-1).width, 120); assert.equal(columns.at(-1).fixed, 'right')
  h.close()
})
