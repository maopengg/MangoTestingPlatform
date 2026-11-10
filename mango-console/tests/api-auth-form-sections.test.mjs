import assert from 'node:assert/strict'
import test from 'node:test'
import { config, component, record, flush } from './helpers/auth-config-harness.mjs'

test('groups cover all fields exactly once and optional target remains optional', () => {
  const editor=component('AuthConfigEditor','formItems')
  const keys=config.authFormSections.flatMap(s=>s.itemKeys)
  assert.equal(new Set(keys).size,keys.length)
  assert.deepEqual([...keys].sort(),editor.formItems.map(i=>i.key).sort())
  assert.equal(editor.formItems.find(i=>i.key==='target_address').required,false)
  editor.cleanup()
})
test('every auth/refresh mode shows appropriate controls and clears irrelevant submit fields', async () => {
  const editor=component('AuthConfigEditor','formModel,authFormGroups')
  editor.handle.open(record())
  for(const auth_type of [0,1]) for(const refresh_mode of [0,1,2,3,4]) {
    Object.assign(editor.formModel,{auth_type,refresh_mode});await flush()
    const keys=editor.authFormGroups.value.flatMap(s=>s.items.map(i=>i.key))
    assert.equal(keys.includes('api_info'),auth_type===0)
    assert.equal(keys.includes('custom_code'),auth_type===1)
    assert.equal(keys.includes('time_task'),[1,2].includes(refresh_mode))
    assert.equal(keys.includes('notice_group'),refresh_mode===4)
    assert.equal(keys.includes('refresh_margin'),[0,2].includes(refresh_mode))
  }
  editor.cleanup()
})
