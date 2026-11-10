import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const root = new URL('../../../src/views/report/', import.meta.url)
const source = readFileSync(new URL('details/ReportDisposition.vue', root), 'utf8')

test('排除由前端要求分类和说明，三个类型均接入且保留原始执行项', () => {
  assert.match(source, /form.is_excluded && \(!form.failure_reason \|\| !form.failure_description.trim\(\)\)/)
  for (const path of ['index.vue', 'details/index.vue', 'details/ReportDisposition.vue', 'details/ReportDispositionStatus.vue', 'details/ApiCaseTable.vue', 'details/UiCaseTable.vue', 'details/PytestCaseTable.vue']) {
    const filename = new URL(path, root).pathname
    const code = readFileSync(filename, 'utf8')
    const { descriptor, errors } = parse(code, { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: path })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: path,
      compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    if (path.endsWith('CaseTable.vue')) {
      assert.match(code, /flattenReportCases\(props.cases,/)
      assert.match(code, /label: '排查与排除', hidden: !eligible, overflow: true/)
      assert.match(code, /#default="\{ open, eligible \}"/)
      assert.match(code, /itemRow.key === 'disposition'/)
      assert.match(code, /ReportDispositionStatus :record="record.__sourceRecord"/)
    }
  }
})

test('排查状态是明细最后一个数据列，按执行项合并并显示已排查或已排除', () => {
  const config = readFileSync(new URL('details/config.ts', root), 'utf8')
  const exports = {}
  const code = ts.transpileModule(config, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  new Function('exports', 'require', code)(exports, () => ({ reactive: (value) => value }))
  for (const columns of [exports.apiColumns, exports.uiColumns, exports.pytestColumns]) {
    assert.equal(columns.at(-2).key, 'disposition')
    assert.equal(columns.at(-2).mergeCell, true)
    assert.equal(columns.at(-1).key, 'actions')
    assert.equal(columns.filter((column) => column.key === 'disposition').length, 1)
  }
  const status = readFileSync(new URL('details/ReportDispositionStatus.vue', root), 'utf8')
  assert.match(status, /record.is_excluded \? '已排除' : '已排查'/)
  assert.match(status, /failure_reason/)
  assert.match(status, /failure_description/)
})
