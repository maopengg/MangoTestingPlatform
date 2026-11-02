import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

function transpile(source) {
  return ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
}

const permissions = { exports: {} }
new Function('exports', transpile(fs.readFileSync(
  new URL('../src/utils/permission.ts', import.meta.url), 'utf8'
)))(permissions.exports)
const { hasPermissionKeys } = permissions.exports

test('页面入口对应查看权限，旧页面键不能自动变成查看授权', () => {
  assert.equal(hasPermissionKeys(['api.case:read'], false, 'api.case'), true)
  assert.equal(hasPermissionKeys(['api.case'], false, 'api.case'), false)
})

test('operation permissions support individual keys, alternatives and super administrators', () => {
  assert.equal(hasPermissionKeys(['api.case'], false, 'api.case:change'), false)
  assert.equal(hasPermissionKeys(['api.case:change'], false, 'api.case:change'), true)
  assert.equal(hasPermissionKeys(['ui.case:change'], false, ['ui.case:change', 'ui.page:change']), true)
  assert.equal(hasPermissionKeys([], false, []), false)
  assert.equal(hasPermissionKeys([], true, 'api.case:remove'), true)
})

test('public report access grants only shared read and export operations', () => {
  assert.equal(hasPermissionKeys([], false, 'report:read', true), true)
  assert.equal(hasPermissionKeys([], false, 'report:read', true), true)
  assert.equal(hasPermissionKeys([], false, 'report:change', true), false)
  assert.equal(hasPermissionKeys([], false, 'report:change', true), false)
  assert.equal(hasPermissionKeys([], false, 'api.case:change', true), false)
  assert.equal(hasPermissionKeys([], false, 'report:read', false), false)
})

test('table actions show all operations and retain business visibility conditions', () => {
  const source = fs.readFileSync(new URL('../src/components/table/MangoTableActions.vue', import.meta.url), 'utf8')
  const start = source.indexOf('  const normalizedActions =')
  const end = source.indexOf('  function actionKey', start)
  const code = transpile(source.slice(start, end))
  const props = { maxInline: 2, actions: [
    { label: '详情', permission: 'api.case:read' },
    { label: '删除', permission: 'api.case:remove' },
    { label: '编辑', permission: 'api.case:change' },
    { label: '隐藏操作', hidden: true },
  ] }
  const state = new Function('props', 'permissionStore', 'computed',
    `${code}; return { normalizedActions, visibleInlineActions, overflowActions };`
  )(props, { hasPermission: (key) => hasPermissionKeys(['api.case:read'], false, key) },
    (getter) => ({ get value() { return getter() } }))
  assert.deepEqual(state.normalizedActions.value.map((action) => action.label), ['详情', '删除', '编辑'])
  assert.equal(state.visibleInlineActions.value.length, 3)
  assert.equal(state.overflowActions.value.length, 0)
})

test('explicit overflow actions stay in more even with only one or two inline actions', () => {
  const source = fs.readFileSync(new URL('../src/components/table/MangoTableActions.vue', import.meta.url), 'utf8')
  const start = source.indexOf('  const normalizedActions =')
  const code = transpile(source.slice(start, source.indexOf('  function actionKey', start)))
  for (const labels of [['详细报告'], ['详细报告', '重试']]) {
    const props = { maxInline: 2, actions: [...labels.map((label) => ({ label })),
      { label: '排查与排除', permission: 'report:change', overflow: true }] }
    let allowed = true
    const state = new Function('props', 'permissionStore', 'computed',
      `${code}; return { visibleInlineActions, overflowActions };`)(props,
      { hasPermission: (key) => !key || allowed }, (getter) => ({ get value() { return getter() } }))
    assert.deepEqual(state.visibleInlineActions.value.map((action) => action.label), labels)
    assert.deepEqual(state.overflowActions.value.map((action) => action.label), ['排查与排除'])
    allowed = false
    assert.equal(state.overflowActions.value.length, 1)
  }
})

test('table click handling checks loading and disabled, not role permissions', () => {
  const source = fs.readFileSync(new URL('../src/components/table/MangoTableActions.vue', import.meta.url), 'utf8')
  const code = transpile(source.slice(source.indexOf('  function handleClick('), source.indexOf('</script>')))
  const handle = new Function(`${code}; return handleClick`)()
  let calls = 0
  handle({ onClick: () => calls++ })
  handle({ disabled: true, onClick: () => calls++ })
  handle({ loading: true, onClick: () => calls++ })
  assert.equal(calls, 1)
  assert.doesNotMatch(source, /hasPermission|permission\??:/)
})

const roleSource = fs.readFileSync(new URL('../src/views/system/role/index.vue', import.meta.url), 'utf8')
const loadStart = roleSource.indexOf('  async function onSelectRole(')
const loadEnd = roleSource.indexOf('  function onAdd(', loadStart)
const roleCode = transpile(roleSource.slice(loadStart, loadEnd))
function deferred() {
  let resolve, reject
  const promise = new Promise((ok, fail) => { resolve = ok; reject = fail })
  return { promise, resolve, reject }
}

test('refreshing own permissions preserves menus while loading and replaces routes only after success', async () => {
  const source = fs.readFileSync(new URL('../src/store/modules/permission.ts', import.meta.url), 'utf8')
  const start = source.indexOf('    async initPermissionRoute(')
  const end = source.indexOf('    isEmptyPermissionRoute(', start)
  const code = transpile(`const actions = { ${source.slice(start, end)} };`)
  const request = deferred()
  let removed = 0
  const oldRoutes = [{ path: '/system/role' }]
  const registered = []
  const action = new Function('router', 'mapTwoLevelRouter', 'findRootPathRoute', 'constantRoutes', 'onRemove',
    `let removePermissionRoutes = [() => { onRemove() }]; ${code}; return actions.initPermissionRoute;`
  )({ addRoute: (route) => { registered.push(route); return () => {} } },
    (routes) => routes, () => '/index/home', [], () => { removed++ })
  const state = {
    permissionRoutes: oldRoutes,
    getRoutes: () => request.promise,
    clearPermissionRoute: () => { throw new Error('must not clear live permissions') },
  }
  const saving = action.call(state, true)
  assert.equal(state.permissionRoutes, oldRoutes)
  assert.equal(removed, 0)
  const updated = [{ path: '/system/role' }, { path: '/report' }]
  request.resolve(updated)
  await saving
  assert.equal(removed, 1)
  assert.deepEqual(state.permissionRoutes, updated)
  assert.equal(registered.length, 4)
  const failed = deferred()
  state.getRoutes = () => failed.promise
  const retry = action.call(state, true)
  failed.reject(new Error('network failed'))
  await assert.rejects(retry, /network failed/)
  assert.deepEqual(state.permissionRoutes, updated)
  assert.equal(registered.length, 4)
})
function roleLoader() {
  const requests = new Map()
  const selectedRole = { value: null }
  const loadedRoleId = { value: null }
  const panel = { saving: false, loading: false, checkedKeys: [], treeData: [] }
  const select = new Function('permissionPanel', 'selectedRole', 'loadedRoleId', 'canReadPermission',
    'getUserRolePermission', 'toPermissionTree', 'findFirstPageKey', 'console',
    `let permissionRequestId = 0; ${roleCode}; return onSelectRole;`
  )(panel, selectedRole, loadedRoleId, { value: true }, (id) => {
    const pending = deferred()
    requests.set(id, pending)
    return pending.promise
  }, (tree) => tree, (tree) => tree[0]?.key || '', { log() {} })
  return { panel, requests, selectedRole, loadedRoleId, select }
}

test('late responses cannot overwrite the selected role permission set', async () => {
  const state = roleLoader()
  const first = state.select({ id: 1 })
  const second = state.select({ id: 2 })
  state.requests.get(2).resolve({ data: { tree: [], checked_keys: ['api.case'] } })
  await second
  state.requests.get(1).resolve({ data: { tree: [], checked_keys: ['system.role'] } })
  await first
  assert.equal(state.selectedRole.value.id, 2)
  assert.equal(state.loadedRoleId.value, 2)
  assert.deepEqual(state.panel.checkedKeys, ['api.case'])
  assert.equal(state.panel.loading, false)
})

test('failed loads clear stale permissions and cannot leave a role ready to save', async () => {
  const state = roleLoader()
  state.panel.checkedKeys = ['system.role:change']
  const pending = state.select({ id: 2 })
  assert.deepEqual(state.panel.checkedKeys, [])
  state.requests.get(2).reject(new Error('request failed'))
  await pending
  assert.equal(state.loadedRoleId.value, null)
  assert.equal(state.panel.loading, false)
})

test('role selection is blocked while permission saving is in progress', async () => {
  const state = roleLoader()
  state.selectedRole.value = { id: 1 }
  state.panel.saving = true
  await state.select({ id: 2 })
  assert.equal(state.selectedRole.value.id, 1)
  assert.equal(state.requests.size, 0)
})
