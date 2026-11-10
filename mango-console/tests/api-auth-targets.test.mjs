import assert from 'node:assert/strict'
import test from 'node:test'
import { form, record, component, deferred, flush } from './helpers/auth-config-harness.mjs'

test('submission normalizes optional fields and product leaf without mutating the draft', () => {
  const draft=form.createAuthDraft(record({auth_type:1,refresh_mode:3}))
  Object.assign(draft,{project_product:[1,4],target_address:null,public_variable_ids:null,time_task:2,notice_group:3})
  const result=form.normalizeSubmitValue(draft)
  assert.equal(result.project_product,4);assert.equal(result.target_address,'')
  assert.deepEqual(result.public_variable_ids,[]);assert.equal(result.time_task,null)
  assert.equal(result.notice_group,null);assert.equal(result.api_info,null)
  assert.equal(draft.time_task,2)
  const chosen=form.normalizeSubmitValue({...draft,target_address:'https://example.org',public_variable_ids:[7]})
  assert.equal(chosen.target_address,'https://example.org');assert.deepEqual(chosen.public_variable_ids,[7])
})
test('targets accept environment zero and product scope; old or closed requests cannot overwrite', async () => {
  const pending=[], calls=[]
  const editor=component('AuthConfigEditor','formModel,targetOptions,targetsLoading,onAuthVariableContextChange,closeEditor',{
    api:{getApiAuthTargets:query=>{calls.push(query);const d=deferred();pending.push(d);return d.promise}},
  })
  editor.handle.open(record());assert.deepEqual(calls[0],{project_product:2,test_env:0})
  editor.formModel.project_product=[1,4];editor.onAuthVariableContextChange()
  pending[1].resolve({data:[{value:'https://example.org',label:'new'}]});await flush()
  pending[0].resolve({data:[{value:'https://example.com',label:'old'}]});await flush()
  assert.equal(editor.targetOptions.value[0].label,'new')
  editor.onAuthVariableContextChange();editor.closeEditor();pending[2].resolve({data:[{label:'closed'}]});await flush()
  assert.equal(editor.targetOptions.value.length,0);assert.equal(editor.targetsLoading.value,false)
  editor.cleanup()
})
