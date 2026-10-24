import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'

const filename = 'src/views/apitest/module-coverage/components/CoverageOverview.vue'
const source = fs.readFileSync(filename, 'utf8')
const { descriptor } = parse(source, { filename })
const helpers = descriptor.scriptSetup.content.slice(
  descriptor.scriptSetup.content.indexOf('  function donutStyle('),
  descriptor.scriptSetup.content.indexOf('  function render(')
)
function styles(scale = 1, currentOption) {
  if (arguments.length < 2) currentOption = { legend: [{ selected: { 已完成: false } }] }
  return new Function('token', 'scaleDensityPixels', 'useEcharts', 'getComputedStyle', 'document',
    ts.transpileModule(helpers, { compilerOptions: { target: ts.ScriptTarget.ES2020 } }).outputText +
    '; return { donutStyle, donutSeries }')(
    name => `theme:${name}`,
    value => value * scale,
    () => ({ getOption: () => currentOption }),
    () => ({ fontFamily: 'system-ui' }),
    { documentElement: {} }
  )
}

test('chart style adapts across global density anchors without changing data', () => {
  const rows = [{ name: '已完成', value: 1740 }, { name: '未完成', value: 482 }, { name: '暂不处理', value: 1089 }]
  for (const scale of [1, 1.15, 1.35]) {
    const { donutStyle, donutSeries } = styles(scale)
    const element = { clientWidth: 600 * scale }
    const option = donutStyle(element, rows, '场景总数')
    assert.equal(option.title.text, '3,311')
    assert.equal(option.legend.orient, 'horizontal')
    assert.equal(option.legend.selected.已完成, false)
    const series = donutSeries(element, rows)
    assert.match(series.label.formatter(rows[0]), /1,740 个 · 52\.55%/)
    assert.deepEqual(series.radius, ['50%', '68%'])
    assert.equal(series.label.show, true)
    assert.equal(series.labelLine.show, true)
    assert.equal(option.legend.formatter, undefined)
    assert.equal(option.textStyle.fontFamily, 'system-ui')
    assert.equal(option.title.textStyle.color, 'theme:--m-text')
    assert.deepEqual(rows.map(row => row.value), [1740, 482, 1089])
  }
})

test('narrow chart moves the legend below and keeps ring within its height', () => {
  const { donutStyle, donutSeries } = styles()
  const element = { clientWidth: 360 }
  const rows = [{ name: '未完整扫描', value: 0 }]
  const option = donutStyle(element, rows, '模块总数')
  assert.equal(option.legend.orient, 'horizontal')
  assert.equal(option.legend.bottom, 0)
  assert.match(donutSeries(element, rows).label.formatter(rows[0]), /0\.00%/)
  assert.deepEqual(donutSeries(element, rows).radius, ['40%', '58%'])
  assert.deepEqual(donutSeries(element, rows).center, ['50%', '45%'])
})

test('initial chart render tolerates getOption returning undefined', () => {
  for (const currentOption of [undefined, null, {}]) {
    const { donutStyle } = styles(1, currentOption)
    const option = donutStyle({ clientWidth: 600 }, [{ name: '已完成', value: 3 }], '场景总数')
    assert.equal(option.legend.selected, undefined)
    assert.equal(option.title.text, '3')
  }
})

test('scan click, status tooltip, theme updates and resize lifecycle are preserved', () => {
  assert.match(source, /gapFilter.value = event.dataIndex === 1 \? 'scan' : 'all'/)
  assert.match(source, /statusPercent\(item.value\)/)
  assert.match(source, /data: statusData.value/)
  assert.match(source, /window.addEventListener\('mango-theme-change', render\)/)
  assert.match(source, /prefers-reduced-motion: reduce/)
  assert.match(source, /function resize\(\)[\s\S]*?\.resize\(\)[\s\S]*?render\(\)/)
})

test('overview script, template and scoped styles compile', async () => {
  const script = compileScript(descriptor, { id: 'coverage-chart-style' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'coverage-chart-style', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  const style = await compileStyleAsync({ source: descriptor.styles[0].content, filename,
    id: 'coverage-chart-style', scoped: true, preprocessLang: 'less' })
  assert.deepEqual(style.errors, [])
})
