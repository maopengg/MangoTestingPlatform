import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import { parse } from '@vue/compiler-sfc'
import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const { descriptor } = parse(readFileSync('src/components/feedback/MangoPanelSpin.vue', 'utf8'))
const module = { exports: {} }
runInNewContext(ts.transpileModule(descriptor.script.content, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText, {
  module,
  exports: module.exports,
  require(name) {
    if (name === '@arco-design/web-vue/es/spin') {
      return { default: require('@arco-design/web-vue/lib/spin') }
    }
    return require(name)
  },
})
const MangoPanelSpin = module.exports.default

test('real Arco renders an owned direct content layer in loading and ready states', async () => {
  for (const loading of [false, true]) {
    const html = await renderToString(createSSRApp({
      render: () => h(MangoPanelSpin, { loading, class: 'mango-test-panel', 'data-testid': 'panel' }, {
        default: () => h('section', 'Report content'),
      }),
    }))
    assert.match(html, /class="arco-spin[^" ]*(?: [^"]*)?mango-test-panel/)
    assert.match(html, /data-testid="panel"/)
    assert.match(html, /<div class="mango-panel-spin__content"><section>Report content<\/section><\/div>/)
    assert.equal(html.includes('arco-spin-mask'), loading)
    assert.doesNotMatch(html, /arco-spin-children/)
  }
})

test('nested panels keep distinct content layers and one active mask', async () => {
  const html = await renderToString(createSSRApp({
    render: () => h(MangoPanelSpin, { loading: true }, {
      default: () => h(MangoPanelSpin, { loading: false }, { default: () => h('section', 'Nested') }),
    }),
  }))
  assert.equal((html.match(/class="mango-panel-spin__content"/g) || []).length, 2)
  assert.equal((html.match(/class="arco-spin-mask"/g) || []).length, 1)
})

test('icon slot and spinner-only usage are forwarded without adding an empty panel', async () => {
  const html = await renderToString(createSSRApp({
    render: () => h(MangoPanelSpin, { loading: true, tip: 'Loading' }, {
      icon: () => h('span', 'Custom icon'),
    }),
  }))
  assert.match(html, /Custom icon/)
  assert.match(html, /Loading/)
  assert.doesNotMatch(html, /mango-panel-spin__content/)
})

test('source no longer depends on nonexistent Arco content nodes', () => {
  function walk(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const filename = path.join(directory, entry.name)
      if (entry.isDirectory()) walk(filename)
      else if (/\.(vue|css)$/.test(filename)) {
        assert.doesNotMatch(readFileSync(filename, 'utf8'), /\.arco-spin-children/, filename)
      }
    }
  }
  walk('src')
})
