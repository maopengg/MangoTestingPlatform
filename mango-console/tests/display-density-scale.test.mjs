import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

const source = readFileSync(new URL('../src/hooks/useDisplayDensity.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
})
const exports = {}
runInNewContext(outputText, {
  exports,
  require(name) {
    if (name === 'vue') return { ref: value => ({ value }) }
    if (name === '@/store/types') return {
      DisplayDensity: { AUTO: 'auto', COMPACT: 'compact', STANDARD: 'standard', COMFORTABLE: 'comfortable' },
    }
    { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw new Error(`Unexpected dependency: ${name}`) }
  },
})

test('automatic density uses 100%, 115%, 135% anchors and caps above 4K', () => {
  assert.equal(exports.getAutoDisplayScale(1900), 1)
  assert.equal(exports.getAutoDisplayScale(2560), 1.15)
  assert.equal(exports.getAutoDisplayScale(3840), 1.35)
  assert.equal(exports.getAutoDisplayScale(5120), 1.35)
})

test('automatic density interpolates continuously and keeps the small-screen floor', () => {
  assert.ok(Math.abs(exports.getAutoDisplayScale(2230) - 1.075) < 1e-10)
  assert.ok(Math.abs(exports.getAutoDisplayScale(3200) - 1.25) < 1e-10)
  assert.equal(exports.getAutoDisplayScale(950), 0.5)
  assert.equal(exports.getAutoDisplayScale(600), 0.5)
})

test('account preferences update the shared 2K/4K anchors and reset to defaults safely', () => {
  exports.setAutoDisplayScales(1.3, 1.6)
  assert.equal(exports.getAutoDisplayScale(1900), 1)
  assert.equal(exports.getAutoDisplayScale(2560), 1.3)
  assert.equal(exports.getAutoDisplayScale(3840), 1.6)
  assert.equal(exports.getAutoDisplayScale(5120), 1.6)
  exports.setAutoDisplayScales(1.7, 1.2)
  assert.equal(exports.getAutoDisplayScale(3840), 1.7)
  exports.setAutoDisplayScales(NaN, Infinity)
  assert.equal(exports.getAutoDisplayScale(2560), 1.15)
  assert.equal(exports.getAutoDisplayScale(3840), 1.35)
})
