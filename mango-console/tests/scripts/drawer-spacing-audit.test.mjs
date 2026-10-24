import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { auditDrawerSpacing, inspectDrawerSpacing } from '../../scripts/drawer-spacing-audit.mjs'

test('action panels reject duplicate root padding, including default slots and breakpoints', () => {
  const result = inspectDrawerSpacing(`<template><BaseSidePanel><template #default>
    <div class="mango-form"><section class="mango-card" /></div>
  </template></BaseSidePanel></template><style>
  .mango-form { padding: 0; } @media (max-width: 900px) { .mango-form { padding: 12px; } }
  .mango-card { padding: 10px; }
  </style>`)
  assert.equal(result.issues.length, 1)
})

test('page panels and internal card/footer padding are not mistaken for action root padding', () => {
  assert.deepEqual(inspectDrawerSpacing(`<template>
    <BaseSidePanel mode="page"><div class="mango-page" /></BaseSidePanel>
    <BaseSidePanel><div class="mango-form"><div class="mango-card" /></div>
      <template #footer-buttons><div class="mango-footer" /></template>
    </BaseSidePanel>
    </template><style>.mango-page { padding: 8px; } .mango-form { padding: 0; }
    .mango-card { padding: 10px; } .mango-footer { padding: 10px; }</style>`).issues, [])
})

test('global and side panel shells own exactly one outer inset', () => {
  const css = readFileSync('src/styles/index.css', 'utf8')
  assert.match(css, /\.arco-drawer-body\s*\{[^}]*padding: var\(--m-page-gap\)/)
  assert.match(css, /\.arco-drawer-header,\s*\.arco-drawer-footer\s*\{\s*padding: var\(--m-card-padding\) var\(--m-page-gap\)/)
  const panel = readFileSync('src/components/overlays/BaseSidePanel.vue', 'utf8')
  assert.match(panel, /body-class="mango-side-panel-body"/)
  assert.match(panel, /:global\(\.mango-side-panel-body\)\s*\{[^}]*padding: 0/)
  assert.match(panel, /\.mango-side-panel-content\s*\{[^}]*box-sizing: border-box;[^}]*padding: var\(--m-page-gap\)/)
  assert.doesNotMatch(panel, /:deep\(\.arco-drawer-body\)/)
})

test('all action side panels have no unexplained duplicate outer inset', () => {
  const result = auditDrawerSpacing()
  assert.ok(result.scanned > 200)
  assert.ok(result.drawers > 40 && result.sidePanels > 30)
  assert.deepEqual(result.issues, [])
})
