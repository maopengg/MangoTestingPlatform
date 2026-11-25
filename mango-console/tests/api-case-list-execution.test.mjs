import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import ts from 'typescript'

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8')
const page = read('../src/views/apitest/case/index.vue')
const source = parse(page).descriptor.scriptSetup.content
const ast = ts.createSourceFile('case.ts', source, ts.ScriptTarget.Latest, true)
function functionCode(name) {
  const node = ast.statements.find(node =>
    (ts.isFunctionDeclaration(node) && node.name?.text === name)
    || (ts.isVariableStatement(node) && node.declarationList.declarations.some(item => item.name.getText(ast) === name)))
  assert.ok(node, name)
  return ts.transpileModule(node.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
}

test('list results use displayed version independently of the selected execution environment', () => {
  const code = functionCode('doRefresh')
  assert.match(code, /result_scope = 'displayed_version'/)
  assert.doesNotMatch(code, /list_test_env|selected_environment/)
  assert.match(code, /row\.list_result\?\.is_active === true/)
  assert.doesNotMatch(code, /isPendingExecution|row\.list_result\.status/)
  assert.match(page, /record\.list_result\.trace_id/)
})

test('execute submits the backend version token without falling back to editing', async () => {
  const calls = [], messages = [], running = { value: false }
  let timer, cleared = 0
  const context = {
    userStore: { selected_environment: 0 }, caseRunning: running, pageActive: { value: true },
    document: { visibilityState: 'visible' }, Message: {
      info: text => messages.push(text), success: () => {}, error: () => {},
    },
    getApiCaseRun: async (...args) => { calls.push(args); return { msg: 'ok' } },
    doRefresh: () => {}, setTimeout: callback => { timer = callback; return 1 }, clearTimeout: () => { cleared++ },
  }
  const run = new Function(...Object.keys(context), `let pageVersion=1, runNoticeTimer=null;
    ${functionCode('caseRun')}; return caseRun`)(...Object.values(context))
  for (const token of ['published:101', 'prepublished:202', `unpublished:${'a'.repeat(64)}`]) {
    await run({ id: 1, list_result: { version_token: token } })
    assert.deepEqual(calls.at(-1), [1, 0, null, undefined, undefined, token])
  }
  const count = calls.length
  await run({ id: 1 })
  assert.equal(calls.length, count)
  assert.match(messages.at(-1), /刷新列表/)
  assert.equal(running.value, false)
  assert.equal(cleared, 4)
  assert.equal(typeof timer, 'function')
})

test('execute rejects missing environment and concurrent submissions', async () => {
  const context = { userStore: { selected_environment: null }, caseRunning: { value: false },
    Message: { error: () => {} } }
  const run = new Function(...Object.keys(context), `${functionCode('caseRun')}; return caseRun`)(...Object.values(context))
  await run({ id: 1 })
  context.userStore.selected_environment = 0
  context.caseRunning.value = true
  await run({ id: 1 })
})

test('version hints agree with the displayed publication state', () => {
  const label = new Function(`${functionCode('listExecutionLabel')}; return listExecutionLabel`)()
  assert.equal(label({ publication_status: 'published', published_version_label: 'V1' }), '执行已发布 V1')
  assert.equal(label({ publication_status: 'prepublished', prepublished_revision_no: 3 }), '执行预发布 r3')
  assert.equal(label({ publication_status: 'unpublished' }), '执行当前编辑态')
})

test('result search keeps original numeric statuses and uses one pending-test option', () => {
  function load(filename, dependencies = {}) {
    const exports = {}
    new Function('exports', 'require', ts.transpileModule(read(filename), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText)(exports, name => dependencies[name])
    return exports
  }
  const shared = load('../src/views/apitest/search-filter-options.ts')
  const { resolveApiCaseSearchOptions } = load('../src/views/apitest/case/api-case-search-filter-options.ts', {
    '../search-filter-options': shared,
  })
  const original = [{ key: 0, title: '失败' }, { key: 1, title: '通过' }, { key: 2, title: '待开始' }]
  assert.deepEqual(resolveApiCaseSearchOptions({key:'status'}, [], {task_status:original}),
    [{key:0,title:'失败'},{key:1,title:'通过'},{key:2,title:'待测试'}])
  assert.equal(original[2].title, '待开始')
  assert.doesNotMatch(page, /'待验证'|'未执行'/)
  assert.match(page, /<a-tag v-else[^>]*>待测试<\/a-tag>/)
})

test('changed page and shared action/drawer components compile', () => {
  for (const filename of ['../src/views/apitest/case/index.vue',
    '../src/views/apitest/case/components/CaseResultTitle.vue',
    '../src/views/apitest/case/components/CaseVersionResultPopover.vue',
    '../src/components/table/MangoTableActions.vue',
    '../src/views/apitest/case/details/components/ApiCaseExecutionTraceDrawer.vue']) {
    const { descriptor } = parse(read(filename))
    const script = compileScript(descriptor, { id: filename })
    const result = compileTemplate({ source: descriptor.template.content, filename, id: filename,
      compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(result.errors, [], filename)
  }
})
