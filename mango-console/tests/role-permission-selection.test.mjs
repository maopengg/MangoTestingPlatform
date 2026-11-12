import assert from 'node:assert/strict'
import test from 'node:test'
import { flush } from './helpers/case-details-harness.mjs'
import { setupRolePage, roleOk, permissionFixture } from './helpers/role-page-harness.mjs'

const id = `http.${'a'.repeat(64)}`

test('checking a menu grants its HTTP and MCP interfaces, excluding fixed rules', async t => {
  const mcp = `mcp.${'b'.repeat(64)}`, fixed = `http.${'c'.repeat(64)}`
  const h = setupRolePage({ getUserRolePermission: async () => roleOk({ ...permissionFixture(),
    tree: [{ permissionKey: 'index.home', children: [] }, { permissionKey: 'api.case', children: [] }],
    menu_keys: ['index.home'], endpoint_groups: [{ menu_key: 'api.case', endpoints: [
      ...[id, mcp, fixed].map((key, index) => ({ id: key, protocol: index === 1 ? 'mcp' : 'http',
        method: 'GET', name: 'read', description: '查看用例', urls: [], fixed: index === 2, fixed_enabled: index === 2, fixed_reason: '' })),
    ] }], endpoint_permissions: {},
  }) })
  t.after(h.close); h.mount(); await flush()
  h.onPageCheck(['api.case'])
  assert.deepEqual(h.permissionPanel.checkedKeys, ['api.case', 'index.home'])
  assert.deepEqual(h.endpointOverrides.value, { [id]: 'endpoint_allow', [mcp]: 'endpoint_allow' })
  h.onPageCheck([])
  assert.deepEqual(h.endpointOverrides.value, { [id]: 'endpoint_deny', [mcp]: 'endpoint_deny' })
})

test('guest remains readonly for menus and interfaces', async t => {
  const h = setupRolePage(); t.after(h.close); h.mount(); await flush()
  await h.onSelectRole({ id: 7, name: '游客', description: '' })
  const original = [...h.permissionPanel.checkedKeys]
  h.onPageCheck([]); h.onEndpointChange(id, 'endpoint_allow')
  assert.deepEqual(h.permissionPanel.checkedKeys, original)
  assert.deepEqual(h.endpointOverrides.value, {})
})

test('role parser requires pure interface snapshots and protects default pages', t => {
  const h = setupRolePage(); t.after(h.close)
  const helper = h.load('role-permissions.ts')
  assert.throws(() => helper.parseRolePermissions(roleOk({ tree: [], checked_keys: [] })))
  assert.throws(() => helper.parseRolePermissions(roleOk({ ...permissionFixture(), menu_keys: ['api.case:read'] })))
  const nodes = helper.toPermissionTree([{ permissionKey: 'help.variable', children: [] }])
  assert.equal(nodes[0].disabled, false)
  assert.equal(nodes[0].disableCheckbox, true)
  const roles = helper.parseRoles(roleOk([{ key: 1, title: '普通角色' }, { key: 2, title: '游客' }]))
  assert.equal(roles[0].name, '游客')
})

test('home and help nodes remain selectable while their checkboxes are locked', async t => {
  const h = setupRolePage({ getUserRolePermission: async () => roleOk({ ...permissionFixture(),
    tree: [{ permissionKey: 'index.home', children: [] }, { permissionKey: 'help', children: [
      { permissionKey: 'help.variable', children: [] },
    ] }], menu_keys: ['index.home', 'help', 'help.variable'],
  }) })
  t.after(h.close); h.mount(); await flush()
  const helper = h.load('role-permissions.ts')
  for (const key of ['index.home', 'help', 'help.variable']) {
    const node = helper.findPermissionNode(h.permissionPanel.treeData, key)
    assert.equal(node.disabled, false)
    assert.equal(node.disableCheckbox, true)
    h.onPageSelect([key])
    if (node.children.length) {
      h.onPageExpand([key], { expanded: true, node: { key } })
      assert.deepEqual(h.permissionPanel.expandedKeys, [key])
    } else assert.deepEqual(h.permissionPanel.selectedKeys, [key])
  }
  h.onPageCheck([])
  for (const key of ['index.home', 'help', 'help.variable']) {
    assert.ok(h.permissionPanel.checkedKeys.includes(key))
  }
})

test('checking a parent grants all child interfaces and unchecking one preserves shared interfaces', async t => {
  const shared = id, caseOnly = `mcp.${'b'.repeat(64)}`, infoOnly = `http.${'d'.repeat(64)}`
  const row = key => ({ id: key, protocol: key.startsWith('mcp') ? 'mcp' : 'http', method: 'GET',
    name: 'read', description: '查看', urls: [], fixed: false, fixed_enabled: false, fixed_reason: '' })
  const h = setupRolePage({ getUserRolePermission: async () => roleOk({ ...permissionFixture(),
    tree: [{ permissionKey: 'index.home', children: [] }, { permissionKey: 'api', children: [
      { permissionKey: 'api.case', children: [] }, { permissionKey: 'api.info', children: [] },
    ] }], menu_keys: ['index.home'], endpoint_permissions: {}, endpoint_groups: [
      { menu_key: 'api.case', endpoints: [row(shared), row(caseOnly)] },
      { menu_key: 'api.info', endpoints: [row(shared), row(infoOnly)] },
    ],
  }) })
  t.after(h.close); h.mount(); await flush()
  h.onPageCheck(['index.home', 'api', 'api.case', 'api.info'], { checked: true, node: { key: 'api' } })
  assert.deepEqual(h.endpointOverrides.value, { [shared]: 'endpoint_allow', [caseOnly]: 'endpoint_allow', [infoOnly]: 'endpoint_allow' })
  h.onPageCheck(['index.home', 'api.info'], { checked: false, node: { key: 'api.case' } })
  assert.equal(h.endpointOverrides.value[shared], 'endpoint_allow')
  assert.equal(h.endpointOverrides.value[caseOnly], 'endpoint_deny')
  assert.equal(h.endpointOverrides.value[infoOnly], 'endpoint_allow')
  h.onEndpointChange(infoOnly, 'endpoint_deny')
  assert.equal(h.endpointOverrides.value[infoOnly], 'endpoint_deny')
  h.onPageCheck(['index.home', 'api', 'api.case', 'api.info'], { checked: true, node: { key: 'api' } })
  assert.equal(h.endpointOverrides.value[caseOnly], 'endpoint_allow')
  assert.equal(h.endpointOverrides.value[infoOnly], 'endpoint_allow')
  h.onPageCheck(['index.home'], { checked: false, node: { key: 'api' } })
  assert.equal(h.endpointOverrides.value[shared], 'endpoint_deny')
  assert.equal(h.endpointOverrides.value[caseOnly], 'endpoint_deny')
  assert.equal(h.endpointOverrides.value[infoOnly], 'endpoint_deny')
})

test('parent clicks expand one branch at a time without selecting a group or changing grants', async t => {
  const h = setupRolePage({ getUserRolePermission: async () => roleOk({ ...permissionFixture(), tree: [
    { permissionKey: 'index.home', children: [] },
    { permissionKey: 'api', children: [{ permissionKey: 'api.case', children: [] }] },
    { permissionKey: 'ui', children: [{ permissionKey: 'ui.case', children: [] }] },
  ] }) })
  t.after(h.close); h.mount(); await flush()
  const checked = [...h.permissionPanel.checkedKeys]
  h.onPageExpand(['api'], { expanded: true, node: { key: 'api' } })
  h.onPageSelect(['api'])
  assert.deepEqual(h.permissionPanel.expandedKeys, ['api'])
  assert.deepEqual(h.permissionPanel.selectedKeys, ['index.home'])
  h.onPageExpand(['api', 'ui'], { expanded: true, node: { key: 'ui' } })
  assert.deepEqual(h.permissionPanel.expandedKeys, ['ui'])
  h.onPageSelect(['ui.case'])
  assert.deepEqual(h.permissionPanel.selectedKeys, ['ui.case'])
  h.expandPermissionTree(true)
  assert.deepEqual(h.permissionPanel.expandedKeys, ['ui'])
  h.onPageExpand([], { expanded: false, node: { key: 'ui' } })
  assert.deepEqual(h.permissionPanel.expandedKeys, [])
  assert.deepEqual(h.permissionPanel.checkedKeys, checked)
  assert.deepEqual(h.endpointOverrides.value, {})
})
