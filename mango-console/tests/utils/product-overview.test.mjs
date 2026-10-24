import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const exports = {}
new Function('exports', ts.transpileModule(readFileSync('src/views/config/product/overview.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText)(exports)
const { loadAllProducts, groupProducts } = exports
const projects = [{ key: null, title: '选择项目' }, { key: 1, title: '项目甲' }, { key: 2, title: '项目乙' }, { key: 3, title: '空项目' }]
const products = [
  { id: 3, name: '移动端', project: { id: 1, name: '项目甲' }, owners: [{ id: 7 }], ui_client_type: 0, api_client_type: 1 },
  { id: 2, name: '控制台', project: { id: 2, name: '项目乙' }, owners: [{ id: 8 }], ui_client_type: 1, api_client_type: 0 },
  { id: 1, name: '开放平台', project: { id: 1, name: '项目甲' }, owners: [{ id: 8 }], ui_client_type: 0, api_client_type: 0 },
]

test('loads every page even if the server caps pages below the requested size', async () => {
  const calls = []
  const rows = await loadAllProducts(async params => {
    calls.push(params)
    return { data: products.slice(params.page - 1, params.page), totalSize: 3 }
  })
  assert.equal(rows.length, 3)
  assert.deepEqual(calls.map(call => call.page), [1, 2, 3])
  assert.ok(calls.every(call => call.pageSize === 100 && !('size' in call)))
})

test('empty results, stale responses and failed/incomplete pages never publish partial results', async () => {
  assert.deepEqual(await loadAllProducts(async () => ({ data: [], totalSize: 0 })), [])
  let current = true
  assert.deepEqual(await loadAllProducts(async () => { current = false; return { data: products, totalSize: 3 } }, () => current), [])
  await assert.rejects(loadAllProducts(async ({ page }) => ({ data: page === 1 ? products.slice(0, 1) : [], totalSize: 3 })))
  await assert.rejects(loadAllProducts(async () => { throw new Error('example failure') }))
})

test('groups interleaved products by project, retains empty projects and matches names', () => {
  const groups = groupProducts(products, projects, [])
  assert.equal(groups.length, 3)
  assert.equal(groups.find(group => group.id === '1').products.length, 2)
  assert.equal(groups.find(group => group.id === '3').total, 0)
  assert.equal(groupProducts(products, projects, [{ key: 'keyword', value: '项目甲' }])[0].products.length, 2)
  const matched = groupProducts(products, projects, [{ key: 'keyword', value: '开放' }])
  assert.equal(matched[0].products.length, 1)
  assert.equal(matched[0].total, 2)
  assert.equal(groupProducts(products, projects, [{ key: 'keyword', value: '空项目' }])[0].total, 0)
})

test('multi-select filters support zero values, owners and comma separated ids', () => {
  const groups = groupProducts(products, projects, [
    { key: 'owners', value: [7, 8] }, { key: 'ui_client_type', value: [0] }, { key: 'id', value: '1,3' },
  ])
  assert.deepEqual(groups[0].products.map(row => row.id).sort(), [1, 3])
  assert.deepEqual(groupProducts(products, projects, [{ key: 'owners', value: [999] }]), [])
})

test('overview, CRUD form and navigation workbench compile', () => {
  for (const filename of ['src/views/config/product/index.vue', 'src/views/config/product/components/ProductOverview.vue', 'src/components/business/ProjectProductNavigationWorkbench.vue']) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: 'product-overview' })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'product-overview',
      compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  }
})

test('overview keeps explicit operation permissions and project-aware create flow', () => {
  const component = readFileSync('src/views/config/product/components/ProductOverview.vue', 'utf8')
  const page = readFileSync('src/views/config/product/index.vue', 'utf8')
  for (const operation of ['create', 'detail', 'edit', 'delete']) {
    assert.ok(component.includes(`config.product:${operation}`))
  }
  assert.match(component, /danger: true/)
  assert.doesNotMatch(component, /emit\('add', group.id\)/)
  assert.equal((component.match(/>新增产品<\/a-button/g) || []).length, 1)
  assert.match(component, /scrollIntoView/)
  assert.match(component, /collapsed.value = \[\]/)
  assert.match(page, /function onAdd\(projectId\?: string\)/)
  assert.match(page, /projectField.value = productProjectOptions.value.find/)
  assert.match(page, /loadAllProducts\(getUserProduct/)
  assert.doesNotMatch(page, /usePagination|<TableFooter/)
})

test('audit columns are always visible and the normal toolbar only keeps create', () => {
  const component = readFileSync('src/views/config/product/components/ProductOverview.vue', 'utf8')
  const config = readFileSync('src/views/config/product/config.ts', 'utf8')
  const toolbar = component.split('<template #toolbar>')[1].split('</template>')[0]
  assert.doesNotMatch(toolbar, /matchedCount|显示审计字段|全部展开|全部收起|刷新/)
  assert.doesNotMatch(component, /showAudit|visibleColumns/)
  assert.match(component, /v-for="item in tableColumns"/)
  for (const field of ['index', 'update_user', 'update_time']) {
    assert.ok(component.includes(field) || config.includes(field))
  }
  assert.match(config, /key: 'actions',[\s\S]*?align: 'center',[\s\S]*?fixed: 'right',[\s\S]*?width: 160/)
  const nameColumn = config.split("title: '产品名称'")[1].split('},')[0]
  assert.doesNotMatch(nameColumn, /width:/)
})
