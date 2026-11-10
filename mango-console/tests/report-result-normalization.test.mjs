import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'

const cache = new Map()
function load(filename) {
  if (cache.has(filename)) return cache.get(filename)
  const exports = {}; cache.set(filename, exports)
  const code = ts.transpileModule(readFileSync(filename, 'utf8'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText
  new Function('exports', 'require', code)(exports, id => load(id.startsWith('@/') ? path.resolve('src', id.slice(2)) + '.ts' : path.resolve(path.dirname(filename), id) + '.ts'))
  return exports
}
const { buildReportResult, parseReportResultOptions, parseReportResult } = load(path.resolve('src/views/report/details/report-result.ts'))

test('执行历史边界保留 ID 0 和长整数字符串，拒绝错误码、重复和不合法标识', () => {
  const options = parseReportResultOptions({ code: 200, data: [{ id: 0, test_suite_detail_id: 0, is_latest: true }, { id: '9223372036854775807' }] })
  assert.equal(options[0].id, '0'); assert.equal(options[0].test_suite_detail_id, '0'); assert.equal(options[0].is_latest, true)
  assert.equal(options[1].id, '9223372036854775807')
  for (const value of [{ code: 403, data: [] }, { code: 200, data: null }, { code: 200, data: [{ id: 1 }, { id: '1' }] }, { code: 200, data: [{ id: false }] }]) {
    assert.throws(() => parseReportResultOptions(value))
  }
  assert.equal(parseReportResult({ code: 200, data: null }, '1'), null)
  assert.throws(() => parseReportResult({ code: 200, data: { id: 2 } }, '1'))
})

test('参数 ID 0 优先匹配，状态 0、空缓存和 false 不被父记录覆盖', () => {
  const source = { id: 8, parameter_id: 0, case_type: 0 }
  const detail = { id: 0, test_time: 10, cache_data: { old: true }, data_factory_cache_data: { old: true }, children: [
    { id: 8, name: 'wrong' },
    { parameter_id: '0', name: 'selected', status: 0, test_time: 0, cache_data: false, data_factory_cache_data: [] },
  ] }
  const result = buildReportResult(source, detail, '2')
  assert.equal(result.name, 'selected'); assert.equal(result.status, 0)
  assert.equal(result.test_time, 0); assert.equal(result.cache_data, false)
  assert.deepEqual(result.data_factory_cache_data, [])
  assert.equal(result.test_suite_detail_id, 0); assert.equal(result.__caseSourceId, 0)
  assert.equal(result.children[0].name, 'selected'); assert.equal(result.element_result_list[0].name, 'selected')
  assert.equal(detail.children.length, 2); assert.equal(source.id, 8)
})

test('保留 Pytest UUID 和长整数串匹配，不转换为有精度损失的数字', () => {
  for (const id of ['fixture-uuid-1', '9223372036854775807']) {
    const result = buildReportResult({ id, case_type: 2 }, { children: [{ id: 'other' }, { id, fullName: 'selected' }] }, '0')
    assert.equal(result.id, id); assert.equal(result.fullName, 'selected')
    assert.equal(result.children, undefined)
  }
})

test('参数未命中仍按行 ID、名称和首条结构化结果依次回退', () => {
  const detail = { children: [null, 'legacy text', { id: 1, name: 'first' }, { id: 2, name: 'second' }] }
  assert.equal(buildReportResult({ id: '2', parameter_id: 99 }, detail, '2').name, 'second')
  assert.equal(buildReportResult({ name: 'second' }, detail, '2').id, 2)
  assert.equal(buildReportResult({}, detail, '2').name, 'first')
})

test('UI 继承明细元数据，空数组、空对象和空字符串保留实际含义', () => {
  const detail = { id: 4, type: 0, test_time: 7, test_object: 'parent', video_path: 'parent.mp4', cache_data: { parent: 1 }, children: [
    { name: 'child', test_object: '', video_path: '', cache_data: {}, data_factory_cache_data: false },
  ] }
  const result = buildReportResult({}, detail, '2')
  assert.equal(result.test_time, 7); assert.equal(result.test_object, ''); assert.equal(result.video_path, '')
  assert.deepEqual(result.cache_data, {}); assert.equal(result.data_factory_cache_data, false)
})

test('缺少结果时使用明确来源元数据，非对象和错误子节点不触发异常', () => {
  for (const value of [null, undefined, false, 'legacy', []]) {
    const result = buildReportResult({ name: 'source', status: 0, test_suite_detail_id: 0 }, value, '2')
    assert.equal(result.name, 'source'); assert.equal(result.status, 0); assert.equal(result.test_suite_detail_id, 0)
  }
  assert.equal(buildReportResult(null, { type: 2, statusDetails: { message: 'failure' } }, '0').error_message, 'failure')
})
