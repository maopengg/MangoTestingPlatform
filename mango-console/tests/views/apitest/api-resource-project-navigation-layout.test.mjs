import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'

const root = path.resolve(import.meta.dirname, '../../..')
const pages = ['public', 'auth-config', 'headers']
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8')

for (const page of pages) {
  test(`${page} uses the shared project navigation workbench`, () => {
    const source = read(`src/views/apitest/${page}/index.vue`)
    assert.match(source, /<TableBody[^>]*plain[^>]*class="mango-api-resource-page/)
    assert.match(source, /<ProjectProductNavigationWorkbench/)
    assert.match(source, /<template #search>/)
    assert.match(source, /<template #toolbar>/)
    assert.match(source, /<template #footer>[\s\S]*?<TableFooter/)
    assert.match(source, /headerConditionItems/)
    assert.match(source, /item\.key !== 'project_product'/)
    assert.match(source, /sidebarResetKey/)
  })

}

test('navigation sidebar can operate without module APIs on resource pages', () => {
  const source = read('src/components/business/ProjectProductNavigationSidebar.vue')
  assert.match(source, /showModules/)
  assert.match(source, /搜索项目或产品/)
  assert.match(source, /buildProjectProductFilterTree/)
  assert.match(source, /filterProjectProductOptions/)
})

test('resource filters place search actions inside the shared search panel', () => {
  const source = read('src/components/business/ApiResourceSearchFilters.vue')
  assert.match(source, /@keyup\.enter="emit\('search'\)"/)
  assert.match(source, /@clear="emit\('search'\)"/)
  const workbench = read('src/components/business/ProjectProductNavigationWorkbench.vue')
  assert.match(workbench, /<TableSearchPanel/)
})
