import test from 'node:test'
import assert from 'node:assert/strict'
import { ref, reactive, nextTick } from 'vue'
import { readFileSync, readdirSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, method, deferred, flush, step, scenario } from './helpers/case-details-harness.mjs'

test('initial current-version selection reloads the case record before loading product-dependent panels',async()=>{
  const h=harness('ApiCaseStepTable','rowActions')
  const {createCaseRequestScope}=h.load('request-scope.ts'),requests=createCaseRequestScope()
  const pending=deferred(),calls=[],record=ref(null)
  const loadRecord=method('ensureCaseRecord',{
    apiCaseId:ref(5751),requests,getApiCase:()=>pending.promise,
    setCaseRecord:r=>{record.value=r;calls.push('record')},normalizeCaseRecord:r=>r,
  })
  const showCurrent=method('showCurrentConfiguration',{
    requests,invalidateParameterLoad(){},invalidateExecutionResultLoad(){},clearPanelCache(){},
    jsonEditDrawer:{visible:false},selectedCaseVersionDetail:ref(null),caseVersionPayloadActive:ref(false),
    caseVersionEditUnlocked:ref(false),snapshotParametersByStep:new Map(),liveCaseRecord:ref(null),
    setCaseRecord(){},normalizeCaseRecord:r=>r,ensureCaseRecord:loadRecord,
    doRefresh:async()=>calls.push('steps'),loadCaseDataFactoryCount:async()=>calls.push('factory'),
    refreshSelectedRuntimeResult:async()=>calls.push('result'),
  })
  const initial=loadRecord()
  showCurrent()
  pending.resolve({data:[{id:5751,project_product:{id:3}}]})
  await initial;await flush()
  assert.equal(record.value.project_product.id,3)
  assert.deepEqual(calls,['record','steps','factory','result'])
  h.close()
})

test('product selection defaults to the case, restores existing bindings and discards old product responses',async()=>{
  const request=deferred()
  const h=harness('ApiCaseStepEditor','draft,selectedProductId,changeProduct,apiOptions,getModuleApi',{
    api:{getApiInfoName:()=>request.promise},
  })
  h.exposed.open()
  assert.equal(h.selectedProductId.value,2)
  h.getModuleApi(1)
  Object.assign(h.draft,{module:1,api_info:20,pinned_api_info_revision:30})
  h.changeProduct([7,3])
  assert.equal(h.selectedProductId.value,3)
  assert.equal(h.draft.module,null)
  assert.equal(h.draft.api_info,'')
  assert.equal(h.draft.pinned_api_info_revision,'')
  request.resolve({data:[{key:20,title:'old'}]});await flush()
  assert.equal(h.apiOptions.value.length,0)
  h.exposed.open({...step,api_info:{...step.api_info,project_product:3}})
  assert.equal(h.selectedProductId.value,3)
  assert.equal(h.draft.api_info,20)
  h.close()
})

test('step selection ignores old module responses and retains failed form without duplicate saves', async()=>{
  const pending=[],writes=[],save=deferred()
  const h=harness('ApiCaseStepEditor','draft,apiOptions,optionsLoading,getModuleApi,loadApiInfoRevisions,save,visible,saving',{
    api:{getApiInfoName:()=>{const d=deferred();pending.push(d);return d.promise},postApiCaseDetailed:p=>{writes.push(p);return save.promise}},
  })
  h.exposed.open();h.getModuleApi(1);h.getModuleApi(2)
  pending[1].resolve({data:[{key:20,title:'new',published_revision_id:30}]});await flush()
  pending[0].resolve({data:[{key:9,title:'old'}]});await flush()
  assert.equal(h.apiOptions.value[0].key,20)
  Object.assign(h.draft,{module:2,api_info:20});h.loadApiInfoRevisions(20)
  const first=h.save();assert.equal(await h.save(),false);assert.equal(writes.length,1)
  save.reject(Error('offline'));assert.equal(await first,false)
  assert.equal(h.visible.value,true);assert.equal(h.saving.value,false);assert.equal(h.draft.pinned_api_info_revision,30)
  h.exposed.close();h.exposed.open();assert.equal(h.draft.api_info,null);assert.equal(h.apiOptions.value.length,0);h.close()
})
test('module is optional; opening and clearing the filter loads product interfaces and saves without a module',async()=>{
  const calls=[],writes=[]
  const h=harness('ApiCaseStepEditor','draft,apiOptions,getModuleApi,loadApiInfoRevisions,save,formItems',{
    api:{getApiInfoOptions:async product=>{calls.push(product);return [{id:40,name:'Product API',published_revision_id:50,published_version_label:'V2'}]},
      getApiInfoName:async()=>({data:[{key:20,title:'Module API',published_revision_id:30}]}),
      postApiCaseDetailed:async p=>{writes.push(p);return {msg:'ok'}}},
  })
  h.exposed.open();await flush()
  assert.deepEqual(calls,[2]);assert.equal(h.formItems.find(item=>item.key==='module').required,false)
  assert.equal(h.apiOptions.value[0].title,'Product API（已发布 V2）')
  h.getModuleApi(8);await flush();assert.equal(h.apiOptions.value[0].key,20)
  h.draft.module=null;h.getModuleApi(null);await flush()
  assert.deepEqual(calls,[2,2]);assert.equal(h.apiOptions.value[0].key,40)
  h.draft.api_info=40;h.loadApiInfoRevisions(40)
  assert.equal(await h.save(),true);assert.equal(writes[0].api_info,40)
  assert.equal(writes[0].pinned_api_info_revision,50);h.close()
})
test('editing without a module retains the exact bound revision even when product options omit it',async()=>{
  const writes=[]
  const h=harness('ApiCaseStepEditor','draft,apiOptions,save',{
    api:{getApiInfoOptions:async()=>[{id:40,name:'Other API',published_revision_id:50}],
      putApiCaseDetailed:async p=>{writes.push(p);return {msg:'ok'}}},
  })
  h.exposed.open({...step,pinned_api_info_revision:30});await flush()
  assert.equal(h.draft.module,null);assert.equal(h.draft.api_info,20)
  assert.equal(h.draft.pinned_api_info_revision,30)
  assert.deepEqual(h.apiOptions.value.map(item=>item.key),[40,20])
  assert.equal(await h.save(),true);assert.equal(writes[0].pinned_api_info_revision,30);h.close()
})
test('switching products loads its unfiltered interfaces and ignores late product responses',async()=>{
  const requests=[]
  const h=harness('ApiCaseStepEditor','draft,apiOptions,changeProduct,optionsLoading',{
    api:{getApiInfoOptions:product=>{const request=deferred();requests.push({product,...request});return request.promise}},
  })
  h.exposed.open();h.changeProduct(3)
  assert.deepEqual(requests.map(item=>item.product),[2,3])
  assert.equal(h.draft.module,null);assert.equal(h.draft.api_info,'')
  requests[1].resolve([{id:40,name:'New product',published_revision_id:50}]);await flush()
  requests[0].resolve([{id:20,name:'Old product',published_revision_id:30}]);await flush()
  assert.deepEqual(h.apiOptions.value.map(item=>item.key),[40]);assert.equal(h.optionsLoading.value,false);h.close()
})
test('new steps persist normal or recovery timing and reopening resets the timing draft',async()=>{
  const writes=[]
  const h=harness('ApiCaseStepEditor','draft,save',{
    api:{postApiCaseDetailed:async(p,id)=>{writes.push([p,id]);return {msg:'ok'}}},
  })
  for (const isRecovery of [true,false]) {
    h.exposed.open()
    assert.equal(h.draft.is_recovery,false)
    Object.assign(h.draft,{module:2,api_info:20,pinned_api_info_revision:30,is_recovery:isRecovery})
    assert.equal(await h.save(),true)
    assert.deepEqual(writes.at(-1)[0].execution_config,{is_recovery:isRecovery})
    assert.equal(writes.at(-1)[1],1)
  }
  h.close()
})
test('step actions expose editing instead of a standalone timing operation',()=>{
  const h=harness('ApiCaseStepTable','rowActions',{props:{editLocked:false,executionActive:false,getApiInfoId:()=>20}})
  const actions=h.rowActions(step)
  assert.equal(actions.some(action=>action.label==='执行时机'),false)
  const edit=actions.find(action=>action.label==='编辑')
  edit.onClick()
  assert.deepEqual(h.events,[['edit',step]])
  h.props.executionActive=true
  assert.equal(h.rowActions(step).find(action=>action.label==='编辑').disabled,true)
  h.close()
})
test('scenario create/edit/copy owns isolated drafts, normalizes protocol expectations and retries failed saves',async()=>{
  const pending=[],writes=[]
  const save=(type,p)=>{writes.push([type,p]);const d=deferred();pending.push(d);return d.promise}
  const h=harness('ApiCaseScenarioEditor','draft,save,visible,saving',{
    api:{postApiCaseDetailedParameter:p=>save('create',p),putApiCaseDetailedParameter:p=>save('edit',p),postApiCaseDetailedParameterCopy:p=>save('copy',p)},
  })
  const original=scenario({body_config:{protocol_expectation:{mode:'codes',status_codes:[400,422]}}})
  h.exposed.open(step,'edit',original);h.draft.name='renamed'
  assert.equal(original.name,'Example scenario');assert.equal('protocol_expectation_codes' in h.draft,false)
  const first=h.save();await h.save();assert.equal(writes.length,1)
  pending[0].reject(Error('failure'));assert.equal(await first,false);assert.equal(h.visible.value,true)
  const retry=h.save();pending[1].resolve({msg:'ok'});assert.equal(await retry,true);assert.equal(h.visible.value,false)
  assert.equal(writes[1][1].id,11);assert.equal('protocol_expectation' in writes[1][1],false)
  h.exposed.open(step,'copy',original);const copy=h.save();pending[2].resolve({msg:'ok'});await copy;assert.equal(writes[2][0],'copy')
  h.exposed.open({...step,api_info:{...step.api_info,protocol_type:'grpc'}});h.draft.name='gRPC'
  const create=h.save();pending[3].resolve({msg:'ok'});await create
  assert.equal(writes[3][1].case_detailed,10);assert.equal('id' in writes[3][1],false)
  assert.equal('protocol_expectation' in writes[3][1],false);assert.equal(h.events.length,3);h.close()
})
test('scenario save completing after a case switch cannot close or refresh the new case',async()=>{
  const d=deferred()
  const h=harness('ApiCaseScenarioEditor','draft,save,visible', {api:{postApiCaseDetailedParameter:()=>d.promise}})
  h.exposed.open(step);h.draft.name='new';const save=h.save()
  h.props.caseId=2;await flush();d.resolve({msg:'ok'});assert.equal(await save,false);assert.deepEqual(h.events,[]);h.close()
})
test('draft edits do not mutate props; persisted patches freeze data and ignore late completions after source changes',async()=>{
  const h=harness('ApiCaseScenarioEditor','draft')
  const {useApiCaseScenarioDraft}=h.load('composables/useApiCaseScenarioDraft.ts')
  const source=ref(scenario({params:'old'})),patches=[],writes=[],pending=[]
  const draft=useApiCaseScenarioDraft(()=>source.value,p=>patches.push(p),p=>{writes.push(p);const d=deferred();pending.push(d);return d.promise})
  draft.draft.value.params='new';assert.equal(source.value.params,'old')
  const first=draft.save({id:11,params:'new'});pending[0].reject(Error('failed'));await assert.rejects(first)
  assert.deepEqual(patches,[])
  const second=draft.save({id:11,params:'new'});source.value=scenario({id:12,params:'other'})
  pending[1].resolve({msg:'ok'});await second;assert.deepEqual(patches,[]);assert.equal(draft.draft.value.params,'other')
  const third=draft.save({id:12,params:'saved'});pending[2].resolve({msg:'ok'});await third
  assert.deepEqual(patches,[{id:12,changes:{params:'saved'}}])
  const fourth=draft.save({id:12,params:'closed'});h.close()
  pending[3].resolve({msg:'ok'});await fourth
  assert.equal(patches.length,1)
})
test('trace queries are latest-only, close invalidates requests, cyclic node parents do not hang',async()=>{
  const pending=[]
  const h=harness('ApiCaseExecutionTraceDrawer','state,visibleNodes', {api:{getSystemTestSuiteDetailsExecutionTrace:()=>{const d=deferred();pending.push(d);return d.promise}}})
  const first=h.exposed.open({case_id:1}),second=h.exposed.open({case_id:2})
  pending[1].resolve({data:{trace:{trace_id:'new'},nodes:[{id:1,parent_step_id:2},{id:2,parent_step_id:1}]}});await second
  pending[0].resolve({data:{trace:{trace_id:'old'},nodes:[]}});await first
  assert.equal(h.state.trace.trace_id,'new');assert.deepEqual(h.visibleNodes.value,[])
  const third=h.exposed.open({case_id:3});h.exposed.close();pending[2].resolve({data:{trace:{trace_id:'closed'}}});await third
  assert.equal(h.state.trace,null);assert.equal(h.state.loading,false);h.close()
})
test('AI focus/record/close invalidates previous analyses and releases both loading flags',async()=>{
  const pending=[],previews=[]
  const h=harness('ApiCaseDiagnosisDrawer','preview,analysis,analyze,selectUnit,analysisLoading,previewLoading',{
    api:{getApiCaseDiagnosisPreview:()=>{const d=deferred();previews.push(d);return d.promise},postApiCaseDiagnosis:()=>{const d=deferred();pending.push(d);return d.promise}},
  })
  h.exposed.open();previews[0].resolve({data:{can_analyze:true,evidence_level:'result',units:[{status:0,unit_index:0}]}});await flush()
  const first=h.analyze();h.selectUnit(1);pending[0].resolve({data:{available:true,analysis:{cause:'old'}}});await first
  assert.equal(h.analysis.value,null);assert.equal(h.analysisLoading.value,false)
  const second=h.analyze();h.exposed.close();pending[1].reject(Error('closed'));await second
  assert.equal(h.analysis.value,null);assert.equal(h.analysisLoading.value,false)
  h.exposed.open();h.props.resultId=null;await flush();assert.equal(h.previewLoading.value,false)
  previews[1].resolve({data:{units:[]}});await flush();assert.equal(h.preview.value,null);h.close()
})
test('recovery preserves existing execution keys and sends the captured case while rejecting concurrent opens',async()=>{
  const d=deferred(),writes=[]
  const h=harness('ApiCaseStepEditor','draft,editingId,save,visible', {api:{putApiCaseDetailed:(p,id)=>{writes.push([p,id]);return d.promise}}})
  h.exposed.open({...step,api_info:{...step.api_info,module:2},pinned_api_info_revision:30,execution_config:{is_recovery:false,existing:'keep'}});h.draft.is_recovery=true
  const saving=h.save();h.exposed.open({...step,id:88,case:2});assert.equal(h.editingId.value,10)
  d.resolve({msg:'ok'});await saving
  assert.equal(writes[0][1],1);assert.equal(writes[0][0].execution_config.existing,'keep')
  assert.equal(writes[0][0].execution_config.is_recovery,true);assert.equal(h.visible.value,false)
  h.exposed.open();assert.equal(h.editingId.value,null);assert.equal(h.draft.api_info,null);assert.equal(h.draft.is_recovery,false)
  h.close()
})
test('editing restores module and interface selectors and saves a changed published binding',async()=>{
  const writes=[]
  const h=harness('ApiCaseStepEditor','draft,apiOptions,getModuleApi,loadApiInfoRevisions,save',{
    api:{getApiInfoName:async moduleId=>({data:moduleId===2?[{key:20,title:'Existing',published_revision_id:31}]:[{key:40,title:'Changed',published_revision_id:50}]}),
      putApiCaseDetailed:async(p,id)=>{writes.push([p,id]);return {msg:'ok'}}},
  })
  h.exposed.open({...step,api_info:{...step.api_info,module:2},pinned_api_info_revision:30})
  await flush()
  assert.equal(h.draft.module,2);assert.equal(h.draft.api_info,20)
  assert.equal(h.draft.pinned_api_info_revision,30)
  h.draft.module=3;h.getModuleApi(3);await flush()
  assert.equal(await h.save(),false)
  h.draft.api_info=40;h.loadApiInfoRevisions(40)
  h.draft.is_recovery=true
  assert.equal(await h.save(),true)
  assert.equal(writes[0][0].api_info,40)
  assert.equal(writes[0][0].pinned_api_info_revision,50)
  assert.deepEqual(writes[0][0].execution_config,{is_recovery:true})
  assert.equal('case_sort' in writes[0][0],false)
  h.close()
})
test('page request generation invalidates all channels, latest request remains valid within its channel',()=>{
  const h=harness('ApiCaseScenarioEditor','draft'),{createCaseRequestScope}=h.load('request-scope.ts')
  const scope=createCaseRequestScope(),first=scope.begin('steps'),second=scope.begin('steps'),option=scope.begin('options')
  assert.equal(first(),false);assert.equal(second(),true);assert.equal(option(),true)
  scope.invalidate();assert.equal(second(),false);assert.equal(option(),false);h.close()
})
test('step refresh ignores old responses and selects a surviving step after the selected step is deleted',async()=>{
  const h=harness('ApiCaseScenarioEditor','draft'),{createCaseRequestScope}=h.load('request-scope.ts'),requests=createCaseRequestScope()
  const pending=[],selected=[]
  const dep={apiCaseId:ref(1),pageActive:true,caseVersionPayloadActive:ref(false),requests,stepTableLoading:ref(false),optionLists:{},caseRecord:ref({front_headers:[]}),
    getApiCaseDetailed:()=>{const d=deferred();pending.push(d);return d.promise},normalizeCaseDetailRow:r=>r,caseSteps:ref([]),selectedStep:ref({id:99}),scenarios:ref([]),
    select:async r=>{selected.push(r.id)},invalidateParameterLoad(){},syncCaseRunRefreshByRows(){}}
  const refresh=method('doRefresh',dep),first=refresh(),second=refresh()
  pending[1].resolve({data:[step]});await second;pending[0].resolve({data:[{...step,id:88}]});await first
  assert.deepEqual(selected,[10]);assert.equal(dep.caseSteps.value[0].id,10);assert.equal(dep.stepTableLoading.value,false);h.close()
})
test('JSON save failure preserves source and open draft; success commits only the captured scenario',async()=>{
  const pending=[],source={id:11,params:'old'},patches=[]
  const dep={jsonEditDrawer:{value:'new',field:'params',item:source,visible:true},ensureCaseEditable:()=>true,jsonEditSaving:ref(false),requests:{capture:()=>()=>true},
    saveParameter:()=>{const d=deferred();pending.push(d);return d.promise},applyScenarioPatch:p=>patches.push(p),formatJsonObj:()=>{throw Error('not JSON')}}
  const save=method('saveJsonEditDrawer',dep),first=save();pending[0].reject(Error('offline'));await first
  assert.equal(source.params,'old');assert.equal(dep.jsonEditDrawer.visible,true)
  const second=save();pending[1].resolve(null);await second
  assert.deepEqual(patches,[{id:11,changes:{params:'new'}}]);assert.equal(dep.jsonEditDrawer.visible,false)
})
test('all details components compile and the page no longer owns an untyped data bucket or mutates store state',()=>{
  const base='src/views/apitest/case/details/'
  for(const f of ['index.vue',...readdirSync(base+'components').filter(f=>f.endsWith('.vue')).map(f=>'components/'+f)]){
    const filename=base+f,source=readFileSync(filename,'utf8'),{descriptor,errors}=parse(source)
    assert.deepEqual(errors,[])
    const script=compileScript(descriptor,{id:f})
    assert.deepEqual(compileTemplate({source:descriptor.template.content,filename,id:f,compilerOptions:{bindingMetadata:script.bindings}}).errors,[],f)
  }
  const page=readFileSync(base+'index.vue','utf8');assert.doesNotMatch(page,/const data: any|pageData\.setRecord|pageData\.record/)
  for(const f of ['ApiCaseRequestPanel','ApiCaseScenarioFrontPanel','ApiCasePosteriorPanel','ApiCaseAssertionPanel']){
    const source=readFileSync(base+'components/'+f+'.vue','utf8');assert.doesNotMatch(source,/props\.item\.[\w]+\s*=|v-model="item\./)
  }
})

test('failed step reordering restores previous order and blocks duplicate submissions',async()=>{
  const pending=deferred(),rows=ref([step,{...step,id:12}]),loading=ref(false);let writes=0
  const reorder=method('handleChange',{ensureCaseEditable:()=>true,caseExecutionActive:ref(false),sortingSteps:loading,
    requests:{capture:()=>()=>true},caseSteps:rows,putApiPutCaseSort:()=>{writes++;return pending.promise},Message:{success(){}}})
  const first=reorder([...rows.value].reverse());await reorder([])
  assert.equal(writes,1);assert.equal(rows.value[0].id,12);assert.equal(loading.value,true)
  pending.reject(Error('offline'));await first
  assert.deepEqual(rows.value.map(r=>r.id),[10,12]);assert.equal(loading.value,false)
})

test('closing callback evidence ignores late delivery results and releases its local loading',async()=>{
  const pending=deferred()
  const h=harness('ApiCaseCallbackPanel','openDeliveries,deliveries,evidenceVisible,evidenceLoading,closePanels',{
    props:{productId:2,rules:[],triggerStep:step,scenarioCount:1,savePending:false,active:true,persistRules:async()=>true},
    api:{getCallbackDeliveries:()=>pending.promise},
  })
  const first=h.openDeliveries({id:1});h.closePanels()
  pending.resolve({data:{items:[{id:8}],count:1}});await first
  assert.deepEqual(h.deliveries.value,[]);assert.equal(h.evidenceVisible.value,false);assert.equal(h.evidenceLoading.value,false);h.close()
})

test('revision list and detail requests cannot publish previous case data after a case switch',async()=>{
  const lists=[],details=[]
  const h=harness('ApiCaseVersionPanel','refresh,revisions,selectRevision,selectingVersion',{
    api:{getApiCaseRevisionList:()=>{const d=deferred();lists.push(d);return d.promise},getApiCaseRevisionDetail:()=>{const d=deferred();details.push(d);return d.promise}},
  })
  const first=h.refresh();h.props.caseId=2;await flush()
  lists[1].resolve({data:[{id:20,revision_no:1}]});await flush();lists[0].resolve({data:[{id:10}]});await first
  assert.equal(h.revisions.value[0].id,20)
  const detail=h.selectRevision({id:20,revision_no:1});h.props.caseId=3;await flush()
  details[0].resolve({data:{id:20,payload:{}}});await detail
  assert.equal(h.events.some(event=>event[0]==='detail'),false);assert.equal(h.selectingVersion.value,false)
  lists[2].resolve({data:[]});await flush();h.close()
})

test('saving one field preserves another unsaved draft field, and runtime responses remain current',async()=>{
  const h=harness('ApiCaseScenarioEditor','draft'),{useApiCaseScenarioDraft}=h.load('composables/useApiCaseScenarioDraft.ts')
  const source=ref(scenario({params:'old',headers:[]})),pending=[]
  const editor=useApiCaseScenarioDraft(()=>source.value,patch=>{source.value={...source.value,...patch.changes}},()=>{const d=deferred();pending.push(d);return d.promise})
  editor.draft.value.params='unsaved';editor.draft.value.headers=[1]
  const first=editor.save({id:11,headers:[1]});pending[0].resolve({msg:'ok'});await first
  assert.equal(editor.draft.value.params,'unsaved');assert.equal(source.value.params,'old')
  const second=editor.save({id:11,params:'unsaved'});pending[1].resolve({msg:'ok'});await second
  assert.equal(source.value.params,'unsaved')
  source.value.result_data={response:{code:200,json:{latest:true}}};await flush()
  assert.equal(editor.draft.value.result_data.response.json.latest,true);h.close()
})
