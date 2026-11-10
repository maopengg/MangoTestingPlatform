import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import { parse } from '@vue/compiler-sfc'
import { baseParse } from '@vue/compiler-dom'

const source = fs.readFileSync(
  new URL(
    '../../../../src/views/config/data-source/components/DataSourceWorkbench.vue',
    import.meta.url
  ),
  'utf8'
)
const { descriptor } = parse(source)
const template = baseParse(descriptor.template.content)
function elements(node, tag) {
  return (node.children || []).flatMap((child) => [
    ...(child.tag === tag ? [child] : []),
    ...elements(child, tag),
  ])
}
function hasClass(node, name) {
  return node.props?.some(
    (prop) => prop.name === 'class' && prop.value?.content.split(/\s+/).includes(name)
  )
}

test('父页面不向多根工作台传入未声明的 refresh 事件', () => {
  const pageSource = fs.readFileSync(
    new URL('../../../../src/views/config/data-source/index.vue', import.meta.url),
    'utf8'
  )
  const page = parse(pageSource).descriptor
  const workbench = elements(baseParse(page.template.content), 'DataSourceWorkbench')[0]
  assert.ok(workbench)
  assert.equal(
    workbench.props.some((prop) => prop.name === 'on' && prop.arg?.content === 'refresh'),
    false
  )
})

test('Tabs 使用有限高度布局，避免表格将分页挤出页面', () => {
  const tabs = elements(template, 'a-tabs')[0]
  assert.ok(hasClass(tabs, 'mango-source-tabs'))
  assert.match(
    descriptor.styles[0].content,
    /\.mango-source-tabs\s*\{[^}]*flex:\s*1;[^}]*min-height:\s*0;/
  )
})

test('两个页签的工具栏、表格和分页处于同一个高度受限容器', () => {
  for (const tab of elements(template, 'a-tab-pane')) {
    assert.equal(tab.children.filter((node) => node.type === 1).length, 1)
    const pane = tab.children.find((node) => node.type === 1)
    assert.ok(hasClass(pane, 'mango-source-table-pane'))
    assert.equal(elements(pane, 'TableFooter').length, 1)
    assert.equal(elements(pane, 'a-table').length, 1)
    const tableArea = elements(pane, 'div').find((node) =>
      hasClass(node, 'mango-source-table-area')
    )
    assert.equal(elements(tableArea, 'TableFooter').length, 0)
  }
})

test('页签禁止外层滚动，分页不参与表格收缩', () => {
  const style = descriptor.styles[0].content
  assert.match(style, /\.mango-source-tabs\s*:deep\(\.arco-tabs-pane\)\s*\{\s*overflow:\s*hidden;/)
  assert.match(
    style,
    /\.mango-source-table-pane\s*>\s*:not\(\.mango-source-table-area\)\s*\{\s*flex:\s*none;/
  )
})

test('导航只保留类型和连接两层，不重复增加实例地址分组', () => {
  const groups = elements(template, 'details')
  assert.equal(groups.length, 1)
  assert.equal(elements(groups[0], 'button').length, 1)
  assert.doesNotMatch(descriptor.scriptSetup.content, /group\.instances|const instances/)
  assert.match(descriptor.template.content, /搜索名称、地址或账号/)
  assert.match(descriptor.template.content, /:title="connectionAddress\(source\)"/)
})

test('连接元信息及ID和类型位于名称下面，默认展示绑定关系', () => {
  const title = elements(template, 'div').find((node) => hasClass(node, 'mango-source-title'))
  const children = title.children.filter((node) => node.type === 1)
  assert.equal(children[0].tag, 'strong')
  assert.ok(hasClass(children[1], 'mango-source-meta'))
  assert.equal(elements(children[1], 'a-tag').length, 1)
  assert.equal(elements(children[1], 'small').length, 1)
  assert.equal(elements(children[1], 'span').length, 3)
  assert.deepEqual(
    children[1].children.filter((node) => node.type === 1).map((node) => node.tag),
    ['small', 'a-tag', 'span', 'span', 'span']
  )
  assert.match(
    descriptor.scriptSetup.content,
    /activeTab\.value\s*=\s*'bindings'\s*;?\s*loadTab\(\)/
  )
  assert.match(descriptor.styles[0].content, /content: '·'/)
})

test('数据库发现提供查询操作，打开时冻结连接和数据库目标', () => {
  assert.match(descriptor.template.content, /openDatabaseQuery\(record\)/)
  assert.match(descriptor.scriptSetup.content, /sourceId: selected\.value\.id/)
  assert.match(descriptor.scriptSetup.content, /databaseName: record\.name/)
  assert.equal(elements(template, 'DataSourceSqlQueryDrawer').length, 1)
})

test('数据库类型标签使用全局枚举配色', () => {
  assert.match(
    descriptor.template.content,
    /<a-tag :color="enums\.colors\[selected\.db_type\]" size="small">/
  )
})

test('数据库名称吸收剩余宽度，操作列保持全局固定宽度和右侧固定', () => {
  const config = fs.readFileSync(
    new URL('../../../../src/views/config/data-source/config.ts', import.meta.url),
    'utf8'
  )
  const databases = config.slice(
    config.indexOf('export const databaseColumns'),
    config.indexOf('export const sourceFormFields')
  )
  assert.match(databases, /dataIndex: 'name', ellipsis: true, tooltip: true/)
  assert.match(
    databases,
    /slotName: 'query',\s*width: 160,\s*fixed: 'right' as const,\s*align: 'center' as const/
  )
  assert.doesNotMatch(databases, /width: 260/)
  assert.match(config, /slotName: 'actions',\s*width: 160,\s*fixed: 'right'/)
  assert.match(descriptor.template.content, /#query="\{ record \}"\s*>\s*<MangoTableActions/)
})
