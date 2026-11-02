import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileTemplate } from '@vue/compiler-sfc'

function handler(file, name, bindings) {
  const descriptor = parse(readFileSync(file, 'utf8')).descriptor
  const ast = ts.createSourceFile('handler.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
  const node = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name.text === name)
  const code = ts.transpileModule(node.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2020 } }).outputText
  return new Function(...Object.keys(bindings), `${code}; return ${name}`)(...Object.values(bindings))
}

test('manual task trigger keeps the one detailed API error and resets loading without closing form', async () => {
  const errors = []
  const state = { triggerRecord: { id: 1 }, triggerLoading: false }
  let closed = 0
  const loading = []
  const trigger = handler('src/views/timing/tasks/index.vue', 'onConfirmTrigger', {
    data: state,
    postSystemTriggerManual: async () => { errors.push('定时任务尚未绑定任何有效用例'); throw new Error(errors[0]) },
    Message: { error: text => errors.push(text), success: () => assert.fail('must not report success') },
    triggerModalRef: { value: { close: () => closed++, setConfirmLoading: value => loading.push(value) } },
    doRefresh: () => assert.fail('must not refresh failed trigger'),
  })
  assert.equal(await trigger({ testEnvs: [0], apiConcurrencyLimit: null }), false)
  assert.deepEqual(errors, ['定时任务尚未绑定任何有效用例'])
  assert.equal(state.triggerLoading, false)
  assert.equal(state.triggerRecord.id, 1)
  assert.equal(closed, 0)
  assert.deepEqual(loading, [false])
})

test('execution options failure uses existing request-layer notification only', async () => {
  const errors = []
  const data = { executionOptionsLoading: false }
  const load = handler('src/views/timing/tasks/index.vue', 'loadExecutionOptions', {
    data, getSystemTaskExecutionOptions: async () => { errors.push('服务连接异常'); throw new Error('network') },
    Message: { error: value => errors.push(value) },
  })
  assert.equal(await load(), false)
  assert.equal(data.executionOptionsLoading, false)
  assert.deepEqual(errors, ['服务连接异常'])
})

test('repository action consumes reported failures and ignores repeated clicks during loading', async () => {
  const errors = []
  const actionLoading = {}
  let reject, requests = 0
  const run = handler('src/views/pytest/repository/index.vue', 'runAction', {
    actionLoading, Message: { success: () => assert.fail('must not report success'), error: value => errors.push(value) },
    loadRepositories: () => assert.fail('must not refresh failed pull'),
    loadRepositoryTree: () => assert.fail('must not fetch tree after failed pull'),
  })
  const action = () => { requests++; return new Promise((_resolve, fail) => { reject = fail }) }
  const first = run({ id: 7 }, action)
  await run({ id: 7 }, action)
  assert.equal(requests, 1)
  errors.push('Pytest 仓库凭证不存在或无法解密')
  reject(new Error(errors[0]))
  await first
  assert.equal(actionLoading[7], false)
  assert.deepEqual(errors, ['Pytest 仓库凭证不存在或无法解密'])
})

test('action area stops DOM click bubbling and dropdown item stops its teleported event', () => {
  const filename = 'src/components/table/MangoTableActions.vue'
  const source = readFileSync(filename, 'utf8')
  const descriptor = parse(source).descriptor
  const compiled = compileTemplate({ source: descriptor.template.content, filename, id: 'action-click' })
  assert.deepEqual(compiled.errors, [])
  const code = ts.transpileModule(compiled.code, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  const exports = {}
  new Function('require', 'exports', code)(() => ({ ...vue, resolveComponent: name => name }), exports)
  const root = exports.render({ visibleInlineActions: [], overflowActions: [], handleClick() {} }, [])
  const event = { cancelBubble: false, stopPropagation() { this.cancelBubble = true } }
  root.props.onClick(event)
  assert.equal(event.cancelBubble, true)
  assert.match(source, /@click\.stop="handleClick\(action\)"/)
})
