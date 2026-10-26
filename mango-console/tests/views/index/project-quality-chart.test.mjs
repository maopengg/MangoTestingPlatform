import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = 'src/views/index/components/chart/ProjectQualityChart.vue'
const source = readFileSync(new URL('../../../src/views/index/components/chart/ProjectQualityChart.vue', import.meta.url), 'utf8')

test('project quality chart keeps the report-count axis title below the plot with reserved space', () => {
  assert.match(source, /name: '报告数（份）',\s*nameLocation: 'middle',\s*nameGap: 24/)
  assert.match(source, /grid:\s*\{[^}]*bottom: 32,[^}]*containLabel: true/)
})

test('project quality chart compiles after the axis layout change', () => {
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: filename })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
})
