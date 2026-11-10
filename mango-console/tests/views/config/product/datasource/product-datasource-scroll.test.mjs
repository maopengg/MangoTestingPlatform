import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import postcss from 'postcss'
import ts from 'typescript'

const filename = new URL(
  '../../../../../src/views/config/product/datasource/index.vue',
  import.meta.url
).pathname
const source = readFileSync(filename, 'utf8')
const { descriptor } = parse(source, { filename })
const css = postcss.parse(descriptor.styles[0].content)
function properties(selector) {
  const result = {}
  css.walkRules(selector, (rule) =>
    rule.walkDecls((decl) => {
      result[decl.prop] = decl.value
    })
  )
  return result
}

test('workbench has a bounded height and outer wrapper only scrolls horizontally', () => {
  const outer = properties('.mango-datasource-workbench-scroll')
  assert.equal(outer['overflow-x'], 'auto')
  assert.equal(outer['overflow-y'], 'hidden')
  const grid = properties('.mango-datasource-workbench')
  assert.equal(grid.height, '100%')
  assert.equal(grid['min-height'], '0')
  assert.equal(grid['grid-template-rows'], 'minmax(0, 1fr)')
})

test('card list has independent scrolling without scrolling the title or right pane', () => {
  const list = properties('.mango-datasource-card-loading')
  assert.equal(list.flex, '1')
  assert.equal(list['min-height'], '0')
  assert.equal(list['overflow-y'], 'auto')
  assert.equal(list['overflow-x'], 'hidden')
  assert.equal(list['overscroll-behavior-y'], 'contain')
  assert.equal(list['scrollbar-gutter'], 'stable')
  assert.match(
    descriptor.template.content,
    /<MangoPanelSpin\s+class="mango-datasource-card-loading mango-native-scrollbar"/
  )
  assert.match(descriptor.template.content, /<\/MangoPanelSpin>\s*<\/section>/)
})

test('datasource page compiles with its script bindings after scroll containment', () => {
  const script = compileScript(descriptor, { id: 'datasource-scroll' })
  assert.deepEqual(
    compileTemplate({
      source: descriptor.template.content,
      filename,
      id: 'datasource-scroll',
      compilerOptions: { bindingMetadata: script.bindings },
    }).errors,
    []
  )
})

test('right pane keeps tab navigation fixed and long content reachable', () => {
  assert.match(descriptor.template.content, /<a-tabs[^>]*class="mango-datasource-detail-tabs">/)
  const tabs = properties('.mango-datasource-detail-tabs')
  assert.equal(tabs.flex, '1')
  assert.equal(tabs['min-height'], '0')
  assert.equal(tabs['flex-direction'], 'column')
  const content = properties(':deep(.arco-tabs-content)')
  assert.equal(content['overflow-y'], 'auto')
  assert.equal(content['min-height'], '0')
})

test('table discovery tab is hidden for unsupported source types and falls back to bindings', () => {
  assert.match(
    descriptor.template.content,
    /<a-tab-pane v-if="supportsDatasourceTables" key="tables"/
  )
  assert.match(source, /const datasource = selectedDatasource.value/)
  assert.match(source, /selectedId.value = record.id/)
  assert.match(source, /if \(!supported\) detailTab.value = 'bindings'/)
  assert.match(descriptor.template.content, /v-model:active-key="detailTab"/)
})

test('table capability accepts MySQL and relational types but excludes Redis and missing values', () => {
  const body = source.match(
    /const supportsDatasourceTables = computed\(\(\) => \{([\s\S]*?)\n  \}\)/
  )[1]
  const supports = new Function('selectedDatasource', body)
  for (const db_type of [0, '0', 1, 2, 3, 4, 20, '20']) {
    assert.equal(supports({ value: { db_type } }), true)
  }
  for (const value of [
    null,
    {},
    { db_type: null },
    { db_type: 10 },
    { db_type: '10' },
    { db_type: 99 },
  ]) {
    assert.equal(supports({ value }), false)
  }
})

test('logical databases are fetched without pagination and stably sorted across all types', () => {
  const request = source.match(/getDataFactoryDatasourceAlias\(\{([\s\S]*?)\}\)/)[1]
  assert.doesNotMatch(request, /pageSize|\bpage\b|db_type|source_category/)
  const config = readFileSync(
    new URL('../../../../../src/views/config/product/datasource/config.ts', import.meta.url),
    'utf8'
  )
  const sortSource = config.slice(
    config.indexOf('export function sortLogicalDatasources'),
    config.indexOf('export const discoveryColumns')
  )
  const compiled = ts.transpileModule(sortSource, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
  const exports = {}
  new Function('exports', compiled)(exports)
  const rows = [
    { id: 1, db_type: 20 },
    { id: 2, db_type: 10 },
    { id: 3, db_type: '0' },
    { id: 4, db_type: 1 },
    { id: 5, db_type: 0 },
    { id: 6, db_type: 99 },
  ]
  assert.deepEqual(
    exports.sortLogicalDatasources(rows).map((row) => row.id),
    [3, 5, 4, 2, 1, 6]
  )
  assert.deepEqual(
    rows.map((row) => row.id),
    [1, 2, 3, 4, 5, 6]
  )
  assert.match(
    source,
    /rows.value\s*=\s*sortLogicalDatasources<LogicalSource>\(response.data \|\| \[\]\)/
  )
})
