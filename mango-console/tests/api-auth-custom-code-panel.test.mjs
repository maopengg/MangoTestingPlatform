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
  const panel = { visible: false, title: '', code: '', version: 0 }
  const open = new Function('customCodePanel', code + ';return onViewCustomCode')(panel)
  const row = Object.freeze({ id: 1, name: 'Example auth', auth_type: 1, custom_code: 'def auth(context):\n    return {}' })
  open(row)
  assert.deepEqual(panel, { visible: true, title: '自定义代码 / Example auth', code: row.custom_code,
    id: 1, result: null, error: '', version: 1 })
  panel.visible = false
  open({ auth_type: 0, name: 'API auth' })
  assert.equal(panel.visible, false)
  open({ auth_type: 1, name: 'Empty code', custom_code: null })
  assert.equal(panel.code, '')
})

function createRunner(refresh) {
  const method = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === 'onRunCustomCode')
  const compiled = ts.transpileModule(method.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const panel = { visible: true, id: 1, version: 1, result: null, error: '', code: 'unchanged' }
  const running = new Set()
  const run = new Function('customCodePanel', 'customCodeRunningIds', 'postApiAuthConfigRefresh', 'doRefresh',
    compiled + ';return onRunCustomCode')(panel, running, refresh, () => {})
  return { panel, running, run }
}

test('execution refreshes authorization and displays latest response without editing code', async () => {
  const { panel, running, run } = createRunner(async id => {
    assert.equal(id, 1)
    return { data: { cache_data: { token: 'example-token' }, last_refresh_status: 1 } }
  })
  await run()
  assert.equal(panel.result.last_refresh_status, 1)
  assert.equal(panel.code, 'unchanged')
  assert.equal(running.size, 0)
})

test('failure clears previous success and displays error with loading released', async () => {
  const { panel, running, run } = createRunner(async () => { throw new Error('example failure') })
  panel.result = { old: true }
  await run()
  assert.equal(panel.result, null)
  assert.equal(panel.error, 'example failure')
  assert.equal(running.size, 0)
})

test('duplicate execution is blocked and stale response cannot overwrite reopened panel', async () => {
  let resolve
  let calls = 0
  const { panel, running, run } = createRunner(() => { calls++; return new Promise(done => { resolve = done }) })
  const pending = run()
  assert.equal(running.has(1), true)
  await run()
  assert.equal(calls, 1)
  panel.version++
  resolve({ data: { stale: true } })
  await pending
  assert.equal(panel.result, null)
  assert.equal(running.size, 0)
})

test('split view reuses JSON/loading components and requires debug permission', () => {
  assert.match(source, /grid-template-rows: minmax\(0, 7fr\) minmax\(0, 3fr\)/)
  assert.match(source, /v-permission="'api.auth_config:change'"/)
  assert.match(source, /<JsonDisplay v-else-if="customCodePanel.result !== null"/)
  assert.match(source, /<MangoPanelSpin :loading="customCodeRunningIds.has\(customCodePanel.id\)"/)
})

test('preview reuses pytest editor and side panel with detail permission and no save entry', () => {
  assert.match(source, /permission: 'api.auth_config:read', label: '自定义代码', hidden: record.auth_type !== 1, overflow: true/)
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

test('authorization name keeps a readable width and scrolling includes every column', () => {
  const config = readFileSync(new URL('../src/views/apitest/auth-config/config.ts', import.meta.url), 'utf8')
  const columnCode = config.slice(config.indexOf('export const tableColumns')).replaceAll('export ', '')
  const compiled = ts.transpileModule(columnCode, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const result = new Function('useTableColumn', 'table', 'updateUserColumn',
    compiled + ';return {tableColumns,tableScrollX}')(
      columns => columns, { indexColumn: { width: 100 } }, () => ({ width: 110 }),
    )
  const name = result.tableColumns.find(column => column.key === 'name')
  assert.equal(name.width, 240)
  assert.equal(name.ellipsis, true)
  assert.equal(name.tooltip, true)
  assert.equal(result.tableScrollX, result.tableColumns.reduce((sum, column) => sum + column.width, 40))
  assert.match(source, /:scroll="\{ x: tableScrollX, y: '100%' \}"/)
})
