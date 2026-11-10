import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import test from 'node:test'
import { createSSRApp, h, toRaw } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness } from '../../helpers/case-details-harness.mjs'

const { Table } = createRequire(import.meta.url)('@arco-design/web-vue')
const root = new URL('../../../src/views/report/details/', import.meta.url)
function flatRows(component, cases) {
  const instance = harness(component, 'flatRows', {
    filename: new URL(component, root).pathname, props: { cases },
  })
  const rows = instance.flatRows.value
  instance.close()
  return rows
}

async function renderTable(data, warnHandler = () => {}) {
  const app = createSSRApp({ render: () => h(Table, {
    data, rowKey: '__rowKey', pagination: false, columns: [{ dataIndex: 'name', title: '用例' }],
  }) })
  app.config.warnHandler = warnHandler
  return renderToString(app)
}

test('the real Arco table reproduces non-iterable children without normalization', async () => {
  await assert.rejects(renderTable([{ name: 'bad', children: {} }]), /not iterable/)
})

for (const component of ['ApiCaseTable.vue', 'UiCaseTable.vue', 'PytestCaseTable.vue']) {
  test(`${component}: malformed or business children never become table subtrees`, async () => {
    for (const children of [{ count: 1 }, 'text', 42, true, null, [], [null, 'text', [], 3]]) {
      const input = [{ id: 1, name: '用例', children }]
      const before = JSON.stringify(input)
      const rows = flatRows(component, input)
      assert.equal(rows.length, 1)
      assert.equal(rows[0].children, undefined)
      assert.equal(toRaw(rows[0].__sourceRecord), input[0])
      assert.match(await renderTable(rows), /用例/)
      assert.equal(JSON.stringify(input), before)
    }
  })

  test(`${component}: valid scenarios and warnings stay flat, without losing detail payload`, async () => {
    const input = [{ id: 1, name: '父用例', warning: 1, children: [
      { id: 2, name: '场景A', status: 1, children: { response: [1, 2] } },
      { id: 3, name: '场景B', status: 0, children: [{ name: '业务字段，不是表格行' }] },
    ] }]
    const rows = flatRows(component, input)
    assert.equal(rows.length, 3)
    assert.equal(rows[0].__caseRowSpan, 3)
    assert.equal(rows[1].__caseRowSpan, 0)
    assert.equal(rows[2].status, 4)
    assert.equal(new Set(rows.map(row => row.__rowKey)).size, 3)
    for (const row of rows) assert.equal(row.children, undefined)
    assert.equal(toRaw(rows[0].__sourceRecord.children[0]), input[0].children[0])
    const html = await renderTable(rows)
    assert.match(html, /场景A/)
    assert.match(html, /场景B/)
    assert.doesNotMatch(html, /业务字段，不是表格行/)
  })

  test(`${component}: invalid root entries do not crash and SFC still compiles`, () => {
    for (const value of [undefined, null, {}, '', false]) assert.deepEqual(flatRows(component, value), [])
    assert.equal(flatRows(component, [null, 1, [], 'bad', { id: 1, name: '正常' }]).length, 1)
    const filename = new URL(component, root).pathname
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: component })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: component,
      compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  })
}
