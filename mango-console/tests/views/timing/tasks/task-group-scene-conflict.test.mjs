import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../../../../src/views/timing/tasks/components/TaskGroupManager.vue', import.meta.url), 'utf8')
const start = source.indexOf('  function hasStabilitySceneConflict(')
const end = source.indexOf('  const moduleParentMap', start)
const code = ts.transpileModule(source.slice(start, end), {}).outputText

test('任务组生产场景双向互斥，巡检与回归可共选，旧冲突项可取消', () => {
  const keys = ['stability_monitoring', 'production_inspection', 'production_regression']
  const form = { execution_scenes: [] }
  const options = { value: keys.map((key) => ({ key, title: key })) }
  const state = new Function('form', 'selectableSceneOptions', 'computed',
    `${code}; return { mutuallyExclusiveSceneOptions, hasStabilitySceneConflict }`)(form, options,
    (getter) => ({ get value() { return getter() } }))
  const disabled = () => state.mutuallyExclusiveSceneOptions.value.filter((item) => item.disabled).map((item) => item.key)
  assert.deepEqual(disabled(), [])
  form.execution_scenes = [keys[0]]
  assert.deepEqual(disabled(), keys.slice(1))
  for (const scenes of [[keys[1]], [keys[2]], keys.slice(1)]) {
    form.execution_scenes = scenes
    assert.deepEqual(disabled(), [keys[0]])
    assert.equal(state.hasStabilitySceneConflict(scenes), false)
  }
  form.execution_scenes = keys
  assert.deepEqual(disabled(), [])
  assert.equal(state.hasStabilitySceneConflict(keys), true)
  assert.match(source, /:options="mutuallyExclusiveSceneOptions"/)
  assert.match(source, /if \(hasStabilitySceneConflict\(form.execution_scenes\)\) return/)
})
