import assert from 'node:assert/strict'
import test from 'node:test'
import { reactive } from 'vue'
import { config, form, record, component, deferred, flush } from './helpers/auth-config-harness.mjs'

test('independent search and edit instances cannot leak values; edit drafts do not mutate rows', () => {
  const a=config.createConditionItems(), b=config.createConditionItems()
  a[1].value='changed'
  assert.equal(b[1].value,'')
  const row=record(), draft=reactive(form.createAuthDraft(row)), fields=config.createFormItems(draft)
  fields.find(f=>f.key==='name').value='edited'
  draft.public_variable_ids.push(8)
  assert.equal(draft.name,'edited'); assert.equal(row.name,'Example auth')
  assert.deepEqual(row.public_variable_ids,[7])
  assert.equal(form.createAuthDraft(undefined,0).test_env,0)
  assert.equal(form.createAuthDraft().api_info,null)
})

test('closing or switching product ignores late public-variable and notice options', async () => {
  const pending=[], notices=[]
  const editor=component('AuthConfigEditor','formModel, publicVariableOptions, noticeOptions, publicVariablesLoading, closeEditor, onFormProjectProductChange',{
    api:{getApiAuthPublicVariables:()=>{const d=deferred();pending.push(d);return d.promise}},
    getSystemNoticeName:()=>{const d=deferred();notices.push(d);return d.promise},
  })
  editor.handle.open(record())
  editor.formModel.project_product=4;editor.onFormProjectProductChange()
  pending[1].resolve({data:[{id:9,name:'new',key:'user'}]});notices[1].resolve({data:[{key:2,title:'new'}]})
  await flush()
  pending[0].resolve({data:[{id:8,name:'old',key:'tenant'}]});notices[0].resolve({data:[{key:1,title:'old'}]})
  await flush()
  assert.deepEqual(editor.publicVariableOptions.value.map(i=>i.value),[9])
  assert.equal(editor.noticeOptions.value[0].key,2)
  editor.formModel.project_product=5;editor.onFormProjectProductChange();editor.closeEditor()
  pending[2].resolve({data:[{id:10}]});notices[2].resolve({data:[{key:3}]});await flush()
  assert.equal(editor.publicVariablesLoading.value,false)
  assert.notEqual(editor.noticeOptions.value[0]?.key,3)
  editor.cleanup()
})

test('save rejects duplicate submissions, retains failed draft and creates without previous edit ID', async () => {
  const pending=[], payloads=[]
  const save=payload=>{payloads.push(payload);const d=deferred();pending.push(d);return d.promise}
  const editor=component('AuthConfigEditor','formModel, saving, editorVisible, onDataForm, closeEditor',{api:{putApiAuthConfig:save,postApiAuthConfig:save}})
  editor.handle.open(record())
  const saving=editor.onDataForm();assert.equal(editor.saving.value,true)
  assert.equal(await editor.onDataForm(),false);assert.equal(payloads.length,1)
  pending[0].reject(new Error('failure'));assert.equal(await saving,false)
  assert.equal(editor.saving.value,false);assert.equal(editor.editorVisible.value,true)
  editor.closeEditor();editor.handle.open(undefined,4)
  Object.assign(editor.formModel,{name:'new auth',api_info:8})
  const created=editor.onDataForm();pending[1].resolve({msg:'ok'});assert.equal(await created,true)
  assert.equal('id' in payloads[1],false);assert.equal(payloads[1].status,1)
  assert.equal(payloads[1].project_product,4);assert.equal(editor.editorVisible.value,false)
  assert.equal(editor.events.length,1);editor.cleanup()
})

test('list preserves zero/multi-value filters and ignores old search responses; reset drops selection', async () => {
  const requests=[]
  const page=component('index','conditionItems, selectedRowKeys, pagination, table, doRefresh, onResetSearch',{
    api:{getApiAuthConfig:query=>{const d=deferred();requests.push({...d,query});return d.promise}},
  })
  page.conditionItems.find(f=>f.key==='test_env').value=[0,2]
  page.conditionItems.find(f=>f.key==='auth_type').value=[0]
  const first=page.doRefresh(true), second=page.doRefresh(true)
  assert.equal(requests[0].query.test_env__in,'0,2');assert.equal(requests[0].query.auth_type__in,'0')
  assert.equal('name' in requests[0].query,false)
  requests[1].resolve({data:[{id:2}],totalSize:1});await second
  requests[0].resolve({data:[{id:1}],totalSize:1});await first
  assert.deepEqual(page.table.dataList,[{id:2}]);assert.equal(page.table.tableLoading.value,false)
  page.selectedRowKeys.value=['1'];page.pagination.page=4;page.onResetSearch()
  assert.equal(page.pagination.page,1);assert.deepEqual(page.selectedRowKeys.value,[])
  assert.deepEqual(page.conditionItems.find(f=>f.key==='test_env').value,[])
  requests[2].resolve({data:[],totalSize:0});await flush();page.cleanup()
})

test('failed status/delete operations do not commit state or close confirmation; success does', async () => {
  let confirmation, fail=true
  const page=component('index','table,onModifyStatus,onDelete,selectedRowKeys',{
    Modal:{confirm:value=>{confirmation=value}},
    api:{putApiAuthConfigStatus:async()=>{if(fail)throw new Error('failure');return {code:200}},
      deleteApiAuthConfig:async()=>{if(fail)throw new Error('failure');return {msg:'ok'}}},
  })
  page.table.dataList=[record()]
  assert.equal(await page.onModifyStatus(false,1),false);assert.equal(page.table.dataList[0].status,1)
  page.selectedRowKeys.value=['1'];page.onDelete(null);page.selectedRowKeys.value=[]
  assert.equal(await confirmation.onBeforeOk(),false)
  fail=false
  assert.equal(await page.onModifyStatus(false,1),true);assert.equal(page.table.dataList[0].status,0)
  assert.equal(await confirmation.onBeforeOk(),true);page.cleanup()
})
