import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import ts from 'typescript'
import { createApp } from 'vue'

const require = createRequire(import.meta.url)
const arco = require('@arco-design/web-vue')

test('global registration tolerates the uninitialized TreeSelect export and still registers it explicitly', () => {
  const source = ts.createSourceFile('index.ts', readFileSync('src/layouts/index.ts', 'utf8'), ts.ScriptTarget.Latest, true)
  const install = source.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === 'install')
  const code = ts.transpileModule(install.getText(source), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const warnings = [], app = createApp({ render: () => null })
  app.config.warnHandler = warning => warnings.push(warning)
  const wrapper = { render: () => null }
  const dependencies = {
    setupArcoTableDefaults() {},
    ArcoVue: { ...arco.default, TreeSelect: undefined, install() { throw Error('unsafe bulk installer invoked') } },
    ArcoVueIcon: { install() {} }, ArcoTreeSelect: arco.TreeSelect,
    DensityTable: wrapper, DensityTableColumn: wrapper, DensityModal: wrapper,
    DensityDrawer: wrapper, DensityAvatar: wrapper,
    registerComponents() {}, components: { install() {} }, getComponentName() {},
    emitKey: Symbol(), TinyEmitter: class {},
  }
  new Function(...Object.keys(dependencies), 'app', `${code};install(app)`)(...Object.values(dependencies), app)
  assert.deepEqual(warnings, [])
  assert.ok(app.component('ATreeSelect'))
  assert.ok(app.component('AButton'))
  assert.equal(app.component('a-modal'), wrapper)
})
