import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import ts from 'typescript'

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8')
const modal = read('../src/components/overlays/TestExecutionModal.vue')
test('batch execution offers all three versions and shared modal compiles', () => {
  const { descriptor } = parse(modal)
  const script = compileScript(descriptor, { id: 'batch-version' })
  const output = compileTemplate({ source: descriptor.template.content, filename: 'TestExecutionModal.vue', id: 'batch-version', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(output.errors, [])
  for (const value of ['editing', 'prepublished', 'published']) assert.ok(modal.includes(`value="${value}"`))
  assert.match(modal, /预发布固定待审核修订/)
  assert.match(read('../src/api/apitest/case.ts'), /'editing' \| 'prepublished' \| 'published'/)
})
test('page submits prepublished and blocks missing candidates without a fallback', async () => {
  const source = parse(read('../src/views/apitest/case/index.vue')).descriptor.scriptSetup.content
  const ast = ts.createSourceFile('case.ts', source, ts.ScriptTarget.Latest, true)
  const fn = ast.statements.find(n => ts.isFunctionDeclaration(n) && n.name.text === 'onConfirmCaseBatchRun')
  const js = ts.transpileModule(fn.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const writes = [], warnings = [], rows = [{ id: 1, name: '待审核', prepublished_revision_id: 101 }]
  const run = new Function('pendingBatchRunCaseIds', 'table', 'Message', 'batchRunModalRef', 'caseRunning', 'postApiCaseBatchRun', 'doRefresh', 'hasPublishedCaseVersion', js + ';return onConfirmCaseBatchRun')(
    { value: [1] }, { dataList: rows }, { warning: s => warnings.push(s), error: () => {}, success: () => {} },
    { value: { setConfirmLoading: () => {}, close: () => {} } }, { value: false },
    async (...args) => { writes.push(args); return { data: {} } }, () => {}, () => false)
  rows[0].prepublished_revision_id = null
  await run({ executionName: 'candidate', testEnv: 0, executionVersion: 'prepublished' })
  assert.equal(writes.length, 0)
  assert.match(warnings[0], /1-待审核/)
  rows[0].prepublished_revision_id = 101
  await run({ executionName: 'candidate', testEnv: 0, executionVersion: 'prepublished' })
  assert.equal(writes[0][4], 'prepublished')
})
