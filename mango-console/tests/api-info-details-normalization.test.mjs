import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base=path.resolve('src/views/apitest/info/details')
function actualLossless(){
 const exports={}
 new Function('exports','require',ts.transpileModule(readFileSync('src/utils/lossless-json.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText)(exports,createRequire(import.meta.url))
 return exports
}
const lossless=actualLossless()
const record=(id=1)=>({id,name:'Example API',method:0,url:'/example',project_product:{id:2},protocol_type:'http',headers:{},params:null,body_type:'json',body_config:{body:{value:'original'}},sse_config:null,posterior_json_path:[],posterior_re:[],posterior_func:''})
function page(api={},extras={}){
 return harness('index','apiRecord,currentApiInfoPayload,headersText,recordReady,configurationLoading,initialize,handleApiVersionSelect,persistApiInfo,waitForSaves,upDate,saveRequestMeta,savePosteriorFuncIfChanged,recordPosteriorFuncSnapshot,loadDefaultHeadersPreview,defaultHeadersText,isDefaultHeadersPreview,loadLatestExecutionResult,executionResult,resultLoading,onRunCase,caseRunning,runtimeParametersRef,deactivate,saveRequestBody,bodyEditorRef,removeExtraction',{
  base,props:{apiInfoId:1},api:{getApiInfo:async()=>({data:[record()]}),...api},
  modules:{'vue-router':{useRoute:()=>({query:{id:'99'}})},'@/store/modules/user':{default:()=>({selected_environment:0})},'@/utils/lossless-json':lossless,...extras.modules},
 })
}
function versions(api={},extras={}){
 return harness('ApiInfoVersionPanel','refresh,selectRevision,selectedKey,revisions,loading,selecting,createRevision,publishSelected,checkoutSelectedRevision,deleteSelectedRevision,publishedRevisionPayload,loadPublishedRevisionPayload,openCompareDrawer,compareDrawerVisible,resultHistoryVisible',{
  base,props:{apiInfoId:1,currentPayload:record(),...extras.props},api,
  Modal:extras.Modal,modules:{'@/utils/lossless-json':lossless},
 })
}
const revision=id=>({id,api_info:1,revision_no:id,release:null})

test('workbench, private panels, body editor and runtime parameters compile',()=>{
 for(const file of ['index.vue','components/ApiInfoVersionPanel.vue','components/ApiInfoResponsePanel.vue','../../components/ApiRequestBodyEditor.vue','../../../../components/business/ApiInfoRuntimeParametersModal.vue','../../../../components/business/VariableReferencePanel.vue','../../../../components/business/ApiVersionCompareDrawer.vue','../../../../components/business/ExecutionResultHistoryDrawer.vue']){
  const filename=path.resolve(base,file),{descriptor,errors}=parse(readFileSync(filename,'utf8'))
  assert.deepEqual(errors,[],file)
  const script=compileScript(descriptor,{id:file})
  assert.deepEqual(compileTemplate({source:descriptor.template.content,filename,id:file,compilerOptions:{bindingMetadata:script.bindings}}).errors,[],file)
 }
})

test('entry loads by explicit ID without reading or mutating page-data',async()=>{
 const requests=[],state=page({getApiInfo:async query=>{requests.push(query);return {data:[record(1)]}}})
 await flush()
 assert.deepEqual(requests,[{id:1}]);assert.equal(state.apiRecord.value.id,1)
 assert.equal(state.recordReady.value,true);assert.equal(state.configurationLoading.value,false)
 assert.doesNotMatch(readFileSync(path.join(base,'index.vue'),'utf8'),/usePageData|pageData\.record/)
 state.close()
})

test('saving one field preserves unrelated unsaved input and lossless body numbers',async()=>{
 const pending=deferred(),writes=[],state=page({putApiInfo:payload=>{writes.push(payload);return pending.promise}})
 await flush()
 const exact=new lossless.LosslessJsonNumber('9007199254740993')
 state.apiRecord.value.body_config={body:{id:exact}}
 state.apiRecord.value.params='unsaved=1'
 const saving=state.persistApiInfo({url:'/saved'})
 await flush();state.apiRecord.value.params='new unsaved=2'
 pending.resolve({data:{...record(),url:'/saved'},msg:'ok'});await saving
 assert.equal(state.apiRecord.value.params,'new unsaved=2')
 assert.equal(state.currentApiInfoPayload.value.params,null)
 assert.equal(state.apiRecord.value.body_config.body.id.value,'9007199254740993')
 assert.deepEqual(writes,[{id:1,url:'/saved'}]);state.close()
})

test('queued saves freeze original targets and skip jobs invalidated by version selection',async()=>{
 const pending=deferred(),writes=[],state=page({putApiInfo:payload=>{writes.push(payload);return pending.promise}})
 await flush()
 const first=state.persistApiInfo({params:'first'});await flush()
 const value=[{key:'id',value:'$.id'}],second=state.persistApiInfo({posterior_json_path:value})
 value[0].value='changed'
 state.handleApiVersionSelect({kind:'revision',id:20,label:'r20',payload:{...record(),url:'/snapshot'}})
 pending.resolve({data:{...record(),params:'first'}})
 assert.equal(await first,null);assert.equal(await second,null)
 assert.equal(writes.length,1);assert.equal(state.apiRecord.value.url,'/snapshot')
 state.close()
})

test('failed save retains input and the same Python function can be retried',async()=>{
 let fail=true;const writes=[],state=page({putApiInfo:async payload=>{writes.push(payload);if(fail)throw Error('offline');return {data:payload,msg:'ok'}}})
 await flush();state.recordPosteriorFuncSnapshot();state.apiRecord.value.posterior_func='return response'
 await state.savePosteriorFuncIfChanged()
 assert.equal(state.apiRecord.value.posterior_func,'return response')
 fail=false;await state.savePosteriorFuncIfChanged()
 assert.equal(writes.length,2)
 await state.savePosteriorFuncIfChanged();assert.equal(writes.length,2)
 state.close()
})

test('default header previews cannot erase input typed while the read is pending',async()=>{
 const pending=deferred(),state=page({getApiHeaders:()=>pending.promise})
 await flush();state.headersText.value=null
 const reading=state.loadDefaultHeadersPreview({...record(),headers:null})
 state.headersText.value='{"X-Example":"local"}'
 pending.resolve({data:[{key:'X-Example',value:'default'}]});await reading
 assert.equal(state.headersText.value,'{"X-Example":"local"}')
 assert.equal(state.isDefaultHeadersPreview.value,false)
 state.close()
})

test('execution freezes environment/version and rejects results after switching revisions',async()=>{
 const pending=deferred(),writes=[],state=page({getApiCaseInfoRun:(...args)=>{writes.push(args);return pending.promise}})
 await flush();state.runtimeParametersRef.value={prepare:async()=>({input:'value'}),cancel(){}}
 const running=state.onRunCase();await flush()
 assert.equal(state.caseRunning.value,true);await state.onRunCase()
 assert.deepEqual(writes,[[1,0,{}, {input:'value'}]])
 state.handleApiVersionSelect({kind:'revision',id:7,label:'r7',payload:record()})
 pending.resolve({data:{id:100},msg:'ok'});await running
 assert.equal(state.executionResult.value,null);assert.equal(state.caseRunning.value,false)
 state.close()
})

test('cancelled runtime parameter discovery cannot start an execution',async()=>{
 const parameters=deferred(),writes=[],state=page({getApiCaseInfoRun:(...args)=>{writes.push(args);return {data:{}}}})
 await flush();state.runtimeParametersRef.value={prepare:()=>parameters.promise,cancel(){parameters.resolve(null)}}
 const running=state.onRunCase();await flush();state.deactivate();await running
 assert.deepEqual(writes,[]);assert.equal(state.caseRunning.value,false)
 state.close()
})

test('failed extraction deletion preserves its original rows',async()=>{
 const state=page({putApiInfo:async()=>{throw Error('offline')}});await flush()
 state.apiRecord.value.posterior_json_path=[{key:'id',value:'$.id'}]
 await state.removeExtraction(0,'posterior_json_path')
 assert.deepEqual(state.apiRecord.value.posterior_json_path,[{key:'id',value:'$.id'}])
 state.close()
})

test('body editor failure resets only the current session deduplication marker',async()=>{
 const pending=deferred(),state=page({putApiInfo:()=>pending.promise});await flush()
 let resets=0;state.bodyEditorRef.value={resetSaveState(){resets++}}
 const save=state.saveRequestBody({body_type:'raw',body_config:{body_text:'example'}});await flush()
 pending.reject(Error('offline'));await save;assert.equal(resets,1)
 state.close()
})

test('response panel preserves a null JSON body and zero status/time',()=>{
 const state=harness('ApiInfoResponsePanel','responseBodyData,responseStatusText,responseTimeText',{base,props:{result:{json:null,text:'fallback',code:0,time:0},loading:false}})
 assert.equal(state.responseBodyData.value,null)
 assert.equal(state.responseStatusText.value,'调用完成');assert.equal(state.responseTimeText.value,'0.00 秒')
 state.close()
})

test('late version lists and selection responses cannot affect a new API',async()=>{
 const reads=[],state=versions({getApiInfoRevisionList:()=>{const pending=deferred();reads.push(pending);return pending.promise}})
 state.props.apiInfoId=2;await flush()
 reads[1].resolve({data:[revision(22)]});await flush()
 reads[0].resolve({data:[revision(11)]});await flush()
 assert.equal(state.revisions.value[0].id,22);assert.equal(state.loading.value,false)
 state.close()
})

test('failed revision selection restores the previous version and releases loading',async()=>{
 const state=versions({getApiInfoRevisionDetail:async()=>{throw Error('offline')}});await flush()
 await state.selectRevision(revision(8))
 assert.equal(state.selectedKey.value,'current');assert.equal(state.selecting.value,false)
 state.close()
})

test('publication confirmation fixes original API and revision IDs and retains failures for retry',async()=>{
 const prompts=[],writes=[];let fail=true
 const state=versions({getApiInfoRevisionList:async()=>({data:[revision(10),revision(11)]}),getApiInfoRevisionDetail:async()=>({data:{payload:{api_info:record()}}}),publishApiInfoRevision:async(...args)=>{writes.push(args);if(fail)throw Error('offline');return {msg:'ok'}}},{Modal:{confirm:config=>{prompts.push(config);return {close(){}}}}})
 await flush();await state.selectRevision(revision(10));state.publishSelected()
 state.selectedKey.value='revision-11'
 assert.equal(await prompts[0].onBeforeOk(),false)
 assert.deepEqual(writes,[[1,10]])
 fail=false;assert.equal(await prompts[0].onBeforeOk(),true)
 state.close()
})

test('old confirmation cannot publish into a newly selected API',async()=>{
 const prompts=[],writes=[],state=versions({getApiInfoRevisionList:async()=>({data:[revision(10)]}),getApiInfoRevisionDetail:async()=>({data:{payload:{api_info:record()}}}),publishApiInfoRevision:async(...args)=>writes.push(args)},{Modal:{confirm:config=>{prompts.push(config);return {close(){}}}}})
 await flush();await state.selectRevision(revision(10));state.publishSelected()
 state.props.apiInfoId=2;await flush()
 assert.equal(await prompts[0].onBeforeOk(),false);assert.deepEqual(writes,[])
 state.close()
})

test('checkout notifies the page to reload the new editing payload',async()=>{
 const prompts=[],state=versions({getApiInfoRevisionList:async()=>({data:[revision(10)]}),getApiInfoRevisionDetail:async()=>({data:{payload:{api_info:record()}}})},{Modal:{confirm:config=>{prompts.push(config);return {close(){}}}}})
 await flush();await state.selectRevision(revision(10));state.checkoutSelectedRevision()
 assert.equal(await prompts[0].onBeforeOk(),true)
 assert.ok(state.events.some(([event])=>event==='checkout'))
 state.close()
})

test('runtime parameters cancel invalidates discovery and settles an already open prompt',async()=>{
 const pending=deferred(),state=harness('business/ApiInfoRuntimeParametersModal','prepare,cancel,rows,modal',{base:path.resolve('src'),api:{getApiInfoExecutionParameters:()=>pending.promise}})
 state.modal.value={show(){},close(){}}
 const reading=state.prepare([{id:1}]);state.cancel()
 pending.resolve({data:{variables:['input']}})
 assert.equal(await reading,null);assert.deepEqual(state.rows.value,[])
 const open=state.prepare([{id:1}]);await flush();state.cancel()
 assert.equal(await open,null)
 state.close()
})

test('blank headers inherit defaults while an explicit empty object suppresses defaults',async()=>{
 const writes=[],state=page({putApiInfo:async payload=>{writes.push(payload);return {data:payload,msg:'ok'}}});await flush()
 assert.equal(await state.upDate('headers',''),true)
 assert.equal(await state.upDate('headers','{}'),true)
 assert.equal(writes[0].headers,null);assert.deepEqual(writes[1].headers,{})
 state.close()
})

test('shared body drafts isolate nested form arrays and retry identical data after a rejected save',async()=>{
 const source={fields:[{key:'input',value:'original'}]}
 const state=harness('ApiRequestBodyEditor','local,save,lastEmittedPayload,resetSaveState',{
  base:path.resolve('src/views/apitest'),props:{protocolType:'http',bodyType:'form',bodyConfig:source,readonly:false,saving:false},
  modules:{'@/utils/lossless-json':lossless,'@/store/modules/get-project':{useProject:()=>({projectProduct:[],projectProductName:async()=>{}})}},
 })
 await flush();state.local.body_config.fields[0].value='local';state.save()
 assert.equal(source.fields[0].value,'original')
 assert.equal(state.events.length,1)
 state.save();assert.equal(state.events.length,1)
 state.resetSaveState();state.save();assert.equal(state.events.length,2)
 state.local.body_config.fields[0].value='another edit'
 assert.equal(state.events[0][1].body_config.fields[0].value,'local')
 state.close()
})

test('revision creation waits for pending saves and stops when its original context closes',async()=>{
 const pending=deferred(),writes=[],state=versions({createApiInfoRevision:async(...args)=>{writes.push(args);return {data:revision(1)}}},{props:{beforeAction:()=>pending.promise}})
 await flush();const creating=state.createRevision();await flush()
 assert.deepEqual(writes,[])
 state.exposed.close();pending.resolve();await creating
 assert.deepEqual(writes,[])
 state.close()
})
