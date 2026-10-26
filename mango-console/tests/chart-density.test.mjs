import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

const source = readFileSync(new URL('../src/utils/chartDensity.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
})

function harness() {
  const exports = {}
  let changeDensity
  runInNewContext(outputText, {
    exports,
    window: { addEventListener: (_, listener) => { changeDensity = listener } },
  })
  return { wrap: exports.makeChartDensityAware, change: scale => changeDensity({ detail: { scale } }) }
}

function chart() {
  return {
    option: undefined,
    disposed: false,
    resizeCount: 0,
    getOption() { return this.option },
    isDisposed() { return this.disposed },
    resize() { this.resizeCount++ },
    setOption(option) {
      if (!option) throw new Error('option is null/undefined')
      this.option = option
    },
  }
}

test('density change before the first option does not read an uninitialized chart', () => {
  const { wrap, change } = harness()
  const empty = chart()
  empty.getOption = () => { throw new TypeError('Cannot convert undefined or null to object') }
  wrap(empty)
  assert.doesNotThrow(() => change(1.35))
  empty.setOption({ textStyle: { fontSize: 12 }, series: [{ data: [10] }] })
  assert.equal(empty.option.textStyle.fontSize, 16.2)
  assert.equal(empty.option.series[0].data[0], 10)
})

test('empty charts do not prevent other charts from scaling and repeated changes do not compound', () => {
  const { wrap, change } = harness()
  wrap(chart())
  const ready = wrap(chart())
  ready.setOption({ textStyle: { fontSize: 20 }, grid: { left: 40 }, series: [{ data: [10] }] })
  change(1.35)
  assert.equal(ready.option.textStyle.fontSize, 27)
  change(1)
  assert.equal(ready.option.textStyle.fontSize, 20)
  assert.equal(ready.option.grid.left, 40)
  assert.equal(ready.option.series[0].data[0], 10)
  assert.equal(ready.resizeCount, 2)
})

test('a failed first setOption is not treated as an initialized chart', () => {
  const { wrap, change } = harness()
  const broken = wrap(chart())
  assert.throws(() => broken.setOption(null), /option is null/)
  broken.getOption = () => { throw new Error('model not initialized') }
  assert.doesNotThrow(() => change(1.15))
})

test('null options and disposed charts are skipped safely', () => {
  const { wrap, change } = harness()
  const cleared = wrap(chart())
  cleared.setOption({})
  cleared.option = null
  assert.doesNotThrow(() => change(1.15))
  cleared.setOption({ textStyle: { fontSize: 20 } })
  assert.equal(cleared.option.textStyle.fontSize, 23)
  cleared.disposed = true
  change(1.35)
  assert.equal(cleared.resizeCount, 0)
})
