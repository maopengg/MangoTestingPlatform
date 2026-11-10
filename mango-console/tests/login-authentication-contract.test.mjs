import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { deferred } from './helpers/case-details-harness.mjs'

const compile = source => ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText

test('login response mapping excludes extra fields and preserves nullable guest and zero IDs', () => {
  const exports = {}
  new Function('exports', compile(readFileSync('src/views/login/records.ts', 'utf8')))(exports)
  const row = { userId: 1, roleId: null, token: 'fixture-token', userName: 'person@example.com', name: 'Example', selected_environment: 0, roles: [{ roleId: null, roleName: null, description: null }], password: 'must-not-copy' }
  const mapped = exports.readLoginUser(row)
  assert.equal(mapped.roleId, null); assert.equal(mapped.selected_environment, 0); assert.equal(mapped.avatar, '')
  assert.equal('password' in mapped, false); assert.notEqual(mapped.roles, row.roles)
  for (const patch of [{ token: '' }, { roles: {} }, { userId: '1' }, { selected_environment: undefined }]) {
    assert.throws(() => exports.readLoginUser({ ...row, ...patch }))
  }
})

test('authentication adapters preserve endpoints and explicitly map credentials', async () => {
  const exports = {}, calls = []
  const source = readFileSync('src/api/user/authentication.ts', 'utf8')
  new Function('exports', 'require', compile(source))(exports, name => name === '@/api/http'
    ? { post: async options => { calls.push(options); return { code: 200 } } }
    : { login: '/login', register: '/register' })
  await exports.loginAccount('person@example.com', 'fixture-digest')
  await exports.registerAccount('Example', 'person@example.com')
  await exports.resetAccountPassword('person@example.com')
  assert.deepEqual(calls, [
    { url: '/login', data: { username: 'person@example.com', password: 'fixture-digest', type: 1 } },
    { url: '/register', data: { name: 'Example', email: 'person@example.com' } },
    { url: '/reset-password', data: { email: 'person@example.com' } },
  ])
})

function menuHarness() {
  const source = readFileSync('src/store/modules/permission.ts', 'utf8')
  const read = source.slice(source.indexOf('    async getRoutes('), source.indexOf('    clearPermissionRoute('))
  const init = source.slice(source.indexOf('    async initPermissionRoute('), source.indexOf('    isEmptyPermissionRoute('))
  const pending = deferred(), registered = [], removed = [], old = [{ path: '/old' }]
  const actions = new Function('post', 'getMenuListByRoleId', 'generatorRoutes', 'mapTwoLevelRouter', 'findRootPathRoute', 'router', 'constantRoutes', 'removed',
    `let removePermissionRoutes = [() => removed.push('old')]; ${compile(`const actions = {${read}${init}}`)}; return actions`
  )(() => pending.promise, '/menu', value => value, value => value, () => '/index/home', { addRoute: route => { registered.push(route); return () => {} } }, [], removed)
  const state = { ...actions, permissionRoutes: old, permissionKeys: ['old:read'], isSuperAdmin: false, homePath: '/old' }
  return { pending, registered, removed, state, old }
}

test('invalidated menu response cannot write permission keys, remove routes or install old routes', async () => {
  const h = menuHarness(); let current = true
  const job = h.state.initPermissionRoute(true, () => current)
  current = false
  h.pending.resolve({ data: { menus: [{ path: '/new' }], permissions: ['new:read'], is_super_admin: true } })
  await job
  assert.deepEqual(h.state.permissionKeys, ['old:read']); assert.equal(h.state.isSuperAdmin, false)
  assert.equal(h.state.permissionRoutes, h.old); assert.deepEqual(h.registered, []); assert.deepEqual(h.removed, [])
})

test('default menu initialization retains ordinary route replacement semantics', async () => {
  const h = menuHarness(), menus = [{ path: '/new' }]
  const job = h.state.initPermissionRoute(true)
  h.pending.resolve({ data: { menus, permissions: ['new:read'], is_super_admin: false } }); await job
  assert.deepEqual(h.state.permissionKeys, ['new:read']); assert.deepEqual(h.state.permissionRoutes, menus)
  assert.deepEqual(h.removed, ['old']); assert.equal(h.registered.length, 3)
})
