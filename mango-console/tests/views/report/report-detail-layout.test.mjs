import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import less from 'less'
import postcss from 'postcss'
import fluidRem from '../../../scripts/postcss-fluid-rem.cjs'

const filename = new URL('../../../src/views/report/details/index.vue', import.meta.url).pathname
const source = readFileSync(filename, 'utf8')
const { descriptor } = parse(source, { filename })
const css = postcss.parse((await less.render(descriptor.styles[0].content)).css)

function properties(selector) {
  const result = {}
  css.walkRules(selector, rule => {
    if (rule.parent.type !== 'root') return
    rule.walkDecls(decl => { result[decl.prop] = decl.value })
  })
  return result
}

test('public report keeps independent reading shell while platform uses page tokens', () => {
  assert.equal(properties('.report-lab').padding, 'var(--m-page-gap)')
  assert.equal(properties('.standalone-report-container').padding, 'var(--m-space-lg)')
  assert.equal(properties('.standalone-report-container').height, '100vh')
  assert.equal(properties('.report-lab')['box-sizing'], 'border-box')
  assert.match(descriptor.scriptSetup.content, /route.path === '\/report\/details'/)
  assert.doesNotMatch(descriptor.template.content, /<TableBody|<TableHeader/)
  const globalCss = postcss.parse(readFileSync(new URL('../../../src/styles/index.css', import.meta.url), 'utf8'))
  const shellSelectors = []
  globalCss.walkRules(rule => {
    if (!rule.selector.includes(':has(.mango-report-detail-page.standalone-report-container)')) return
    shellSelectors.push(...rule.selectors)
    const declarations = Object.fromEntries(rule.nodes.filter(node => node.type === 'decl').map(node => [node.prop, node.value]))
    assert.equal(declarations.width, '100%')
    assert.equal(declarations['min-width'], '0')
  })
  assert.equal(shellSelectors.length, 3)
})

test('metadata uses centered title-value rows in a responsive grid without segmented borders', () => {
  assert.equal(properties('.meta-strip').display, 'grid')
  assert.match(properties('.meta-strip.has-task-name')['grid-template-columns'], /minmax\(230px, 1\.4fr\) repeat\(4, minmax\(0, 1fr\)\)/)
  assert.equal(properties('.report-meta-item').display, 'flex')
  assert.equal(properties('.report-meta-item')['justify-content'], 'center')
  assert.equal(properties('.report-meta-item')['align-items'], 'center')
  assert.equal(properties('.report-meta-item dt::after').content, "'：'")
  assert.equal(properties('.report-meta-item dd').margin, '0')
  assert.equal(properties('.report-meta-item dd')['align-items'], 'center')
  assert.equal(properties('.report-meta-item dt').margin, '0')
  assert.equal(properties('.meta-strip')['border-top'], '1px solid var(--m-border)')
  assert.equal(properties('.meta-strip').border, undefined)
  assert.equal(properties('.meta-strip')['overflow-x'], undefined)
  assert.match(descriptor.template.content, /a-tooltip :content="reportExecutionName"/)
  assert.doesNotMatch(descriptor.styles[0].content, /meta-strip::-webkit-scrollbar/)
  assert.doesNotMatch(descriptor.styles[0].content, /report-meta-item \+ \.report-meta-item/)
})

test('report ID reserves enough space for long identifiers without shrinking its value', () => {
  assert.match(descriptor.template.content, /class="report-meta-item mango-report-meta-id">\s*<dt>报告ID<\/dt>/)
  assert.match(properties('.meta-strip')['grid-template-columns'], /^minmax\(230px, 1\.4fr\)/)
  assert.equal(properties('.mango-report-meta-id dd')['flex-shrink'], '0')
  const layouts = {}
  css.walkAtRules('container', rule => {
    rule.walkRules(node => {
      if (!node.selectors.includes('.meta-strip')) return
      node.walkDecls('grid-template-columns', decl => { layouts[rule.params] = decl.value })
    })
  })
  assert.equal(layouts['mango-report-detail (max-width: 90rem)'], 'repeat(3, minmax(0, 1fr))')
  assert.equal(layouts['mango-report-detail (max-width: 68rem)'], 'repeat(2, minmax(0, 1fr))')
})

test('report status spans the whole header while execution metadata stays in the left column', () => {
  assert.equal(properties('.report-head').display, 'grid')
  assert.equal(properties('.head-main').display, 'contents')
  assert.equal(properties('.status-console')['grid-column'], '2')
  assert.equal(properties('.status-console')['grid-row'], '1 / span 2')
  assert.equal(properties('.status-console')['align-self'], 'stretch')
  assert.equal(properties('.meta-strip')['grid-column'], '1')
  assert.equal(properties('.meta-strip')['grid-row'], '2')
  let narrowStatusRow
  css.walkAtRules('container', rule => {
    if (!rule.params.includes('44rem')) return
    rule.walkRules('.status-console', node => node.walkDecls('grid-row', decl => { narrowStatusRow = decl.value }))
  })
  assert.equal(narrowStatusRow, '3')
})

test('filter controls wrap together with separate labels and bounded selectors', () => {
  assert.equal(properties('.case-toolbar-main')['flex-wrap'], 'wrap')
  assert.equal(properties('.case-title-actions')['flex-wrap'], 'wrap')
  assert.equal(properties('.case-title-actions')['min-width'], '0')
  assert.equal(properties('.mango-report-filter-group')['flex-wrap'], 'wrap')
  assert.equal(properties('.case-status-select').width, '160px')
  assert.match(descriptor.template.content, /aria-label="统计范围"/)
  assert.match(descriptor.template.content, /aria-label="测试结果"/)
  assert.doesNotMatch(descriptor.styles[0].content, /max-width: 1px/)
})

test('overview uses container-responsive columns without oversized minimum width', () => {
  assert.equal(properties('.mango-report-detail-page').container, 'mango-report-detail / inline-size')
  assert.equal(properties('.report-overview-scroll')['--mango-workbench-min-width'], '0px')
  assert.doesNotMatch(properties('.overview-grid')['grid-template-columns'], /px/)
  const conditions = []
  css.walkAtRules('container', rule => conditions.push(rule.params))
  assert.deepEqual(conditions, ['mango-report-detail (max-width: 90rem)', 'mango-report-detail (max-width: 68rem)', 'mango-report-detail (max-width: 44rem)'])
})

test('layout sizes pass through global density conversion, chart selector and initial loading are correct', async () => {
  const output = (await postcss([fluidRem()]).process(css.toString(), { from: filename })).css
  assert.match(output, /height: 11\.875rem/)
  assert.match(output, /width: 10rem/)
  assert.match(descriptor.styles[0].content, /:deep\(\.mango-status-chart\)/)
  assert.doesNotMatch(descriptor.styles[0].content, /:deep\(\.status-chart\)/)
  assert.match(descriptor.template.content, /:loading="summaryLoading && !totalCount"/)
})

test('report layout compiles and keeps guest read-only routes and action boundaries', () => {
  const script = compileScript(descriptor, { id: 'report-detail-layout' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'report-detail-layout', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  assert.match(source, /const canRetry = computed\(\(\) => !!userStore.token(?:\s*&&[^\n]+)?\)/)
  assert.match(source, /v-permission="'report:read'"/)
  const guard = readFileSync(new URL('../../../src/router/guard/permission.ts', import.meta.url), 'utf8')
  assert.match(guard, /if \(to.path === '\/report\/system\/details'\)/)
  assert.match(guard, /path: '\/report\/details',[\s\S]*?query: to.query/)
})
