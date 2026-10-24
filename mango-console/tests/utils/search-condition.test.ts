import assert from 'node:assert/strict'
import test from 'node:test'
import type { FormItem } from '@/types/components'
import { getFormItems } from '../../src/utils/datacleaning.ts'
import { enableMultiSelectSearch } from '../../src/utils/search-condition.ts'

test('普通枚举字段升级为多选，依赖型字段保持单选', () => {
  const items = [
    { key: 'test_env', type: 'cascader', value: '' },
    { key: 'execution_scene', type: 'select', value: '' },
    { key: 'project_product', type: 'cascader', value: '' },
    { key: 'module', type: 'select', value: '' },
  ] as FormItem[]

  enableMultiSelectSearch(items)

  assert.deepEqual(
    { multiple: items[0].multiple, searchOperator: items[0].searchOperator, value: items[0].value },
    { multiple: true, searchOperator: 'in', value: [] }
  )
  assert.deepEqual(
    { multiple: items[1].multiple, searchOperator: items[1].searchOperator, value: items[1].value },
    { multiple: true, searchOperator: 'in', value: [] }
  )
  assert.equal(items[2].value, '')
  assert.equal(items[2].multiple, undefined)
  assert.equal(items[3].multiple, undefined)
})

test('多选值使用 in 查询并可恢复为空数组', () => {
  const items = [{ key: 'test_env', type: 'cascader', value: '' }] as FormItem[]
  enableMultiSelectSearch(items)
  items[0].value = [1, 2]

  assert.deepEqual(getFormItems(items), { test_env__in: '1,2' })
  items[0].reset?.()
  assert.deepEqual(items[0].value, [])
})
