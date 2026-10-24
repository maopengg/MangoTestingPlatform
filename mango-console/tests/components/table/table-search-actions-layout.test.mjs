import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'

const root = path.resolve(import.meta.dirname, '../../..')
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8')

const actionsSource = read('src/components/table/TableSearchActions.vue')
const headerSource = read('src/components/table/TableHeader.vue')
const caseFiltersSource = read('src/views/apitest/case/ApiCaseSearchFilters.vue')
const casePageSource = read('src/views/apitest/case/index.vue')
const tableTabsSource = read('src/components/table/TableTabs.vue')
const searchPanelSource = read('src/components/table/TableSearchPanel.vue')
const navigationWorkbenchSource = read(
  'src/components/business/ProjectProductNavigationWorkbench.vue'
)
const navigationSidebarSource = read('src/components/business/ProjectProductNavigationSidebar.vue')
const infoFiltersSource = read('src/views/apitest/info/ApiInfoSearchFilters.vue')
const resourceFiltersSource = read('src/components/business/ApiResourceSearchFilters.vue')
const functionalTestSource = read('src/views/functional-test/suite/index.vue')

const collectVueFiles = (directory) =>
  fs.readdirSync(path.join(root, directory), { withFileTypes: true }).flatMap((entry) => {
    const relativePath = path.join(directory, entry.name)
    if (entry.isDirectory()) return collectVueFiles(relativePath)
    return entry.isFile() && entry.name === 'index.vue' ? [relativePath] : []
  })

test('table search actions occupy the last cell of the first responsive grid row', () => {
  assert.match(actionsSource, /class="mango-table-search-actions"/)
  assert.match(actionsSource, /justify-content:\s*flex-end;/)
  assert.match(
    searchPanelSource,
    /grid-template-columns:\s*repeat\(\s*var\(--mango-table-search-column-count\),\s*var\(--mango-table-search-cell-width\)\s*\);/s
  )
  assert.match(searchPanelSource, /width:\s*100%;/)
  assert.match(searchPanelSource, /const MIN_CELL_WIDTH = 210/)
  assert.match(searchPanelSource, /const MAX_CELL_WIDTH = 250/)
  assert.match(searchPanelSource, /const BASE_GAP = 8/)
  assert.match(searchPanelSource, /new ResizeObserver/)
  assert.match(searchPanelSource, /column-gap:\s*var\(--mango-table-search-column-gap\);/)
  assert.match(searchPanelSource, /row-gap:\s*8px;/)
  assert.doesNotMatch(searchPanelSource, /justify-content:\s*space-between;/)
  assert.match(searchPanelSource, /display:\s*contents\s*!important;/)
  assert.doesNotMatch(searchPanelSource, /mango-table-search-panel__content::after/)
  assert.match(
    searchPanelSource,
    /mango-table-search-actions\)[^{]*\{[^}]*grid-row:\s*1;[^}]*grid-column:\s*-2\s*\/\s*-1;[^}]*width:\s*var\(--mango-table-search-cell-width\);[^}]*justify-content:\s*flex-end;/s
  )
})

test('normal table search controls use fixed global dimensions', () => {
  assert.match(headerSource, /--table-filter-label-width:\s*70px;/)
  assert.match(headerSource, /--table-filter-control-width:\s*160px;/)
  assert.match(headerSource, /--table-filter-item-width:\s*230px;/)
  assert.match(headerSource, /flex:\s*0\s+0\s+var\(--table-filter-control-width\)\s*!important;/)
  assert.match(
    headerSource,
    /arco-form-item-content\s*>\s*:first-child\)[^{]*\{[^}]*flex:\s*0\s+0\s+var\(--table-filter-control-width\)\s*!important;[^}]*width:\s*var\(--table-filter-control-width\)\s*!important;[^}]*max-width:\s*var\(--table-filter-control-width\)\s*!important;/s
  )
  assert.match(
    headerSource,
    /arco-form-inline\s+\.arco-input-tag\)[^{]*\{[^}]*flex:\s*0\s+0\s+var\(--table-filter-control-width\)\s*!important;[^}]*width:\s*var\(--table-filter-control-width\)\s*!important;[^}]*max-width:\s*var\(--table-filter-control-width\)\s*!important;/s
  )
})

test('API case search receives shared actions from the navigation workbench', () => {
  assert.match(casePageSource, /<ProjectProductNavigationWorkbench/)
  assert.match(casePageSource, /<template #search>/)
  assert.doesNotMatch(caseFiltersSource, /TableSearchActions/)
  assert.match(headerSource, /showSearchActions:\s*\{[^}]*default:\s*true/s)
  assert.match(headerSource, /showDefaultSearchActions/)
})

test('all project navigation pages receive the shared search actions', () => {
  const navigationPages = collectVueFiles('src/views').filter((file) => {
    const source = read(file)
    return /ProjectProductNavigation(?:Workbench|Sidebar)/.test(source)
  })
  assert.equal(navigationPages.length, 21)
  for (const page of navigationPages) {
    const source = read(page)
    assert.match(source, /ProjectProductNavigationWorkbench/)
    assert.doesNotMatch(source, /ProjectProductNavigationSidebar/)
  }
  assert.match(navigationWorkbenchSource, /<TableSearchPanel/)
  assert.match(searchPanelSource, /<TableSearchActions[^>]*@search[^>]*@reset/)
  assert.match(searchPanelSource, /:show-search-actions="false"/)

  for (const page of ['info', 'case', 'public', 'auth-config', 'headers']) {
    const source = read(`src/views/apitest/${page}/index.vue`)
    assert.match(source, /<ProjectProductNavigationWorkbench/)
  }
  assert.doesNotMatch(infoFiltersSource, /TableSearchActions|search-filters__actions/)
  assert.doesNotMatch(resourceFiltersSource, /TableSearchActions|search-filters__actions/)
  assert.doesNotMatch(functionalTestSource, /mango-functional-case-filter|TableSearchActions/)
  assert.match(functionalTestSource, /<template #search>[\s\S]*v-else :model="caseFilter"/)
  assert.match(
    functionalTestSource,
    /<template #toolbar>[\s\S]*data-testid="qa-views-functional-test-suite-button-导出"[\s\S]*<\/template>/
  )
})

test('project navigation sidebar omits project and product statistics', () => {
  assert.doesNotMatch(navigationSidebarSource, /projectCount|productCount/)
  assert.doesNotMatch(navigationSidebarSource, /mango-project-navigation-sidebar__stats/)
  assert.doesNotMatch(navigationSidebarSource, /mango-project-navigation-sidebar__count/)
})

test('shared tabs and API case toolbar keep the global action spacing', () => {
  assert.match(
    tableTabsSource,
    /\.mango-table-tabs__actions\s*\{[^}]*height:\s*40px;[^}]*align-items:\s*center;/s
  )
  assert.match(
    tableTabsSource,
    /\.mango-table-tabs\s+:deep\(\.arco-tabs-nav-extra\)\s*\{[^}]*height:\s*40px;[^}]*align-items:\s*center;[^}]*padding-right:\s*var\(--m-page-gap\);/s
  )
  assert.match(navigationWorkbenchSource, /<TableTabs[^>]*>[\s\S]*<slot name="toolbar"/)
  assert.match(casePageSource, /<template #toolbar>[\s\S]*qa-views-apitest-case-button-批量删除/)
})
