import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const directory = 'src/views/config/product/module/'
const exports = {}
new Function('exports', ts.transpileModule(readFileSync(`${directory}config.ts`, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText)(exports)
const { buildModuleTree, filterModuleTree, moduleBranchKeys, moduleCreateDraft } = exports
const root = { id: 1, name: '业务服务', level: 1 }
const parent = { id: 2, name: '用户管理', level: 2, parent: root }
const leaf = { id: 3, name: '登录', level: 3, parent }
const sibling = { id: 4, name: '注销', level: 3, parent }
const rows = [leaf, root, sibling, parent, { id: 5, name: '其他模块', level: 1 }]

test('tree includes all three levels and uses parent IDs, independent of source ordering', () => {
  const tree = buildModuleTree(rows)
  assert.equal(tree.length, 2)
  assert.equal(tree[0].children[0].record, parent)
  assert.deepEqual(tree[0].children[0].children.map(node => node.key), [3, 4])
  assert.deepEqual(moduleBranchKeys(tree), [1, 2])
  assert.deepEqual(moduleBranchKeys(tree, 1), [1])
  assert.deepEqual(moduleBranchKeys(tree, 0), [])
  const missingParent = buildModuleTree([{ id: 9, name: '待核查模块', parent: { id: 99 } }])
  assert.equal(missingParent[0].key, 9)
})

test('search keeps ancestor context for leaves and complete descendants for matching parents', () => {
  const tree = buildModuleTree(rows)
  const matched = filterModuleTree(tree, '登录')
  assert.equal(matched[0].key, 1)
  assert.deepEqual(matched[0].children[0].children.map(node => node.key), [3])
  assert.equal(matched[0].children[0].childCount, 2)
  assert.equal(filterModuleTree(tree, '用户')[0].children[0].children.length, 2)
  assert.equal(filterModuleTree(tree, ' 3 ')[0].children[0].children[0].key, 3)
  assert.deepEqual(filterModuleTree(tree, '不存在'), [])
  assert.equal(filterModuleTree(tree, ' '), tree)
  assert.equal(tree[0].children[0].children.length, 2)
})

test('save renames only the selected module and keeps failed forms open', async () => {
  const source = readFileSync(`${directory}index.vue`, 'utf8')
  const handler = source.slice(source.indexOf('  async function saveModule('), source.indexOf('  function removeModule('))
  const compiled = ts.transpileModule(handler, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText
  const calls = []
  let fail = false
  const form = { id: 3, name: ' 登录更新 ' }
  const save = new Function('moduleForm', 'Message', 'moduleDialogRef', 'putUserModule', 'postUserModule', 'projectProductId', 'projectStore', 'loadModules',
    `${compiled}; return saveModule`)(form, { success() {}, error() {} }, { value: {
      close() { calls.push('close') }, setConfirmLoading(value) { calls.push(['loading', value]) },
    } }, async payload => { if (fail) throw new Error('example failure'); calls.push(payload) }, async () => assert.fail('rename must not create a path'),
    { value: 10 }, { invalidateAllProductModuleTreeCache() { calls.push('invalidate') } }, async () => calls.push('refresh'))
  await save()
  assert.deepEqual(calls, [{ id: 3, name: '登录更新' }, 'invalidate', 'close', 'refresh', ['loading', false]])
  calls.length = 0
  fail = true
  await save()
  assert.deepEqual(calls, [['loading', false]])
})

test('top-level create is fixed to level one and child creation uses the clicked parent ID', () => {
  assert.deepEqual(moduleCreateDraft(), { name: '', parent: null, parentName: '', level: 1 })
  assert.deepEqual(moduleCreateDraft(root), { name: '', parent: 1, parentName: '业务服务', level: 2 })
  assert.deepEqual(moduleCreateDraft(parent), { name: '', parent: 2, parentName: '用户管理', level: 3 })
})

test('tree-only workspace retains details and guarded mutation flows with local loading', () => {
  const page = readFileSync(`${directory}index.vue`, 'utf8')
  const tree = readFileSync(`${directory}ModuleTree.vue`, 'utf8')
  assert.doesNotMatch(page, /<a-table|<TableFooter|pagedModules|superior_module/)
  assert.match(tree, /MangoPanelSpin :loading="loading"/)
  assert.match(tree, /:show-line="false"/)
  assert.doesNotMatch(tree, /<a-tag|moduleLevelLabels/)
  assert.match(tree, /moduleBranchKeys\(nodes, 0\)/)
  assert.match(tree, /Number\(record.level\) < 3/)
  assert.match(tree, /label: '删除', danger: true/)
  assert.match(tree, /disabled: props.loading/)
  assert.match(page, /@detail="detailRecord = \$event"/)
  assert.match(page, /postUserModule\(/)
  assert.doesNotMatch(page, /postUserModulePath|level_[123]_name|新增模块路径/)
  assert.match(page, /新增一级模块/)
  assert.doesNotMatch(tree, />刷新<|\$emit\('refresh'\)/)
  assert.doesNotMatch(tree, /mango-module-manager__count|共 \{\{ modules.length \}\} 个模块/)
  assert.match(page, /putUserModule\(\{ id: moduleForm.id, name:/)
  assert.match(page, /deleteUserModule\(record.id\)/)
  assert.match(page, /version === requestVersion/)
  assert.match(page, /parent: moduleForm.parent/)
})

test('module levels use one, two and three centered horizontal strokes with consistent styling', () => {
  const tree = readFileSync(`${directory}ModuleTree.vue`, 'utf8')
  assert.deepEqual(exports.moduleLevelIconLines, [[12], [9, 15], [6, 12, 18]])
  assert.match(tree, /v-for="y in moduleLevelIconLines\[Number\(node.record.level\) - 1\]"/)
  assert.doesNotMatch(tree, /IconFile|IconFolder|IconApps/)
  assert.match(tree, /class="mango-module-manager__id">ID \{\{ node.key \}\}/)
  assert.doesNotMatch(tree, /#\{\{ node.key/)
  assert.match(tree, /\.mango-module-manager\s*\{[^}]*width: 100%;\s*max-width: 1120px;/)
  assert.match(tree, /\.mango-module-manager\s*\{[^}]*margin-inline: auto;/)
  assert.match(tree, /\.mango-module-manager__row--root\s*\{\s*background: var\(--m-surface\)/)
  const page = readFileSync(`${directory}index.vue`, 'utf8')
  assert.match(page, /\.mango-module-page :deep\(\.mango-table-body__content\)\s*\{\s*background: var\(--m-surface\)/)
  assert.match(tree, /mango-module-manager__row--root/)
  assert.match(tree, /\.mango-module-manager__name\s*\{[^}]*font-weight: 400/)
  assert.match(tree, /\.mango-module-manager__row--root \.mango-module-manager__name\s*\{\s*font-weight: 600/)
  assert.match(tree, /\.mango-module-manager__tree\s*\{\s*width: 100%;\s*max-width: 760px;\s*margin-inline: auto;/)
  assert.match(tree, /\.mango-module-manager__id\s*\{\s*margin-left: 24px;\s*flex: 0 0 80px;\s*text-align: left;/)
  assert.match(tree, /\.mango-module-manager__children\s*\{\s*flex: 0 0 80px;\s*box-sizing: border-box;\s*text-align: left;/)
  assert.match(tree, /\.mango-module-manager__children--empty\s*\{\s*visibility: hidden;/)
  assert.match(tree, /\.mango-module-manager__actions\s*\{\s*flex: 0 0 160px;\s*margin-left: 48px;/)
})

test('create sends one name and one parent, never a three-level path', async () => {
  const source = readFileSync(`${directory}index.vue`, 'utf8')
  const handler = source.slice(source.indexOf('  async function saveModule('), source.indexOf('  function removeModule('))
  const compiled = ts.transpileModule(handler, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText
  for (const parentId of [null, 1, 2]) {
    const payloads = []
    const save = new Function('moduleForm', 'Message', 'moduleDialogRef', 'putUserModule', 'postUserModule', 'projectProductId', 'projectStore', 'loadModules',
      `${compiled}; return saveModule`)(
      { parent: parentId, name: ' 新模块 ' }, { success() {}, error() {} }, { value: { close() {}, setConfirmLoading() {} } },
      () => assert.fail('create must not update'), async payload => payloads.push(payload),
      { value: 10 }, { invalidateAllProductModuleTreeCache() {} }, async () => {},
    )
    await save()
    assert.deepEqual(payloads, [{ project_product: 10, parent: parentId, name: '新模块' }])
  }
})

test('module page and tree templates compile', () => {
  for (const file of ['index.vue', 'ModuleTree.vue']) {
    const filename = `${directory}${file}`
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: 'module-tree' })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'module-tree',
      compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  }
})
