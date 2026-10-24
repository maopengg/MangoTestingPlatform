import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = fs.readFileSync(
  new URL('../src/views/system/role/index.vue', import.meta.url),
  'utf8'
)
const start = source.indexOf('  function collectTreeKeys(')
const end = source.indexOf('  function onSavePermission(', start)
assert.ok(start > 0 && end > start)
const js = ts.transpileModule(source.slice(start, end), {}).outputText

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
              { permissionKey: 'system.role:create' },
              { permissionKey: 'system.role:delete' },
            ],
            children: [],
          },
          {
            key: 'system.user',
            actions: [{ permissionKey: 'system.user:edit' }],
            children: [],
          },
          { key: 'system.readonly', actions: [], children: [] },
        ],
      },
      {
        key: 'report',
        actions: [{ permissionKey: 'report:export' }],
        children: [],
      },
    ],
  }
  const handlers = new Function(
    'permissionPanel',
    'isSelectedGuestRole',
    'homePermissionKey',
    `${js}; return { onPageCheck, onActionCheck };`
  )(permissionPanel, { value: guest }, 'index.home')
  return { permissionPanel, ...handlers }
}

function assertKeys(state, expected) {
  assert.deepEqual([...state.permissionPanel.checkedKeys].sort(), [...expected].sort())
}

const systemPages = ['system', 'system.role', 'system.user', 'system.readonly']
const systemActions = ['system.role:create', 'system.role:delete', 'system.user:edit']

test('checking a first-level page selects every child page action and keeps existing permissions', () => {
  const state = createPermissionState(['index.home', 'report', 'report:export', 'system.role'])
  state.onPageCheck(['index.home', 'report', ...systemPages], {
    checked: true,
    node: { key: 'system' },
  })
  assertKeys(state, ['index.home', 'report', 'report:export', ...systemPages, ...systemActions])
})

test('checking a second-level page keeps a sibling action manually unchecked', () => {
  const state = createPermissionState(['index.home', ...systemPages, ...systemActions])
  state.onActionCheck('system.role:delete', false)
  state.onPageCheck(['index.home', 'system.role', 'system.readonly'], {
    checked: false,
    node: { key: 'system.user' },
  })
  state.onPageCheck(['index.home', ...systemPages], {
    checked: true,
    node: { key: 'system.user' },
  })
  assertKeys(state, ['index.home', ...systemPages, 'system.role:create', 'system.user:edit'])
})

test('checking a page again restores all its actions without duplicate keys', () => {
  const state = createPermissionState(['index.home', ...systemPages, ...systemActions])
  state.onActionCheck('system.role:delete', false)
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
    'report:export',
  ])
  state.onPageCheck(['index.home', 'report'], { checked: false, node: { key: 'system' } })
  assertKeys(state, ['index.home', 'report', 'report:export'])
})

test('a page without actions can be checked and home remains selected', () => {
  const state = createPermissionState()
  state.onPageCheck(['system.readonly'], { checked: true, node: { key: 'system.readonly' } })
  assertKeys(state, ['index.home', 'system.readonly'])
})

test('updates without an event select new page actions and clear removed page actions', () => {
  const state = createPermissionState(['index.home', 'report', 'report:export'])
  state.onPageCheck(['index.home', ...systemPages])
  assertKeys(state, ['index.home', ...systemPages, ...systemActions])
  state.onActionCheck('system.role:delete', false)
  state.onPageCheck(['index.home', ...systemPages, 'report'])
  assertKeys(state, [
    'index.home',
    ...systemPages,
    'system.role:create',
    'system.user:edit',
    'report',
    'report:export',
  ])
})

test('guest permissions stay read-only for both page and action checks', () => {
  const state = createPermissionState(['index.home'], true)
  state.onPageCheck(['index.home', ...systemPages], {
    checked: true,
    node: { key: 'system' },
  })
  state.onActionCheck('system.role:create', true)
  assertKeys(state, ['index.home'])
})
