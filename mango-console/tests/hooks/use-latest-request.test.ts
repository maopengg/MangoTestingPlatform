import assert from 'node:assert/strict'
import test from 'node:test'

import { useLatestRequest } from '../../src/hooks/use-latest-request.ts'

test('只有最后发起的请求可以更新页面状态', () => {
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const firstRequestId = beginRequest()
  const secondRequestId = beginRequest()

  assert.equal(isLatestRequest(firstRequestId), false)
  assert.equal(isLatestRequest(secondRequestId), true)
})

test('主动失效后，当前请求不能继续更新页面状态', () => {
  const { beginRequest, isLatestRequest, invalidateRequests } = useLatestRequest()
  const requestId = beginRequest()

  invalidateRequests()

  assert.equal(isLatestRequest(requestId), false)
})
