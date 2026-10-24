import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import postcss from 'postcss'

const filename = new URL('../src/views/report/effectiveness/index.vue', import.meta.url).pathname
const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename })
const css = postcss.parse(descriptor.styles[0].content)
function properties(selector) {
  const result = {}
  css.walkRules(selector, rule => rule.walkDecls(decl => { result[decl.prop] = decl.value }))
  return result
}

test('report rows fit paper width without inheriting normal-mode minimums', () => {
  const row = properties('.is-report-mode .mango-effectiveness-module-row')
  assert.equal(row['min-width'], '0')
  assert.equal(row.width, '100%')
  assert.equal(row['box-sizing'], 'border-box')
  assert.equal((row['grid-template-columns'].match(/minmax\(0,/g) || []).length, 6)
  assert.doesNotMatch(row['grid-template-columns'], /px/)
  assert.equal(properties('.mango-effectiveness-module-row')['min-width'], '900px')
})

test('report long comparison text wraps instead of widening the last column', () => {
  assert.equal(properties('.is-report-mode .mango-effectiveness-module-row > *')['min-width'], '0')
  assert.equal(properties('.is-report-mode .mango-effectiveness-module-row__comparison')['white-space'], 'normal')
})

test('report template compiles with script bindings', () => {
  const script = compileScript(descriptor, { id: 'report-width' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'report-width', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})

test('report health panels expand without scroll-only content', () => {
  const panel = properties('.is-report-mode .mango-effectiveness-grid--health > .mango-effectiveness-panel')
  assert.equal(panel.height, 'auto')
  assert.equal(panel['max-height'], 'none')
  assert.equal(panel.overflow, 'visible')
  css.walkRules(rule => {
    if (rule.selector.includes('.is-report-mode .mango-effectiveness-task-health__list,')) {
      const declarations = Object.fromEntries(rule.nodes.filter(node => node.type === 'decl').map(node => [node.prop, node.value]))
      assert.equal(declarations.overflow, 'visible')
    }
  })
  assert.doesNotMatch(descriptor.scriptSetup.content, /height: 520px !important/)
})

test('diagnostic charts have more room and odd chart spans the report width', () => {
  assert.equal(properties('.is-report-mode .mango-effectiveness-grid--diagnostics')['grid-template-columns'], 'repeat(2, minmax(0, 1fr))')
  assert.equal(properties('.is-report-mode .mango-effectiveness-grid--diagnostics > :last-child:nth-child(odd)')['grid-column'], '1 / -1')
  assert.match(descriptor.scriptSetup.content, /hideOverlap: true/)
})

test('quality labels reuse global Arco tags and numeric cells are centered', () => {
  assert.doesNotMatch(descriptor.template.content, /mango-effectiveness-quality-tag/)
  assert.match(descriptor.template.content, /<a-tag[\s\S]*?record\.quality_label/)
  assert.equal(properties('.mango-effectiveness-module-row > :not(:first-child):not(:last-child)')['text-align'], 'center')
  css.walkRules(rule => {
    if (rule.selector.includes('.mango-effectiveness-output-table td')) {
      const alignment = rule.nodes.find(node => node.prop === 'text-align')
      assert.equal(alignment.value, 'center')
    }
  })
})

test('period report preserves status chart size and equal-height panels', () => {
  const periodFilename = new URL('../src/views/report/effectiveness/components/PeriodQualityTrend.vue', import.meta.url).pathname
  const period = parse(readFileSync(periodFilename, 'utf8'), { filename: periodFilename }).descriptor
  const periodCss = postcss.parse(period.styles[0].content)
  periodCss.walkRules('.mango-period-quality-trend', rule => {
    assert.equal(rule.nodes.find(node => node.prop === 'align-items').value, 'stretch')
  })
  periodCss.walkRules('.mango-period-quality-trend__status-chart.is-report-layout', rule => {
    assert.equal(rule.nodes.find(node => node.prop === 'height').value, '430px')
  })
  const script = compileScript(period, { id: 'period-report' })
  assert.deepEqual(compileTemplate({ source: period.template.content, filename: periodFilename,
    id: 'period-report', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})
