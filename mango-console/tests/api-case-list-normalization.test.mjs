import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync, readdirSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { ref } from 'vue'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/apitest/case')
const tableModule = { useTableIndexColumn: () => ({ key: 'index' }), useTableColumn: items => items }
function panel(name, bindings, overrides = {}) {
  return harness(name, bindings, { base, ...overrides, modules: { '@/hooks/table': tableModule, ...overrides.modules } })
}
const row = (id = 1) => ({ id, name: 'Example case', project_product: {id: 2}, module: {id: 3},
  case_people: {id: 4}, level: 0, scenario_layer: 0, scenario_type: 0, scenario_tags: ['regression'],
  parametrize: [{name:'suite',parametrize:[{key:'input',value:null,test_envs:[0]}]}] })

test('list and owned panels compile with shared suite drawer', () => {
  const files = [path.join(base,'index.vue'), ...readdirSync(path.join(base,'components')).filter(f=>f.endsWith('.vue')).map(f=>path.join(base,'components',f)), path.resolve('src/components/forms/ParametrizeDrawer.vue')]
  for (const filename of files) {
    const {descriptor, errors}=parse(readFileSync(filename,'utf8'))
    assert.deepEqual(errors, [], filename)
    const script=compileScript(descriptor,{id:filename})
    const result=compileTemplate({source:descriptor.template.content,filename,id:filename,compilerOptions:{bindingMetadata:script.bindings}})
    assert.deepEqual(result.errors, [], filename)
  }
})

test('search factories isolate multiple values and metadata preserves zero without inheriting navigation sentinel', () => {
  const state=panel('ApiCaseMetadataEditor','draft',{props:{userOptions:[]}})
  const {createConditionItems}=state.load('config.ts')
  const first=createConditionItems(),second=createConditionItems()
  const levels=items=>items.find(i=>i.key==='level')
  levels(first).value=[0,1]
  assert.deepEqual(levels(second).value,[])
  const {createMetadataDraft,metadataPayload}=state.load('metadata.ts')
  assert.equal(createMetadataDraft(undefined,{module:'__all__'}).module,null)
  assert.equal(metadataPayload(createMetadataDraft(row())).level,0)
  state.close()
})

test('metadata cancel and reopening never mutate source or carry previous record identity', () => {
  const state=panel('ApiCaseMetadataEditor','draft,editingId,visible,open,close',{props:{userOptions:[]}})
  const source=row()
  state.open(source)
  state.draft.scenario_tags.push('extra')
  state.draft.name='Edited'
  state.exposed.close()
  assert.equal(source.name,'Example case')
  assert.deepEqual(source.scenario_tags,['regression'])
  state.open(undefined,{projectProduct:8,module:9})
  assert.equal(state.editingId.value,null)
  assert.equal(state.draft.name,'')
  assert.equal(state.draft.project_product,8)
  state.close()
})

test('metadata save uses a fixed metadata payload, blocks duplicate writes and keeps failed input', async () => {
  const pending=deferred(),writes=[]
  const state=panel('ApiCaseMetadataEditor','draft,saving,visible,open,save',{props:{userOptions:[]},api:{putApiCase:payload=>{writes.push(payload);return pending.promise}}})
  state.open({...row(),front_sql:[{value:'select 1'}]})
  const save=state.save()
  assert.equal(state.saving.value,true)
  assert.equal(await state.save(),false)
  state.draft.name='Changed after submission'
  assert.equal(writes.length,1)
  assert.equal(writes[0].name,'Example case')
  assert.equal('front_sql' in writes[0],false)
  assert.equal('parametrize' in writes[0],false)
  pending.reject(Error('offline'));await save
  assert.equal(state.visible.value,true)
  assert.equal(state.saving.value,false)
  assert.equal(state.draft.name,'Changed after submission')
  state.close()
})

test('metadata requires execution scenes for both creation and editing before requesting a save', async () => {
  const writes=[]
  const state=panel('ApiCaseMetadataEditor','draft,open,save,formItems',{props:{userOptions:[]},api:{
    postApiCase:async payload=>{writes.push(payload);return {msg:'ok'}},
    putApiCase:async payload=>{writes.push(payload);return {msg:'ok'}},
  }})
  assert.equal(state.formItems.find(item=>item.key==='scenario_tags').required,true)
  for (const editing of [false,true]) {
    state.open(editing ? row() : undefined)
    Object.assign(state.draft,{...row(),project_product:2,module:3,case_people:4})
    for (const empty of [[],null,undefined]) {
      state.draft.scenario_tags=empty
      assert.equal(await state.save(),false)
      assert.equal(writes.length,editing ? 1 : 0)
    }
    state.draft.scenario_tags=['regression']
    assert.equal(await state.save(),true)
  }
  assert.equal(writes.length,2)
  state.close()
})

test('closed metadata editor ignores a late successful write', async () => {
  const pending=deferred()
  const state=panel('ApiCaseMetadataEditor','open,save,visible',{props:{userOptions:[]},api:{putApiCase:()=>pending.promise}})
  state.open(row());const save=state.save();state.exposed.close()
  pending.resolve({msg:'ok'});await save
  assert.deepEqual(state.events,[])
  state.close()
})

test('task options accept only the latest product response and clearing cancels old results', async () => {
  const requests=[]
  const state=panel('ApiCaseTaskBindingModal','open,draft,taskOptions,optionsLoading,loadTasks',{api:{getSystemTasksName:()=>{const pending=deferred();requests.push(pending);return pending.promise}}})
  state.open([{case_id:1,case_release_id:10}])
  state.draft.projectProduct=2;const old=state.loadTasks()
  state.draft.projectProduct=3;const current=state.loadTasks()
  requests[1].resolve({data:[{key:30,title:'Current'}]});await current
  requests[0].resolve({data:[{key:20,title:'Old'}]});await old
  assert.equal(state.taskOptions.value[0].key,30)
  state.draft.projectProduct=4;const late=state.loadTasks()
  state.draft.projectProduct=null;await state.loadTasks()
  requests[2].resolve({data:[{key:40}]});await late
  assert.deepEqual(state.taskOptions.value,[])
  assert.equal(state.optionsLoading.value,false)
  state.close()
})

test('task binding freezes selected releases and target task, failure keeps window for retry', async () => {
  const pending=deferred(),writes=[]
  const state=panel('ApiCaseTaskBindingModal','open,save,draft,visible,saving',{api:{postSystemTasksBatchSetCaseVersions:(...args)=>{writes.push(args);return pending.promise}}})
  const items=[{case_id:1,case_release_id:10}]
  state.open(items);items[0].case_release_id=99
  state.draft.projectProduct=2;state.draft.task=30
  const save=state.save();state.draft.task=31;await state.save()
  assert.deepEqual(writes,[[[{case_id:1,case_release_id:10}],30,1]])
  pending.reject(Error('offline'));await save
  assert.equal(state.visible.value,true);assert.equal(state.saving.value,false)
  state.close()
})

test('suite drafts isolate original arrays and null/environment zero survive save', async () => {
  const writes=[]
  const state=panel('ApiCaseParametrizePanel','open,draft,save,visible',{api:{putApiCase:async payload=>{writes.push(payload);return {msg:'ok'}}}})
  const source=row();state.open(source)
  state.draft.value[0].name='Local suite'
  assert.equal(source.parametrize[0].name,'suite')
  await state.save(state.draft.value)
  assert.equal(writes[0].parametrize[0].parametrize[0].value,null)
  assert.deepEqual(writes[0].parametrize[0].parametrize[0].test_envs,[0])
  assert.equal(state.visible.value,false)
  state.close()
})

test('suite failures retain the drawer and empty suites clear only the fixed original case', async () => {
  const writes=[];let fail=true
  const state=panel('ApiCaseParametrizePanel','open,draft,save,visible,saving',{api:{putApiCase:async payload=>{writes.push(payload);if(fail)throw Error('offline');return {msg:'ok'}}}})
  state.open(row(12));await state.save(state.draft.value)
  assert.equal(state.visible.value,true);assert.equal(state.saving.value,false)
  fail=false;await state.save([{name:'',parametrize:[{key:'',value:''}]}])
  assert.deepEqual(writes[1],{id:12,parametrize:[]})
  assert.equal(state.visible.value,false)
  state.close()
})

test('related task close and case switch ignore late reads', async () => {
  const requests=[]
  const state=panel('ApiCaseRelatedTasksDrawer','open,boundTaskList,boundTaskLoading',{api:{getApiCaseRelatedTasks:()=>{const pending=deferred();requests.push(pending);return pending.promise}}})
  const old=state.open(row(1)),current=state.open(row(2))
  requests[1].resolve({data:[{task_id:2}]});await current
  requests[0].resolve({data:[{task_id:1}]});await old
  assert.equal(state.boundTaskList.value[0].task_id,2)
  const late=state.open(row(3));state.exposed.close()
  requests[2].resolve({data:[{task_id:3}]});await late
  assert.deepEqual(state.boundTaskList.value,[])
  assert.equal(state.boundTaskLoading.value,false)
  state.close()
})

test('only manual related tasks can be unbound, a failed confirmation stays open', async () => {
  const confirmations=[],writes=[]
  const state=panel('ApiCaseRelatedTasksDrawer','open,unbindBoundTask,boundTaskList',{Modal:{confirm:options=>confirmations.push(options)},api:{getApiCaseRelatedTasks:async()=>({data:[]}),deleteSystemTasksRunCase:async id=>{writes.push(id);throw Error('offline')}}})
  await state.open(row())
  state.unbindBoundTask({relation_type:'automatic',task_id:1,task_detail_id:11})
  assert.equal(confirmations.length,0)
  state.unbindBoundTask({relation_type:'manual',task_id:2,task_detail_id:12})
  assert.equal(await confirmations[0].onBeforeOk(),false)
  assert.deepEqual(writes,[12])
  state.close()
})

test('delete confirmation freezes selected IDs and failed deletion does not close it', async () => {
  let confirmation;const ids=ref([1,2]),writes=[]
  const remove=method('onDelete',{selectedRowKeys:ids,pageVersion:1,pageActive:ref(true),Modal:{confirm:o=>confirmation=o},Message:{success(){},error(){}},deleteApiCase:async value=>{writes.push(value);throw Error('offline')},onAssetsChanged(){}},path.join(base,'index.vue'))
  remove(null);ids.value=[3]
  assert.equal(await confirmation.onBeforeOk(),false)
  assert.deepEqual(writes,[[1,2]])
})

test('batch submission validates frozen rows despite refreshed list and rejects duplicates', async () => {
  const pending=deferred(),writes=[],running=ref(false),ids=ref([1])
  const submit=method('onConfirmCaseBatchRun',{pendingBatchRunCaseIds:ids,pendingBatchRows:ref([{id:1,name:'Original',prepublished_revision_id:11}]),pageVersion:1,pageActive:ref(true),Message:{success(){},error(){},warning(){throw Error('must use frozen rows')}},batchRunModalRef:ref({setConfirmLoading(){},close(){}}),caseRunning:running,postApiCaseBatchRun:(...args)=>{writes.push(args);return pending.promise},doRefresh(){},hasPublishedCaseVersion:()=>true},path.join(base,'index.vue'))
  const config={executionName:'Example',testEnv:0,apiConcurrencyLimit:null,executionVersion:'prepublished'}
  const save=submit(config);ids.value=[3];await submit(config)
  assert.deepEqual(writes[0],[[1],0,'Example',null,'prepublished'])
  assert.equal(writes.length,1);assert.equal(running.value,true)
  pending.reject(Error('offline'));await save
  assert.equal(running.value,false)
  await flush()
})

test('single execution notice cannot unlock another write while the original request is pending', async () => {
  const pending=deferred(),running=ref(false),requests=[],timers=[],cleared=[]
  const run=method('caseRun',{userStore:{selected_environment:0},Message:{success(){},error(){},info(){}},caseRunning:running,pageVersion:1,pageActive:ref(true),runNoticeTimer:null,setTimeout:fn=>{timers.push(fn);return 1},clearTimeout:id=>cleared.push(id),document:{visibilityState:'visible'},getApiCaseRun:(...args)=>{requests.push(args);return pending.promise},doRefresh(){}},path.join(base,'index.vue'))
  const current=run(row())
  timers[0]()
  assert.equal(running.value,true)
  await run(row(2))
  assert.deepEqual(requests,[[1,0,null]])
  pending.resolve({msg:'ok'});await current
  assert.equal(running.value,false)
  assert.deepEqual(cleared,[1])
})

test('actual search fields keep zero in collection queries and preserve dedicated scene arrays', () => {
  const state=panel('ApiCaseMetadataEditor','draft',{props:{userOptions:[]}})
  const {createConditionItems}=state.load('config.ts'), {getFormItems}=state.load('../../../utils/datacleaning.ts')
  const items=createConditionItems()
  items.find(i=>i.key==='status').value=[0,1]
  items.find(i=>i.key==='scenario_tags').value=['regression','data']
  const query=getFormItems(items)
  assert.equal(query.status__in,'0,1')
  assert.deepEqual(query.scenario_tags,['regression','data'])
  state.close()
})
