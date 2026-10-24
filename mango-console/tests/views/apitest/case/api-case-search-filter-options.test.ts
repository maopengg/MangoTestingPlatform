import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveApiCaseSearchOptions } from '../../../../src/views/apitest/case/api-case-search-filter-options'

const users = [{ key: 1, title: '张三' }]
const enumStore = {
  task_status: [{ key: 1, title: '已完成' }],
  case_level: [{ key: 2, title: 'P2' }],
  api_case_scenario_type: [{ key: 3, title: '功能' }],
}

test('负责人和更新人始终使用用户列表', () => {
  assert.equal(
    resolveApiCaseSearchOptions({ key: 'case_people', optionItems: [] }, users, enumStore),
    users
  )
  assert.equal(
    resolveApiCaseSearchOptions({ key: 'update_user', optionItems: [] }, users, enumStore),
    users
  )
})

test('空 optionItems 不覆盖枚举选项', () => {
  assert.equal(
    resolveApiCaseSearchOptions({ key: 'status', optionItems: [] }, users, enumStore),
    enumStore.task_status
  )
  assert.equal(
    resolveApiCaseSearchOptions({ key: 'level', optionItems: [] }, users, enumStore),
    enumStore.case_level
  )
  assert.equal(
    resolveApiCaseSearchOptions({ key: 'scenario_type', optionItems: [] }, users, enumStore),
    enumStore.api_case_scenario_type
  )
})

test('静态筛选项保留自身选项', () => {
  const options = [{ value: 'published', label: '已发布' }]
  assert.equal(
    resolveApiCaseSearchOptions(
      { key: 'publication_status', optionItems: options },
      users,
      enumStore
    ),
    options
  )
})
