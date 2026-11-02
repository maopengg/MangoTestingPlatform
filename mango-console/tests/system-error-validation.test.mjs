import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = 'src/views/system/error-record/index.vue'
const source = readFileSync(filename, 'utf8')

test('validation diagnostics use warning status in both list and detail', () => {
  assert.match(source, /record.status === 'warning' \? 'orange' : 'red'/)
  assert.match(source, /detail.record.status === 'warning' \? 'orange' : 'red'/)
  assert.match(source, /detail.record.status === 'warning' \? '校验诊断' : '异常堆栈'/)
  const { descriptor } = parse(source)
  const script = compileScript(descriptor, { id: 'system-error-validation' })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: 'system-error-validation',
    compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
})
