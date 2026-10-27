import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'
import ts from 'typescript'

const filename = new URL('../src/views/apitest/auth-config/index.vue', import.meta.url)
const source = readFileSync(filename, 'utf8')
const { descriptor } = parse(source)
const ast = ts.createSourceFile('auth.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
const method = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === 'onViewCustomCode')
const code = ts.transpileModule(method.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText

test('custom code opens read-only preview without mutating the row or edit form', () => {
  const panel = { visible: false, title: '', code: '' }
  const open = new Function('customCodePanel', code + ';return onViewCustomCode')(panel)
  const row = Object.freeze({ id: 1, name: 'Example auth', auth_type: 1, custom_code: 'def auth(context):\n    return {}' })
  open(row)
  assert.deepEqual(panel, { visible: true, title: '自定义代码 / Example auth', code: row.custom_code })
  panel.visible = false
  open({ auth_type: 0, name: 'API auth' })
  assert.equal(panel.visible, false)
  open({ auth_type: 1, name: 'Empty code', custom_code: null })
  assert.equal(panel.code, '')
})

test('preview reuses pytest editor and side panel with detail permission and no save entry', () => {
  assert.match(source, /permission: 'api.auth_config:detail', label: '自定义代码', hidden: record.auth_type !== 1, overflow: true/)
  const panel = descriptor.template.content.match(/<BaseSidePanel[\s\S]*?<\/BaseSidePanel>/)?.[0]
  assert.ok(panel)
  assert.match(panel, /:width="1000"/)
  assert.match(panel, /:show-footer="false"/)
  assert.match(panel, /<CodeEditor[\s\S]*?language="python"[\s\S]*?readonly/)
  assert.doesNotMatch(panel, /@confirm|保存|v-model="customCodePanel.code"/)
  const compiled = compileScript(descriptor, { id: 'auth-custom-code' })
  const template = compileTemplate({ source: descriptor.template.content, filename: filename.pathname,
    id: 'auth-custom-code', compilerOptions: { bindingMetadata: compiled.bindings } })
  assert.deepEqual(template.errors, [])
})
