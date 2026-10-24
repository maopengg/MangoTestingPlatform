import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'

const root = path.resolve(import.meta.dirname, '../../..')
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8')

const workbenchSource = read('src/components/business/ProjectProductNavigationWorkbench.vue')
const tableBodySource = read('src/components/table/TableBody.vue')
const tableTabsSource = read('src/components/table/TableTabs.vue')
const globalStyleSource = read('src/styles/index.css')
const apiInfoSource = read('src/views/apitest/info/index.vue')
const functionalListSource = read('src/views/functional-test/suite/index.vue')
const functionalDetailSource = read('src/views/functional-test/suite/details/index.vue')

const collectVueFiles = (directory) =>
  fs.readdirSync(path.join(root, directory), { withFileTypes: true }).flatMap((entry) => {
    const relativePath = path.join(directory, entry.name)
    if (entry.isDirectory()) return collectVueFiles(relativePath)
    return entry.isFile() && entry.name.endsWith('.vue') ? [relativePath] : []
  })

test('project navigation workbench keeps horizontal overflow inside its table body', () => {
  assert.doesNotMatch(workbenchSource, /mango-workbench-scroll-x/)
  assert.doesNotMatch(workbenchSource, /--mango-workbench-min-width|minmax\(830px/)
  assert.match(workbenchSource, /grid-template-columns:\s*240px\s+minmax\(0,\s*1fr\);/)
  assert.match(
    workbenchSource,
    /mango-project-navigation-workbench__body[^{]*\{[^}]*overflow-x:\s*hidden;[^}]*overflow-y:\s*auto;/s
  )
})

test('tabs stay fixed while table content owns horizontal scrolling', () => {
  assert.match(tableTabsSource, /mango-table-tabs mango-tabs-nav-only/)
  assert.match(tableTabsSource, /mango-table-tabs[^{]*\{[^}]*overflow:\s*hidden;/s)
  assert.match(
    workbenchSource,
    /v-if="\$slots\.tabs"[^>]*mango-project-navigation-workbench__tabs[\s\S]*?<slot name="tabs"/
  )
  assert.match(
    workbenchSource,
    /mango-project-navigation-workbench__tabs[^{]*\{[^}]*flex:\s*none;[^}]*overflow:\s*hidden;/s
  )
  assert.match(apiInfoSource, /<template #tabs>[\s\S]*?<a-tabs/)
  assert.match(apiInfoSource, /mango-api-info-tabs mango-tabs-nav-only/)
  assert.doesNotMatch(apiInfoSource, /mango-api-info-content-panel/)
  assert.match(apiInfoSource, /mango-api-info-tabs[^{]*\{[^}]*overflow:\s*hidden;/s)
  assert.match(apiInfoSource, /mango-api-info-table-region[^{]*\{[^}]*overflow:\s*hidden;/s)
  assert.match(apiInfoSource, /<StickyHorizontalTable :scroll-x="2090">/)
  assert.match(apiInfoSource, /<a-table[\s\S]*?:scroll="\{\s*x:\s*2090\s*\}"/)
})

test('navigation-only tabs use compact content padding without affecting content tabs', () => {
  assert.match(
    globalStyleSource,
    /\.mango-tabs-nav-only \.arco-tabs-content\s*\{[^}]*padding-top:\s*1px;/s
  )
  assert.doesNotMatch(
    globalStyleSource,
    /(?:^|\n)\.arco-tabs-content\s*\{[^}]*padding-top:\s*1px;/s
  )
})

test('navigation-only table toolbars always use the shared TableTabs component', () => {
  for (const file of collectVueFiles('src/views')) {
    const source = read(file)
    const rawTabBlocks = source.matchAll(/<a-tabs(?:\s[^>]*)?>([\s\S]*?)<\/a-tabs>/g)
    for (const block of rawTabBlocks) {
      assert.match(
        block[1],
        /<a-tab-pane\b/,
        `${file} contains a navigation-only raw a-tabs block; use TableTabs instead`
      )
    }
  }
})

test('global table tabs stay visible in every main content scroll container', () => {
  assert.match(
    tableTabsSource,
    /mango-table-tabs[^{]*\{[^}]*position:\s*sticky;[^}]*top:\s*0;[^}]*background:\s*var\(--m-surface\);/s
  )
  assert.match(tableBodySource, /mango-table-body__content[^{]*\{[^}]*overflow-y:\s*auto;/s)
  assert.match(tableBodySource, /mango-table-body__footer[^{]*\{[^}]*flex:\s*none;/s)
})

test('shared table body exposes sticky horizontal scrolling as an opt-out capability', () => {
  assert.match(tableBodySource, /stickyHorizontalScroll/)
  assert.match(tableBodySource, /mango-table-body__content--sticky-horizontal-scroll/)
  assert.match(apiInfoSource, /:sticky-horizontal-scroll="false"/)
})

test('all table scrollbars use the shared Arco table theme', () => {
  assert.match(
    globalStyleSource,
    /\.arco-table \.arco-scrollbar-thumb-bar[^{]*\{[^}]*background:\s*var\(--m-scrollbar-thumb\);/s
  )
  assert.match(
    globalStyleSource,
    /\.arco-table \.arco-scrollbar-thumb-direction-horizontal \.arco-scrollbar-thumb-bar[^{]*\{[^}]*height:\s*6px;/s
  )
  for (const source of [functionalListSource, functionalDetailSource]) {
    assert.doesNotMatch(source, /@wheel="onHorizontalTableWheel/)
    assert.doesNotMatch(source, /:deep\(\.arco-(?:table-content|scrollbar-container)[^)]*\)::-/)
    assert.doesNotMatch(source, /mango-functional-scroll-table[^{]*\{[^}]*overflow-x:\s*auto;/s)
  }
})
