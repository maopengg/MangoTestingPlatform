import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const read = (relativePath) =>
  fs.readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')

const casePageSource = read('../../../../src/views/apitest/case/index.vue')
const infoPageSource = read('../../../../src/views/apitest/info/index.vue')
const workbenchSource = read('../../../../src/components/business/ProjectProductNavigationWorkbench.vue')
const sidebarSource = read('../../../../src/components/business/ProjectProductNavigationSidebar.vue')

test('API case and info pages use the shared product navigation workbench', () => {
  for (const source of [casePageSource, infoPageSource]) {
    assert.match(source, /<ProjectProductNavigationWorkbench/)
    assert.match(source, /:reset-key="sidebarResetKey"/)
    assert.match(source, /<template #footer>[\s\S]*?<TableFooter/)
  }
  assert.match(workbenchSource, /<ProjectProductNavigationSidebar/)
  assert.match(workbenchSource, /mango-project-navigation-workbench__body/)
})

test('wide API tables use the shared sticky horizontal table boundary', () => {
  assert.match(casePageSource, /:sticky-horizontal-scroll="false"/)
  const scrollWidth = casePageSource.match(/<StickyHorizontalTable :scroll-x="(\d+)">/)[1]
  assert.ok(Number(scrollWidth) >= 2340)
  assert.match(casePageSource, new RegExp(`:scroll="\\{ x: ${scrollWidth}, y: '100%' \\}"`))
  assert.match(infoPageSource, /:sticky-horizontal-scroll="false"/)
  assert.match(infoPageSource, /<StickyHorizontalTable :scroll-x="2090">/)
})

test('shared navigation supports project, product and module filtering', () => {
  assert.match(sidebarSource, /搜索项目、产品或模块/)
  assert.match(sidebarSource, /buildAllProductModuleFilterTree/)
  assert.match(sidebarSource, /selectedTreeKey/)
  assert.match(sidebarSource, /resetKey/)
  assert.match(sidebarSource, /expandedKeys\.value = \[\]/)
})

test('API case request combines product and module navigation filters', () => {
  assert.match(casePageSource, /module__in/)
  assert.match(casePageSource, /sidebarModuleIds/)
  assert.match(casePageSource, /getApiCase\(value\)/)
})
