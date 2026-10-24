import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { computed, reactive } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import less from 'less'
import postcss from 'postcss'

const filename = new URL('../../src/layouts/MainLayout.vue', import.meta.url).pathname
const source = readFileSync(filename, 'utf8')
const { descriptor } = parse(source, { filename })

test('only report detail opts out of the footer, retaining existing permission metadata', () => {
  const router = readFileSync(new URL('../../src/router/index.ts', import.meta.url), 'utf8')
  assert.match(router, /name: 'ReportDetails',[\s\S]*?hideFooter: true,[\s\S]*?permissionKey: 'report'/)
  assert.equal((router.match(/hideFooter: true/g) || []).length, 1)
})

test('footer follows current route and returns when navigating to other pages', () => {
  const expression = source.match(/const showFooter = computed\(\(\) => ([^\n]+)\)/)[1]
  const route = reactive({ meta: {} })
  const showFooter = computed(new Function('route', `return () => ${expression}`)(route))
  assert.equal(showFooter.value, true)
  route.meta = { hideFooter: true }
  assert.equal(showFooter.value, false)
  route.meta = { hideFooter: false }
  assert.equal(showFooter.value, true)
  route.meta = {}
  assert.equal(showFooter.value, true)
  assert.match(descriptor.template.content, /<section v-if="showFooter" class="mango-footer-wrapper">/)
})

test('no-footer layout releases reserved height for both fixed and fluid content', async () => {
  const css = postcss.parse((await less.render(descriptor.styles[0].content, {
    globalVars: { footerHeight: '40px', logoHeight: '45px', tabHeight: '30px',
      menuWidth: '200px', minMenuWidth: '48px', transitionTime: '0.2s' },
  })).css)
  for (const [selector, property] of [
    ['.mango-main-layout-container.mango-main-layout--without-footer .flex-height', 'height'],
    ['.mango-main-layout-container.mango-main-layout--without-footer .min-height', 'min-height'],
  ]) {
    let value
    css.walkRules(selector, rule => rule.walkDecls(property, decl => { value = decl.value }))
    assert.equal(value, 'calc(100% - var(--m-page-inset-block-start))')
  }
})

test('layout compiles with conditional footer', () => {
  const script = compileScript(descriptor, { id: 'report-footer' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'report-footer', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})
