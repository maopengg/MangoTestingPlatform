import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'
import { harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/pytest/case')
function setup(detail = null) {
  return harness('PytestExecutionResultDetail', 'selectedCaseKey,detailState,sourceSnapshot,executionCases,selectedCase,emptyDescription', { base, props: { detail } })
}

test('accepts execution protocol list/object/null and legacy result containers without mutating evidence', () => {
  const h = setup()
  const { executionDetail } = h.load('execution-result.ts')
  const evidence = { name: 'test_example', status: 'passed', attachments: [{ name: 'data', source: 'false' }], custom: { value: 0 } }
  for (const result_data of [[evidence], evidence, { children: [evidence] }, { cases: [evidence] }, { results: [evidence] }]) {
    const parsed = executionDetail({ id: 0, result_data })
    assert.equal(parsed.id, 0)
    assert.equal(parsed.cases.length, 1)
    assert.equal(parsed.cases[0].payload, evidence)
    assert.equal(parsed.cases[0].name, 'test_example')
    assert.equal(parsed.malformed, false)
    assert.equal(evidence.custom.value, 0)
  }
  for (const result_data of [null, undefined, [], {}, { children: [] }]) {
    const parsed = executionDetail({ result_data })
    assert.deepEqual(parsed.cases, [])
    assert.equal(parsed.malformed, false)
  }
  h.close()
})

test('invalid outer and case shapes are explicit, with no primitive masquerading as a case', () => {
  const h = setup()
  const { executionDetail } = h.load('execution-result.ts')
  for (const value of [false, 0, 'bad', []]) assert.equal(executionDetail(value).malformed, true)
  for (const result_data of [false, 0, 'bad', [false, 2, 'bad']]) {
    const parsed = executionDetail({ result_data })
    assert.equal(parsed.malformed, true)
    assert.deepEqual(parsed.cases, [])
  }
  h.props.detail = { result_data: [{ name: 'valid' }, 7, null] }
  assert.equal(h.detailState.value.malformed, true)
  assert.equal(h.executionCases.value.length, 1)
  assert.equal(h.selectedCase.value.name, 'valid')
  h.close()
})

test('source summary is a finite whitelist and preserves project zero without stringifying objects', () => {
  const h = setup({ source_snapshot: { repository_name: 'Example repository', pytest_project_id: 0, pytest_project_name: null, branch: 'main', commit_hash: '0123456789abcdef', file_path: 'tests/test_example.py', token: 'not-for-summary' } })
  assert.deepEqual({ ...h.sourceSnapshot.value }, { repositoryName: 'Example repository', projectName: '项目 0', branch: 'main', commit: '0123456789', filePath: 'tests/test_example.py' })
  h.props.detail = { source_snapshot: { repository_name: {}, pytest_project_id: false, commit_hash: 12 } }
  assert.equal(h.sourceSnapshot.value.projectName, '-')
  assert.equal(h.sourceSnapshot.value.commit, '-')
  assert.equal(h.sourceSnapshot.value.repositoryName, '默认 Pytest 仓库')
  h.props.detail = { source_snapshot: {} }
  assert.equal(h.sourceSnapshot.value, null)
  h.close()
})

test('allure and numeric statuses retain failure zero; booleans and null remain unknown', () => {
  const h = setup()
  const { resultStatus, executionDetail } = h.load('execution-result.ts')
  for (const [value, expected] of [[0, '失败'], [1, '通过'], [3, '进行中'], ['broken', '失败'], ['FAILED', '失败'], ['success', '通过'], ['skipped', '跳过'], [null, '未知'], [false, '未知'], ['0', '未知']]) {
    const parsed = executionDetail({ result_data: [{ status: value }] })
    assert.equal(resultStatus(parsed.cases[0].status).text, expected)
  }
  h.close()
})

test('initially selects failed case; user selection survives same-record refresh, resets across records and removal', () => {
  const rows = [{ name: 'passed', status: 1 }, { name: 'failed', status: 0 }]
  const h = setup({ id: 1, result_data: rows })
  assert.equal(h.selectedCase.value.name, 'failed')
  h.selectedCaseKey.value = h.executionCases.value[0].key
  h.props.detail = { id: 1, result_data: rows.map(row => ({ ...row })) }
  assert.equal(h.selectedCase.value.name, 'passed')
  h.props.detail = { id: 2, result_data: rows }
  assert.equal(h.selectedCase.value.name, 'failed')
  h.props.detail = { id: 1, result_data: rows.slice(0, 1) }
  assert.equal(h.selectedCase.value.name, 'passed')
  h.props.detail = null
  assert.equal(h.selectedCase.value, null)
  assert.equal(h.selectedCaseKey.value, '')
  h.close()
})

test('result empty states distinguish no selection, cleanup, empty and malformed responses', () => {
  const h = setup()
  assert.match(h.emptyDescription.value, /请选择左侧/)
  h.props.detail = { result_cleaned: true, result_data: null }
  assert.match(h.emptyDescription.value, /保留策略清理/)
  h.props.detail = { result_cleaned: false, result_data: [] }
  assert.match(h.emptyDescription.value, /没有生成/)
  h.props.detail = { result_data: 'bad' }
  assert.match(h.emptyDescription.value, /格式异常/)
  h.props.detail = { result_cleaned: 'false', result_data: [] }
  assert.match(h.emptyDescription.value, /没有生成/)
  h.close()
})

test('duplicate names remain independently selectable and invalid display fields use finite fallbacks', () => {
  const h = setup({ result_data: [{ name: 'same' }, { name: 'same' }, { name: {}, title: 'title', fullName: false, nodeid: 'module::test' }] })
  assert.equal(new Set(h.executionCases.value.map(row => row.key)).size, 3)
  h.selectedCaseKey.value = h.executionCases.value[1].key
  assert.equal(h.selectedCase.value, h.executionCases.value[1])
  assert.equal(h.executionCases.value[2].name, 'title')
  assert.equal(h.executionCases.value[2].description, 'module::test')
  h.close()
})

test('actual result detail script and template compile', () => {
  const filename = path.join(base, 'components/PytestExecutionResultDetail.vue')
  const { descriptor } = parse(readFileSync(filename, 'utf8'))
  const script = compileScript(descriptor, { id: 'pytest-result-detail' })
  const result = compileTemplate({ source: descriptor.template.content, filename, id: 'pytest-result-detail', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(result.errors, [])
})
