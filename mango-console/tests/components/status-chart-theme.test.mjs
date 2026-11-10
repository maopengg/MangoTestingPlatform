import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { computed, ref, watch } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../../src/components/chart/StatusChart.vue', import.meta.url).pathname
const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename })

test('theme changes refresh donut and legend without changing data, and unregister on unmount', () => {
  const props = { success: 8, fail: 2, warning: 0, pending: 0, todo: 0, stopped: 0 }
  let theme = 'light'
  const handlers = new Map()
  const options = []
  let mount, unmount, disposed = false
  const chart = { setOption(option) { options.push(option) }, resize() {}, dispose() { disposed = true } }
  const exports = {}
  const js = ts.transpileModule(descriptor.scriptSetup.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  const state = new Function('exports', 'require', 'defineProps', 'window', 'document',
    'getComputedStyle', 'ResizeObserver', `${js}; return { pieChart, chartItems, total }`)(
    exports, key => key === 'vue'
      ? { computed, ref, watch, onMounted: fn => { mount = fn }, onBeforeUnmount: fn => { unmount = fn }, onActivated() {}, onDeactivated() {} }
      : { default: () => chart }, () => props,
    { addEventListener: (name, fn) => handlers.set(name, fn),
      removeEventListener: (name, fn) => { if (handlers.get(name) === fn) handlers.delete(name) } },
    { documentElement: {} },
    () => ({ getPropertyValue: name => `${theme}:${name}` }), undefined,
  )
  state.pieChart.value = {}
  mount()
  assert.equal(state.total.value, 10)
  assert.equal(state.chartItems.value[0].color, 'light:--m-success')
  assert.equal(state.chartItems.value[0].percentText, '80.00%')
  theme = 'dark'
  handlers.get('mango-theme-change')()
  assert.equal(state.chartItems.value[0].color, 'dark:--m-success')
  assert.equal(options.at(-1).series[0].data[0].itemStyle.color, 'dark:--m-success')
  assert.deepEqual(options.at(-1).series[0].data.map(item => item.value), [8, 2, 0, 0, 0, 0])
  unmount()
  assert.equal(disposed, true)
  assert.equal(handlers.size, 0)
})

test('status chart template compiles', () => {
  const script = compileScript(descriptor, { id: 'status-theme' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'status-theme', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})
