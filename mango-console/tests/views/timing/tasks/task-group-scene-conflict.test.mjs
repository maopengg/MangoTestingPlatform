import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { setupGroupEditor } from '../../../helpers/timing-task-group-editor-harness.mjs'

const source = readFileSync(new URL('../../../../src/views/timing/tasks/components/TaskGroupEditorDialog.vue', import.meta.url), 'utf8')

test('任务组生产场景双向互斥，巡检与回归可共选，旧冲突项可取消', t => {
  const h = setupGroupEditor(); t.after(h.close)
  const { groupSceneOptions, hasStabilitySceneConflict, validateTaskGroupDraft, createTaskGroupDraft } = h.load('task-group-editor-records.ts')
  const keys = ['stability_monitoring', 'production_inspection', 'production_regression']
  const form = { ...createTaskGroupDraft(), name: 'Example', project_product_id: 0, timing_strategies: [0], case_people: 0, module_ids: [0], test_envs: [2] }
  const options = keys.map(key => ({ key, title: key }))
  const disabled = () => groupSceneOptions(options, form.test_envs, form.execution_scenes).filter(item => item.disabled).map(item => item.key)
  assert.deepEqual(disabled(), [])
  form.execution_scenes = [keys[0]]
  assert.deepEqual(disabled(), keys.slice(1))
  for (const scenes of [[keys[1]], [keys[2]], keys.slice(1)]) {
    form.execution_scenes = scenes
    assert.deepEqual(disabled(), [keys[0]])
    assert.equal(hasStabilitySceneConflict(scenes), false)
    assert.equal(validateTaskGroupDraft(form), '')
  }
  form.execution_scenes = keys
  assert.deepEqual(disabled(), [])
  assert.equal(hasStabilitySceneConflict(keys), true)
  assert.match(validateTaskGroupDraft(form), /不能.*同时选择/)
  assert.match(source, /:options="mutuallyExclusiveSceneOptions"/)
  assert.match(source, /validateTaskGroupDraft\(draft\)/)
})
