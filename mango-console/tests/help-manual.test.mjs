import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/help/manual')
const open = () => harness('index', 'pageElement,scrollToSection', { base })

test('目录定位只修改本页滚动位置，并将键盘焦点移至标题', () => {
  const page = open()
  const scrolls = [], focuses = [], selectors = []
  const heading = { getBoundingClientRect: () => ({ top: 240 }), focus: options => focuses.push(options) }
  page.pageElement.value = {
    scrollTop: 40, clientTop: 1,
    getBoundingClientRect: () => ({ top: 100 }),
    querySelector: selector => { selectors.push(selector); return heading },
    scrollTo: options => scrolls.push(options),
  }
  page.scrollToSection('api')
  assert.deepEqual(selectors, ['#mango-manual-api'])
  assert.deepEqual(scrolls, [{ top: 179, behavior: 'auto' }])
  assert.deepEqual(focuses, [{ preventScroll: true }])
  page.close()
})

test('未挂载、目标不存在及容器重新挂载均安全', () => {
  const page = open()
  assert.doesNotThrow(() => page.scrollToSection('ui'))
  page.pageElement.value = { querySelector: () => null }
  assert.doesNotThrow(() => page.scrollToSection('settings'))
  const scrolls = []
  page.pageElement.value = {
    scrollTop: 0, clientTop: 0,
    getBoundingClientRect: () => ({ top: 100 }),
    querySelector: () => ({ getBoundingClientRect: () => ({ top: 90 }), focus() {} }),
    scrollTo: options => scrolls.push(options),
  }
  page.scrollToSection('ui')
  assert.deepEqual(scrolls, [{ top: 0, behavior: 'auto' }])
  page.close()
})

test('当前页面的脚本、模板及样式编译通过', () => {
  const filename = path.join(base, 'index.vue')
  const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'manual-test' })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: 'manual-test', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
  for (const style of descriptor.styles) {
    assert.deepEqual(compileStyle({ source: style.content, filename, id: 'manual-test', scoped: style.scoped }).errors, [])
  }
})
