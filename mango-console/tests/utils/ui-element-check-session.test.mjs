import assert from 'node:assert/strict'
import test from 'node:test'

import { createUiElementCheckSession } from '../../src/utils/ui-element-check-session.mjs'

test('连续两次检测分别消费各自的实时回传', () => {
  const session = createUiElementCheckSession()

  const firstToken = session.start(17, 'workspace-1')
  assert.equal(session.bindCheckId(firstToken, 'check-1'), true)
  assert.equal(
    session.accept({
      workspace_id: 'workspace-1',
      element_id: 17,
      check_id: 'check-1',
    }),
    true
  )

  const secondToken = session.start(18, 'workspace-1')
  assert.equal(session.bindCheckId(secondToken, 'check-2'), true)
  assert.equal(
    session.accept({
      workspace_id: 'workspace-1',
      element_id: 18,
      check_id: 'check-2',
    }),
    true
  )
  assert.equal(session.isActive(), false)
})

test('第二次检测不会消费第一次的重复回传', () => {
  const session = createUiElementCheckSession()

  const firstToken = session.start(17, 'workspace-1')
  session.bindCheckId(firstToken, 'check-1')
  assert.equal(
    session.accept({ workspace_id: 'workspace-1', element_id: 17, check_id: 'check-1' }),
    true
  )

  const secondToken = session.start(18, 'workspace-1')
  session.bindCheckId(secondToken, 'check-2')
  assert.equal(
    session.accept({ workspace_id: 'workspace-1', element_id: 17, check_id: 'check-1' }),
    false
  )
  assert.equal(session.isActive(secondToken), true)
  assert.equal(
    session.accept({ workspace_id: 'workspace-1', element_id: 18, check_id: 'check-2' }),
    true
  )
})

test('实时结果早于接口响应时完成态不会被接口响应重新激活', () => {
  const session = createUiElementCheckSession()
  const token = session.start(17, 'workspace-1')

  assert.equal(
    session.accept({ workspace_id: 'workspace-1', element_id: 17, check_id: 'check-fast' }),
    true
  )
  assert.equal(session.bindCheckId(token, 'check-fast'), false)
  assert.equal(session.isActive(), false)
})
