import assert from 'node:assert/strict'
import test from 'node:test'

import { formatProjectProductPath } from '../../src/utils/business-format.ts'

test('项目产品路径包含项目名称和产品名称', () => {
  assert.equal(
    formatProjectProductPath({ name: '订单前端', project: { name: '示例项目' } }),
    '示例项目/订单前端'
  )
})

test('Pytest 产品包装对象使用真实项目产品路径', () => {
  assert.equal(
    formatProjectProductPath({
      name: 'pytest-repository',
      project_product: { name: '订单后端', project: { name: '示例项目' } },
    }),
    '示例项目/订单后端'
  )
})

test('缺少项目产品时返回占位符', () => {
  assert.equal(formatProjectProductPath(null), '-')
})
