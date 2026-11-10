import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8')
const transpile = (source) =>
  ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext },
  }).outputText
function vueFiles(directory = new URL('../src/', import.meta.url)) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const url = new URL(entry.name, directory)
    return entry.isDirectory()
      ? vueFiles(new URL(entry.name + '/', directory))
      : entry.name.endsWith('.vue')
      ? [url]
      : []
  })
}

test('全部页面与半屏窗口不再声明按钮权限或按角色隐藏操作', () => {
  for (const file of vueFiles()) {
    const source = readFileSync(file, 'utf8')
    assert.doesNotMatch(source, /v-permission|(?:[{,]\s*|^\s*)permission\s*:/m, file.pathname)
    const checks = source.match(/\w+\.hasPermission\([^)]*\)/g) || []
    assert.deepEqual(
      checks,
      file.pathname.endsWith('/system/role/index.vue')
        ? ["permissionStore.hasPermission('system.role')"]
        : [],
      file.pathname
    )
  }
  assert.match(read('router/guard/permission.ts'), /permissionStore\.hasPermission/)
  assert.match(read('api/http.ts'), /permissions\.hasPermission\(required\)/)
})

test('清理和绑定操作统一展示，不再携带前端权限字段', () => {
  const source = read('views/data-factory/execution/index.vue')
  const start = source.indexOf('  function executionActions(')
  const code = transpile(source.slice(start, source.indexOf('  function cleanup(', start)))
  const actions = new Function(
    'cleanupIds',
    'batchCleanupLoading',
    'canCleanup',
    'openDetail',
    'cleanup',
    `${code}; return executionActions`
  )(
    new Set(),
    { value: false },
    () => true,
    () => {},
    () => {}
  )({ id: 1 })
  assert.deepEqual(
    actions.map((action) => action.label),
    ['详情', '清理']
  )
  assert.ok(actions.every((action) => !('permission' in action)))
  assert.doesNotMatch(read('views/apitest/module-coverage/index.vue'), /hasPermission|v-permission/)
})

test('仍保留历史快照只读、发布锁定和防重复提交等业务条件', async () => {
  const callback = read('views/apitest/case/details/components/ApiCaseCallbackPanel.vue')
  assert.match(callback, /computed\(\(\) => !props\.editLocked\)/)
  assert.match(callback, /saving\.value[\s\S]*?props\.savePending[\s\S]*?props\.editLocked/)
  const script = parse(read('components/DataFactory/CaseConfigPanel.vue')).descriptor.scriptSetup.content
  const ast = ts.createSourceFile('panel.ts', script, ts.ScriptTarget.Latest, true)
  const declaration = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === 'save')
  const save = new Function('props', 'visible', transpile(declaration.getText(ast)) + '; return save')({ readonly: true }, { value: true })
  assert.equal(await save(), false)
  assert.match(
    read('components/business/CasePublicationReviewModal.vue'),
    /loading\.value \|\| publishing\.value \|\| !acknowledged\.value/
  )
})

test('所有 Vue 页面及公共组件可编译', () => {
  for (const file of vueFiles()) {
    const filename = file.pathname
    const { descriptor, errors } = parse(readFileSync(file, 'utf8'), { filename })
    assert.deepEqual(errors, [], filename)
    const script = descriptor.scriptSetup ? compileScript(descriptor, { id: filename }) : null
    if (!descriptor.template) continue
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: filename,
        compilerOptions: { bindingMetadata: script?.bindings || {} },
      }).errors,
      [],
      filename
    )
  }
})
