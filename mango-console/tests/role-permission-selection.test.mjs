import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = fs.readFileSync(
  new URL('../src/views/system/role/index.vue', import.meta.url),
  'utf8'
)
const start = source.indexOf('  function expandPermissionTree(')
const end = source.indexOf('  async function refreshOwnRoutes(', start)
assert.ok(start > 0 && end > start)
const js = ts.transpileModule(source.slice(start, end), {}).outputText
const helpers = {}
new Function('exports', ts.transpileModule(fs.readFileSync(new URL('../src/views/system/role/role-permissions.ts', import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText)(helpers)

function createPermissionState(checkedKeys = ['index.home'], guest = false) {
  const permissionPanel = {
    checkedKeys: [...checkedKeys],
    treeData: [
      { key: 'index.home', actions: [], children: [] },
      {
        key: 'system',
        actions: [],
        children: [
          {
            key: 'system.role',
            actions: [
              { permissionKey: 'system.role:add' },
              { permissionKey: 'system.role:remove' },
            ],
            children: [],
          },
          {
            key: 'system.user',
            actions: [{ permissionKey: 'system.user:change' }],
            children: [],
          },
          { key: 'system.readonly', actions: [], children: [] },
        ],
      },
      {
        key: 'report',
        actions: [{ permissionKey: 'report:read' }],
        children: [],
      },
    ],
  }
  const handlers = new Function(
    'permissionPanel',
    'isPermissionReadonly',
    'homePermissionKey',
    'available',
    ...Object.keys(helpers).filter(key => key !== 'homePermissionKey'),
    `${js}; return { onPageCheck, onActionCheck };`
  )(permissionPanel, { value: guest }, 'index.home', () => true, ...Object.entries(helpers).filter(([key]) => key !== 'homePermissionKey').map(([, value]) => value))
  return { permissionPanel, ...handlers }
}

function assertKeys(state, expected) {
  assert.deepEqual([...state.permissionPanel.checkedKeys].sort(), [...expected].sort())
}

const systemPages = ['system', 'system.role', 'system.user', 'system.readonly']
const systemActions = ['system.role:add', 'system.role:remove', 'system.user:change']

test('checking a first-level page selects every child page action and keeps existing permissions', () => {
  const state = createPermissionState(['index.home', 'report', 'report:read', 'system.role'])
  state.onPageCheck(['index.home', 'report', ...systemPages], {
    checked: true,
    node: { key: 'system' },
  })
  assertKeys(state, ['index.home', 'report', 'report:read', ...systemPages, ...systemActions])
})

test('checking a second-level page keeps a sibling action manually unchecked', () => {
  const state = createPermissionState(['index.home', ...systemPages, ...systemActions])
  state.onActionCheck('system.role:remove', false)
  state.onPageCheck(['index.home', 'system.role', 'system.readonly'], {
    checked: false,
    node: { key: 'system.user' },
  })
  state.onPageCheck(['index.home', ...systemPages], {
    checked: true,
    node: { key: 'system.user' },
  })
  assertKeys(state, ['index.home', ...systemPages, 'system.role:add', 'system.user:change'])
})

test('checking a page again restores all its actions without duplicate keys', () => {
  const state = createPermissionState(['index.home', ...systemPages, ...systemActions])
  state.onActionCheck('system.role:remove', false)
  state.onPageCheck(['index.home', ...systemPages], {
    checked: true,
    node: { key: 'system' },
  })
  assertKeys(state, ['index.home', ...systemPages, ...systemActions])
})

test('unchecking a first-level page removes its child actions and keeps other pages', () => {
  const state = createPermissionState([
    'index.home',
    ...systemPages,
    ...systemActions,
    'report',
    'report:read',
  ])
  state.onPageCheck(['index.home', 'report'], { checked: false, node: { key: 'system' } })
  assertKeys(state, ['index.home', 'report', 'report:read'])
})

test('a page without actions can be checked and home remains selected', () => {
  const state = createPermissionState()
  state.onPageCheck(['system.readonly'], { checked: true, node: { key: 'system.readonly' } })
  assertKeys(state, ['index.home', 'system.readonly'])
})

test('updates without an event select new page actions and clear removed page actions', () => {
  const state = createPermissionState(['index.home', 'report', 'report:read'])
  state.onPageCheck(['index.home', ...systemPages])
  assertKeys(state, ['index.home', ...systemPages, ...systemActions])
  state.onActionCheck('system.role:remove', false)
  state.onPageCheck(['index.home', ...systemPages, 'report'])
  assertKeys(state, [
    'index.home',
    ...systemPages,
    'system.role:add',
    'system.user:change',
    'report',
    'report:read',
  ])
})

test('guest permissions stay read-only for both page and action checks', () => {
  const state = createPermissionState(['index.home'], true)
  state.onPageCheck(['index.home', ...systemPages], {
    checked: true,
    node: { key: 'system' },
  })
  state.onActionCheck('system.role:add', true)
  assertKeys(state, ['index.home'])
})
