import test from 'node:test'
import assert from 'node:assert/strict'
import { harness, scenario } from './helpers/case-details-harness.mjs'

test('field toolbar keeps one action outside and creates a local relation group', () => {
  const h = harness('ApiCaseAssertionPanel', 'toolbarActions,draft', {
    props: {item: scenario({ass_jsonpath: []}), activeKey: '31', editLocked: false, verifying: false},
  })
  const actions = h.toolbarActions.value.filter(action => !action.hidden)
  assert.deepEqual(actions.filter(action => !action.overflow).map(action => action.label), ['增加'])
  assert.deepEqual(actions.filter(action => action.overflow).map(action => action.label), ['增加关系组', '对照结果', '一键验证'])
  actions.find(action => action.label === '增加关系组').onClick()
  assert.equal(h.draft.value.ass_jsonpath.length, 2)
  const [left, right] = h.draft.value.ass_jsonpath
  assert.equal(left.group_name, right.group_name)
  assert.equal(left.group_logic, 'OR')
  assert.equal(h.events.length, 0)
  h.props.editLocked = true
  assert.equal(h.toolbarActions.value.find(action => action.label === '增加关系组').disabled, true)
  h.close()
})
test('JSON toolbar exposes verify only and callback has no duplicate toolbar actions', () => {
  const h = harness('ApiCaseAssertionPanel', 'toolbarActions', {
    props: {item: scenario(), activeKey: '30', verifying: true},
  })
  const visible = () => h.toolbarActions.value.filter(action => !action.hidden)
  assert.equal(visible().length, 1)
  assert.equal(visible()[0].overflow, false)
  assert.equal(visible()[0].loading, true)
  assert.equal(visible()[0].disabled, true)
  h.props.activeKey = '36'
  assert.equal(visible().length, 0)
  h.close()
})
