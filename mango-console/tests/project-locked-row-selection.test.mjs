import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'

const source = readFileSync(new URL('../src/hooks/use-project-locked-row-selection.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText
const row = (id, projectId = 3) => ({ id, project: { id: projectId, name: `示例项目${projectId}` } })

function setup(t, initialRows, options) {
  const rows = vue.ref(initialRows), messages = [], exports = {}
  new Function('exports', 'require', compiled)(exports, name => {
    if (name === 'vue') return vue
    if (name === '@arco-design/web-vue') return { Message: { warning: message => messages.push(message) } }
    if (name === '@/hooks/table') return { useRowSelection: () => ({ selectedRowKeys: vue.ref([]), showCheckedAll: vue.ref(true) }) }
    throw new Error(`Unexpected import ${name}`)
  })
  const scope = vue.effectScope()
  t.after(() => scope.stop())
  const hook = scope.run(() => exports.useProjectLockedRowSelection(() => rows.value, value => value?.project, options))
  return { ...hook, rows, messages }
}

test('same-project select-all ignores stale page IDs without cross-project warning', t => {
  const h = setup(t, [row(1), row(2)])
  h.selectedRowKeys.value = [999]
  h.onSelectionChange([999, 1, 2])
  assert.deepEqual(h.selectedRowKeys.value, [1, 2])
  assert.equal(h.validateSingleProject(), true)
  assert.deepEqual(h.messages, [])
})

test('numeric/string project and row IDs use the same identity', t => {
  const h = setup(t, [row(1, 3), row('2', '3')])
  h.onSelectionChange(['1'])
  assert.equal(h.selectableDataList.value[1].disabled, false)
  h.onSelectionChange(['1', 2])
  assert.deepEqual(h.selectedRowKeys.value, ['1', 2])
  assert.equal(h.validateSingleProject(), true)
  assert.deepEqual(h.messages, [])
})

test('real cross-project selection is still rejected and unrelated rows are disabled', t => {
  const h = setup(t, [row(1), row(2), row(3, 4)])
  h.onSelectionChange([1])
  assert.equal(h.selectableDataList.value[2].disabled, true)
  h.onSelectionChange([1, 2, 3])
  assert.deepEqual(h.selectedRowKeys.value, [1, 2])
  assert.equal(h.messages.length, 1)
  assert.match(h.messages[0], /同一项目/)
})

test('existing project lock wins even when select-all key order changes', t => {
  const h = setup(t, [row(1), row(2, 4)])
  h.onSelectionChange([2])
  h.onSelectionChange([1, 2])
  assert.deepEqual(h.selectedRowKeys.value, [2])
  assert.match(h.messages[0], /示例项目4/)
})

test('pagination clears off-page selection and unlocks the next project', async t => {
  const h = setup(t, [row(1)])
  h.onSelectionChange([1])
  h.rows.value = [row(2, 4)]
  await vue.nextTick()
  assert.deepEqual(h.selectedRowKeys.value, [])
  assert.equal(h.selectableDataList.value[0].disabled, false)
  h.onSelectionChange([2])
  assert.deepEqual(h.selectedRowKeys.value, [2])
  assert.deepEqual(h.messages, [])
})

test('polling and in-place list replacement preserve only still-visible IDs', async t => {
  const h = setup(t, [row(1), row(2)])
  h.onSelectionChange([1, 2])
  h.rows.value.length = 0
  h.rows.value.push(row(1), row(2))
  await vue.nextTick()
  assert.deepEqual(h.selectedRowKeys.value, [1, 2])
  h.rows.value = [row(2), row(3)]
  await vue.nextTick()
  assert.deepEqual(h.selectedRowKeys.value, [2])
  assert.deepEqual(h.messages, [])
})

test('execution validation rejects stale keys with a distinct message before the watcher flushes', t => {
  const h = setup(t, [row(1)])
  h.selectedRowKeys.value = [1, 999]
  assert.equal(h.validateSingleProject(), false)
  assert.deepEqual(h.selectedRowKeys.value, [1])
  assert.match(h.messages[0], /已不在当前列表/)
  assert.doesNotMatch(h.messages[0], /同一项目/)
})

test('missing project information cannot pass execution validation', t => {
  const h = setup(t, [row(1), { id: 2 }])
  h.onSelectionChange([1, 2])
  assert.equal(h.validateSingleProject(), false)
  assert.match(h.messages[0], /缺少项目归属信息/)
  assert.doesNotMatch(h.messages[0], /多个项目/)
})

test('execution guard still rejects injected mixed-project selections', t => {
  const h = setup(t, [row(1), row(2, 4)])
  h.selectedRowKeys.value = [1, 2]
  assert.equal(h.validateSingleProject(), false)
  assert.match(h.messages[0], /来自多个项目/)
})

test('clearing selection allows another project and duplicate keys do not cause warnings', t => {
  const h = setup(t, [row(1), row(2, 4)])
  h.onSelectionChange([1])
  h.onSelectionChange([])
  h.onSelectionChange([2, '2'])
  assert.deepEqual(h.selectedRowKeys.value, [2])
  assert.deepEqual(h.messages, [])
})

test('header product-scope reuse preserves custom validation labels', t => {
  const h = setup(t, [row(1), row(2, 4)], { scopeLabel: '产品', actionLabel: '绑定', itemLabel: '请求头' })
  h.onSelectionChange([1, 2])
  assert.match(h.messages[0], /批量绑定只能选择同一产品下的请求头/)
})
