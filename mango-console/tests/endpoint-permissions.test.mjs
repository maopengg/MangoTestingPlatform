import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'
import { setupRolePage, roleOk, permissionFixture } from './helpers/role-page-harness.mjs'

const id = `http.${'a'.repeat(64)}`
const endpoint = { id, protocol: 'http', method: 'GET', name: 'get', description: '查询用例', urls: ['/api/api/case'], fixed: false, fixed_enabled: false, fixed_reason: '' }
const fixture = (overrides = {}) => ({ ...permissionFixture(), endpoint_groups: [{ menu_key: 'api.case', endpoints: [endpoint] }], endpoint_permissions: overrides })
test('interface payload validation only accepts explicit allow and deny', t => {
  const h = setupRolePage(); t.after(h.close)
  const m = h.load('endpoint-permissions.ts')
  assert.deepEqual(m.parseEndpointPermissions(fixture().endpoint_groups, { [id]: 'endpoint_deny' }).overrides, { [id]: 'endpoint_deny' })
  for (const overrides of [null, [], { [id]: 'inherit' }, { invalid: 'endpoint_allow' }]) assert.throws(() => m.parseEndpointPermissions([], overrides))
  assert.throws(() => m.parseEndpointPermissions([{ menu_key: 'api.case', endpoints: [{ ...endpoint, fixed: 'false' }] }], {}))
})
test('switching roles clears overrides and stale responses cannot restore a previous role grant', async t => {
  const first = deferred(), second = deferred()
  const h = setupRolePage({ getUserRolePermission: id => id === 1 ? first.promise : second.promise }); t.after(h.close)
  h.mount(); await flush()
  const select = h.onSelectRole({ id: 2, name: 'Other', description: '' })
  second.resolve(roleOk(fixture({ [id]: 'endpoint_deny' }))); await select
  first.resolve(roleOk(fixture({ [id]: 'endpoint_allow' }))); await flush()
  assert.deepEqual(h.endpointOverrides.value, { [id]: 'endpoint_deny' })
  await h.visibility('hidden')
  assert.deepEqual(h.endpointOverrides.value, {})
  assert.deepEqual(h.endpointGroups.value, [])
})
test('interface permissions are saved as an immutable snapshot, and deny is explicit', async t => {
  const pending = deferred()
  const h = setupRolePage({ getUserRolePermission: async () => roleOk(fixture()), putUserRolePermission: () => pending.promise }); t.after(h.close)
  h.mount(); await flush()
  h.onEndpointChange(id, 'endpoint_allow')
  h.onEndpointChange(id, 'endpoint_deny')
  const saving = h.onSavePermission()
  h.onEndpointChange(id, 'endpoint_allow')
  assert.deepEqual(h.calls.find(([name]) => name === 'putUserRolePermission')[1].endpoint_permissions, { [id]: 'endpoint_deny' })
  assert.deepEqual(h.endpointOverrides.value, { [id]: 'endpoint_deny' })
  pending.reject({ msg: 'Denied' }); await saving
  assert.deepEqual(h.endpointOverrides.value, { [id]: 'endpoint_deny' })
})
test('advanced interface editor compiles with a bounded table and accessible controls', async () => {
  const filename = path.resolve('src/views/system/role/components/EndpointPermissionEditor.vue')
  const { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'endpoint' })
  assert.deepEqual(compileTemplate({ filename, id: 'endpoint', source: descriptor.template.content, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  assert.deepEqual((await compileStyleAsync({ filename, id: 'endpoint', source: descriptor.styles[0].content, scoped: true })).errors, [])
  assert.match(descriptor.template.content, /<a-switch\b/)
  assert.doesNotMatch(descriptor.template.content, /<a-select\b/)
  assert.doesNotMatch(descriptor.template.content, /<a-switch\b[^>]*\bsize=/)
  assert.doesNotMatch(descriptor.template.content, /value="business"|value="fixed"/)
  assert.match(descriptor.template.content, /record\.description \|\| record\.name/)
  assert.doesNotMatch(descriptor.template.content, /\{\{\s*record\.fixed_reason\s*\}\}/)
  assert.doesNotMatch(descriptor.template.content, /<span v-if="record\.fixed">/)
  assert.match(descriptor.template.content, /record\.fixed \? record\.fixed_enabled/)
})

test('authorization switches emit explicit allow and deny, while readonly ignores changes', t => {
  const h = harness('EndpointPermissionEditor', 'change', {
    base: path.resolve('src/views/system/role'),
    props: { groups: [{ menu_key: 'api.case', endpoints: [endpoint] }], menuKey: 'api.case', permissions: {}, readonly: false },
  })
  t.after(h.close)
  h.change(id, true)
  h.change(id, false)
  assert.deepEqual(h.events, [['change', id, 'endpoint_allow'], ['change', id, 'endpoint_deny']])
  h.props.readonly = true
  h.change(id, true)
  assert.equal(h.events.length, 2)
})

test('fixed interfaces use their registered switch defaults and cannot emit editable changes', t => {
  const fixed = { ...endpoint, fixed: true, fixed_enabled: true }
  const h = harness('EndpointPermissionEditor', 'change', {
    base: path.resolve('src/views/system/role'),
    props: { groups: [{ menu_key: 'config.project', endpoints: [fixed] }],
      menuKey: 'config.project', permissions: { [id]: 'endpoint_deny' }, readonly: false },
  })
  t.after(h.close)
  h.change(id, false)
  assert.deepEqual(h.events, [])
})

test('Other is checked and selectable but its fixed rules cannot be edited or persisted', async t => {
  const fixedKeys = ['__fixed__', '__fixed__.public']
  const data = { ...fixture(), tree: [...fixture().tree,
    { permissionKey: '__fixed__', menuName: '其他', displayOnly: true, children: [
      { permissionKey: '__fixed__.public', menuName: '公开入口', displayOnly: true, children: [] },
    ] }],
  }
  const h = setupRolePage({ getUserRolePermission: async () => roleOk(data),
    putUserRolePermission: async body => roleOk({ menu_keys: body.menu_keys, endpoint_permissions: body.endpoint_permissions }),
  })
  t.after(h.close); h.mount(); await flush()
  const helper = h.load('role-permissions.ts')
  assert.ok(fixedKeys.every(key => h.pageCheckedKeys.value.includes(key)))
  const other = helper.findPermissionNode(h.permissionPanel.treeData, '__fixed__')
  assert.equal(other.disabled, false)
  assert.equal(other.disableCheckbox, true)
  h.onPageSelect(['__fixed__.public'])
  h.onEndpointChange(id, 'endpoint_allow')
  assert.deepEqual(h.endpointOverrides.value, {})
  h.onPageCheck([...h.permissionPanel.checkedKeys, ...fixedKeys])
  assert.ok(fixedKeys.every(key => h.pageCheckedKeys.value.includes(key)))
  await h.onSavePermission()
  const body = h.calls.find(([name]) => name === 'putUserRolePermission')[1]
  assert.ok(body.menu_keys.every(key => !fixedKeys.includes(key)))
  assert.deepEqual(body.endpoint_permissions, {})
})

test('protocol tabs only show available interfaces and switching groups selects a valid protocol', async t => {
  const h = harness('EndpointPermissionEditor', 'protocols,protocol,filtered', {
    base: path.resolve('src/views/system/role'),
    props: { groups: [
      { menu_key: 'api.case', endpoints: [endpoint] },
      { menu_key: '__fixed__.mcp_base', endpoints: [{ ...endpoint, protocol: 'mcp', method: 'MCP', fixed: true, fixed_enabled: true }] },
    ], menuKey: 'api.case', permissions: {}, readonly: false },
  })
  t.after(h.close)
  assert.deepEqual(h.protocols.value, ['http'])
  h.props.menuKey = '__fixed__.mcp_base'
  await flush()
  assert.deepEqual(h.protocols.value, ['mcp'])
  assert.equal(h.protocol.value, 'mcp')
  assert.equal(h.filtered.value.length, 1)
  h.props.menuKey = 'api.case'
  await flush()
  assert.deepEqual(h.protocols.value, ['http'])
  assert.equal(h.protocol.value, 'http')
  assert.equal(h.filtered.value.length, 1)
  h.props.groups = []
  await flush()
  assert.deepEqual(h.protocols.value, [])
  assert.deepEqual(h.filtered.value, [])
})
