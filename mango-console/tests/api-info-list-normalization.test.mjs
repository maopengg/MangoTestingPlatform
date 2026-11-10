import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync, readdirSync } from 'node:fs'
import ts from 'typescript'
import { computed, reactive, ref } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base=path.resolve('src/views/apitest/info')
const tableConfig={useTableIndexColumn:()=>({key:'index'}),useTableColumn:items=>items}
const enums={method:[{key:0,title:'GET'},{key:1,title:'POST'},{key:7,title:'MCP_CALL'},{key:8,title:'GRPC_CALL'},{key:9,title:'WEBSOCKET_CONNECT'}]}
const row=(id=1)=>({id,name:'Example API',url:'/example',protocol_type:'http',method:0,body_type:'json',status:1,project_product:{id:2,name:'Example'},module:{id:3},published_release_id:10,published_revision_id:11})
function component(name,bindings,api={},options={}) {
 return harness(name,bindings,{base,api,...options,modules:{'@/hooks/table':tableConfig,'@/store/modules/get-enum':{useEnum:()=>enums},...options.modules}})
}
function editor(api={}){return component('ApiInfoEditor','draft,open,openEdit,close,loadRecord,save,visible,saving,detailLoading,loadFailed,loadingId,editingId,syncProtocol',api)}
function loadPure(file){const exports={};new Function('exports',ts.transpileModule(readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText)(exports);return exports}
function page(api={}){
 const selection=ref([]),prompts=[],user={selected_environment:0},navigation=[]
 const table={dataList:reactive([]),tableLoading:ref(false),handleSuccess:response=>{table.dataList.splice(0,table.dataList.length,...response.data);table.tableLoading.value=false}}
 const pagination=reactive({page:1,pageSize:20,pageCount:0,setTotalSize(total){this.pageCount=total}})
 let refresh,pause,running=false
 const state=component('index','conditionItems,doRefresh,onResetSearch,onSearchRefresh,onSidebarFilterChange,switchProtocol,activeProtocol,onDelete,onConcurrency,onRunCase,runtimeParametersRef,deactivate,editorRef,grpcImportRef,batchImportRef,boundCasesRef,navigationCreateRef,onAdd,onUpdate,onStep,onBatchUpload,recordingLoading,deletingIds,userOptions,userOptionsLoading,getNickName',api,{
  Modal:{confirm:config=>{const modal={config,closed:false,close(){modal.closed=true;config.onClose?.()}};prompts.push(modal);return modal}},
  modules:{
   '@/hooks/table':{...tableConfig,useTable:()=>table,useRowKey:()=> 'id',usePagination:()=>pagination,useRowSelection:()=>({selectedRowKeys:selection,showCheckedAll:ref(true),onSelectionChange:()=>{}})},
   '@/hooks/use-latest-request':loadPure('src/hooks/use-latest-request.ts'),
   '@/hooks/use-page-polling':{isPendingExecution:loadPure('src/utils/page-polling.ts').isPendingExecution,usePagePolling:(fn,onPause)=>{refresh=fn;pause=onPause;return {start(){running=true},stop(){running=false},isRunning:()=>running}}},
   'vue-router':{useRouter:()=>({push:target=>navigation.push(target)})},
   '@/store/modules/user':{default:()=>user},
  },
 })
 return {...state,table,pagination,selection,prompts,user,navigation,poll:()=>refresh(),pause:()=>pause(),isPolling:()=>running}
}

test('list, five owned components and embedded case page compile',()=>{
 const files=[path.join(base,'index.vue'),...readdirSync(path.join(base,'components')).filter(file=>file.endsWith('.vue')).map(file=>path.join(base,'components',file)),path.resolve('src/views/apitest/case/details/index.vue')]
 for(const filename of files){const {descriptor,errors}=parse(readFileSync(filename,'utf8'));assert.deepEqual(errors,[]);const script=compileScript(descriptor,{id:filename});assert.deepEqual(compileTemplate({source:descriptor.template.content,filename,id:filename,compilerOptions:{bindingMetadata:script.bindings}}).errors,[])}
})

test('search factories isolate zero-valued multiple filters and editor defaults',()=>{
 const state=editor(),{createConditionItems}=state.load('config.ts'),first=createConditionItems(),second=createConditionItems()
 for(const key of ['method','protocol_type','status','update_user']){const item=first.find(field=>field.key===key);assert.equal(item.multiple,true);item.value=[0,1];assert.deepEqual(second.find(field=>field.key===key).value,[])}
 state.open('create',{projectProduct:2,module:3},'websocket');assert.equal(state.draft.method,9);assert.equal(state.draft.body_type,'json')
 state.exposed.close();state.open('create',{projectProduct:2,module:3},'sse');assert.equal(state.draft.protocol_type,'sse');assert.equal(state.draft.method,null)
 state.close()
})

test('edit reads the full record with independent loading and ignores late detail after switching to create',async()=>{
 const pending=deferred(),state=editor({getApiInfo:()=>pending.promise})
 const reading=state.openEdit(1);assert.equal(state.loadingId.value,'1');assert.equal(await state.save(),false)
 state.open('create',{projectProduct:8,module:9},'http')
 pending.resolve({data:[row()]});await reading
 assert.equal(state.editingId.value,null);assert.equal(state.draft.project_product,8);assert.equal(state.draft.name,'')
 assert.equal(state.detailLoading.value,false)
 state.close()
})

test('failed detail query keeps a retryable editor and cannot submit blank fields',async()=>{
 let fail=true;const state=editor({getApiInfo:async()=>{if(fail)throw Error('offline');return {data:[{...row(),project_product:2,module:3}]}}})
 await state.openEdit(1);assert.equal(state.loadFailed.value,true);assert.equal(await state.save(),false)
 fail=false;await state.loadRecord();assert.equal(state.loadFailed.value,false);assert.equal(state.draft.method,0)
 assert.equal(state.draft.project_product,2);assert.equal(state.draft.module,3)
 state.close()
})

test('metadata editing freezes its payload and leaves configuration fields out of the write',async()=>{
 const pending=deferred(),writes=[],record={...row(),body_config:{body:{example:'keep'}},posterior_json_path:[{key:'keep',value:'$.id'}]}
 const state=editor({getApiInfo:async()=>({data:[record]}),putApiInfo:payload=>{writes.push(payload);return pending.promise}})
 await state.openEdit(1);state.draft.name='Edited'
 const saving=state.save();assert.equal(await state.save(),false);state.draft.name='Retry'
 assert.equal(writes[0].name,'Edited');assert.equal(writes[0].method,0)
 for(const key of ['body_config','posterior_json_path','front_json_path','front_re'])assert.equal(key in writes[0],false)
 pending.reject(Error('offline'));assert.equal(await saving,false);assert.equal(state.visible.value,true);assert.equal(state.draft.name,'Retry');assert.equal(state.saving.value,false)
 state.close()
})

test('MCP metadata preserves existing binding transport, flags and extension fields',async()=>{
 const writes=[],record={...row(),protocol_type:'mcp',method:7,mcp_binding:{tool_name:'old',transport_type:2,tool_enabled:false,server_id:8,custom:{keep:true}}}
 const state=editor({getApiInfo:async()=>({data:[record]}),putApiInfo:async payload=>{writes.push(payload);return {msg:'ok'}}})
 await state.openEdit(1);state.draft.tool_name=' new '
 assert.equal(await state.save(),true)
 assert.deepEqual(writes[0].mcp_binding,{tool_name:'new',transport_type:2,tool_enabled:false,server_id:8,custom:{keep:true},tool_type:'tool'})
 assert.equal(record.mcp_binding.tool_name,'old')
 state.close()
})

test('cURL import normalizes product and emits only import fields',async()=>{
 const writes=[],state=editor({postApiImportUrl:async payload=>{writes.push(payload);return {msg:'ok'}}})
 state.open('import');Object.assign(state.draft,{project_product:[1,2],module:3,name:'Imported',curl_command:'curl https://example.com/api'})
 assert.equal(await state.save(),true)
 assert.deepEqual(writes,[{project_product:2,module:3,name:'Imported',curl_command:'curl https://example.com/api'}])
 state.close()
})

test('gRPC service changes ignore old method responses and clearing releases loading',async()=>{
 const requests=[],state=component('ApiInfoGrpcImport','open,draft,methods,methodsLoading,onServiceChange',{
  getGrpcMethods:()=>{const pending=deferred();requests.push(pending);return pending.promise},
 })
 await state.open();const old=state.onServiceChange(1),current=state.onServiceChange(2)
 requests[1].resolve({data:[{id:22}]});await current;requests[0].resolve({data:[{id:11}]});await old
 assert.equal(state.methods.value[0].id,22)
 const stale=state.onServiceChange(3);await state.onServiceChange(null);requests[2].resolve({data:[{id:33}]});await stale
 assert.deepEqual(state.methods.value,[]);assert.equal(state.methodsLoading.value,false)
 state.close()
})

test('gRPC rejects streaming/imported methods and retains failed import fields',async()=>{
 const writes=[],pending=deferred(),state=component('ApiInfoGrpcImport','open,draft,methods,save,visible,saving',{postGrpcMethodImportApiInfo:payload=>{writes.push(payload);return pending.promise}})
 await state.open();state.methods.value=[{id:1,client_streaming:true},{id:2,imported_api_info_id:7},{id:3}]
 state.draft.method_id=1;assert.equal(await state.save(),false)
 state.draft.method_id=2;assert.equal(await state.save(),false)
 Object.assign(state.draft,{method_id:3,project_product_id:[4,5],module_id:6,grpc_target:'127.0.0.1:50051'})
 const save=state.save();assert.equal(await state.save(),false)
 pending.reject(Error('offline'));assert.equal(await save,false)
 assert.equal(state.visible.value,true);assert.equal(state.saving.value,false)
 assert.deepEqual(writes,[{grpc_method_id:3,project_product_id:5,module_id:6,grpc_target:'127.0.0.1:50051'}])
 state.close()
})

test('gRPC sync fixes its original service and never loads another service on completion',async()=>{
 const pending=deferred(),writes=[],state=component('ApiInfoGrpcImport','open,draft,syncMethods,onServiceChange,syncing',{
  postGrpcMethodSync:payload=>{writes.push(payload);return pending.promise},
 })
 await state.open();await state.onServiceChange(1)
 const sync=state.syncMethods();await state.syncMethods();await state.onServiceChange(2)
 pending.resolve({msg:'ok'});await sync
 assert.deepEqual(writes,[{grpc_service_id:1}]);assert.equal(state.draft.service_id,2);assert.equal(state.syncing.value,false)
 state.close()
})

test('batch file upload snapshots the original file and failure retains selection',async()=>{
 const pending=deferred(),writes=[],state=component('ApiInfoBatchImport','open,selectedFile,save,saving,visible',{
  postApiUploadApi:file=>{writes.push(file);return pending.promise},
 })
 state.open();const file=new File(['example'],'example.xlsx');state.selectedFile.value=file
 const save=state.save();await state.save();state.selectedFile.value=new File(['other'],'other.xlsx')
 pending.reject(Error('offline'));assert.equal(await save,false);assert.equal(writes[0],file)
 assert.equal(state.visible.value,true);assert.equal(state.selectedFile.value.name,'other.xlsx');assert.equal(state.saving.value,false)
 state.close()
})

test('bound case reads ignore old APIs and closing also closes the nested case page',async()=>{
 const requests=[],state=component('ApiInfoBoundCases','open,rows,loading,casePanel,openCase',{
  getApiInfoBoundCases:()=>{const pending=deferred();requests.push(pending);return pending.promise},
 })
 const old=state.open(row(1)),current=state.open(row(2))
 requests[1].resolve({data:[{case_id:22,case_name:'Current'}]});await current
 requests[0].resolve({data:[{case_id:11}]});await old
 assert.equal(state.rows.value[0].case_id,22)
 state.openCase({case_id:22,case_name:'Current',project_product_id:2});assert.equal(state.casePanel.visible,true)
 state.exposed.close();assert.equal(state.casePanel.visible,false);assert.deepEqual(state.rows.value,[]);assert.equal(state.loading.value,false)
 state.close()
})

test('list filters keep lightweight pagination, leaf product IDs, modules and numeric zero',async()=>{
 const queries=[],state=page({getApiInfo:async query=>{queries.push(query);return {data:[],totalSize:0}}})
 state.conditionItems.find(item=>item.key==='project_product').value=[8,9]
 state.conditionItems.find(item=>item.key==='method').value=[0,1]
 state.conditionItems.find(item=>item.key==='status').value=[0]
 state.pagination.page=3;await state.doRefresh(null,false,true)
 assert.deepEqual(queries[0],{project_product:9,method__in:'0,1',status__in:'0',page:3,pageSize:20,summary:true})
 state.selection.value=[1];state.onResetSearch();await flush()
 assert.equal(state.pagination.page,1);assert.deepEqual(state.selection.value,[]);assert.deepEqual(queries[1],{page:1,pageSize:20,summary:true})
 state.close()
})

test('protocol switches invalidate late reads and page polling stays silent',async()=>{
 const requests=[],state=page({getApiInfo:()=>{const pending=deferred();requests.push(pending);return pending.promise}})
 const old=state.doRefresh(null,false,true);state.switchProtocol('sse')
 requests[1].resolve({data:[{...row(2),status:2}],totalSize:1});await flush()
 requests[0].resolve({data:[row(1)],totalSize:1});await old
 assert.equal(state.table.dataList[0].id,2);assert.equal(state.isPolling(),true)
 const polling=state.poll();assert.equal(state.table.tableLoading.value,false)
 requests[2].reject(Error('offline'));await polling;assert.equal(state.isPolling(),true)
 state.close()
})

test('delete confirmation snapshots IDs, blocks duplicates and keeps failed selection',async()=>{
 const pending=deferred(),writes=[],state=page({deleteApiInfo:ids=>{writes.push(ids);return pending.promise}})
 state.selection.value=['1','2'];state.onDelete(null);state.selection.value=['3'];state.onDelete(null)
 assert.equal(state.prompts.length,1)
 const save=state.prompts[0].config.onBeforeOk();assert.equal(await state.prompts[0].config.onBeforeOk(),false)
 pending.reject(Error('offline'));assert.equal(await save,false)
 assert.deepEqual(writes,[['1','2']]);assert.deepEqual(state.selection.value,['3']);assert.equal(state.deletingIds.size,0)
 state.close()
})

test('batch execution freezes releases and environment before runtime parameter discovery',async()=>{
 const parameters=deferred(),writes=[],targets=[],state=page({postApiInfoBatchRun:async(...args)=>{writes.push(args);return {data:{},msg:'ok'}}})
 state.table.dataList.push(row(1),row(2));state.selection.value=['1','2']
 state.runtimeParametersRef.value={prepare:value=>{targets.push(value);return parameters.promise},cancel(){parameters.resolve(null)}}
 const execution=state.onConcurrency();state.table.dataList[0].published_release_id=99;state.selection.value=['3'];state.user.selected_environment=4
 parameters.resolve({input:'example'});await execution
 assert.deepEqual(targets,[[{id:1,release_id:10},{id:2,release_id:10}]])
 assert.deepEqual(writes,[[[{api_info_id:1,api_info_release_id:10},{api_info_id:2,api_info_release_id:10}],0,{input:'example'}]])
 state.close()
})

test('unpublished batch entries never request runtime parameters or execute',async()=>{
 let prepared=0;const state=page();state.table.dataList.push({...row(),published_release_id:null});state.selection.value=['1']
 state.runtimeParametersRef.value={prepare:async()=>{prepared++;return {}},cancel(){}}
 await state.onConcurrency();assert.equal(prepared,0);state.close()
})

test('leaving the page cancels runtime discovery and closes all owned windows',async()=>{
 const parameters=deferred(),writes=[],state=page({getApiCaseInfoRun:(...args)=>writes.push(args)})
 let closed=0;for(const key of ['editorRef','grpcImportRef','batchImportRef','boundCasesRef'])state[key].value={close(){closed++}}
 state.runtimeParametersRef.value={prepare:()=>parameters.promise,cancel(){parameters.resolve(null)}}
 const running=state.onRunCase(row());await flush();state.deactivate();await running
 assert.deepEqual(writes,[]);assert.equal(closed,4);state.close()
})

test('recording failure keeps confirmation retryable and releases its loading state',async()=>{
 const pending=deferred(),writes=[],state=page({getSystemSocketNewBrowser:(...args)=>{writes.push(args);return pending.promise}})
 state.onBatchUpload();const starting=state.prompts[0].config.onBeforeOk()
 assert.equal(await state.prompts[0].config.onBeforeOk(),false)
 pending.reject(Error('offline'));assert.equal(await starting,false)
 assert.deepEqual(writes,[[null,1]]);assert.equal(state.recordingLoading.value,false);state.close()
})

test('detail navigation uses an ID without putting summary data in a global store',()=>{
 const state=page();state.onStep(row(8))
 assert.deepEqual(state.navigation,[{path:'/apitest/info/details',query:{id:8}}])
 assert.doesNotMatch(readFileSync(path.join(base,'index.vue'),'utf8'),/usePageData|pageData\.setRecord|v-if="false"/)
 state.close()
})

test('template download failure releases loading, blocks duplicates and retains the dialog',async()=>{
 const pending=deferred(),originalFetch=globalThis.fetch,requests=[]
 const state=component('ApiInfoBatchImport','open,downloadTemplate,downloading,visible')
 globalThis.fetch=url=>{requests.push(url);return pending.promise}
 try{
  state.open();const download=state.downloadTemplate();await state.downloadTemplate()
  assert.equal(state.downloading.value,true);assert.equal(requests.length,1)
  assert.match(requests[0],/^\/api\/download\?file_name=/)
  pending.resolve({ok:false,headers:{get:()=>null}});await download
  assert.equal(state.downloading.value,false);assert.equal(state.visible.value,true)
 }finally{globalThis.fetch=originalFetch;state.close()}
})

test('closing a pending upload prevents late success from clearing a different session',async()=>{
 const pending=deferred(),state=component('ApiInfoBatchImport','open,selectedFile,save,visible',{postApiUploadApi:()=>pending.promise})
 state.open();state.selectedFile.value=new File(['example'],'example.xlsx')
 const saving=state.save();state.exposed.close();pending.resolve({msg:'ok'})
 assert.equal(await saving,false);assert.deepEqual(state.events,[]);assert.equal(state.visible.value,false)
 state.close()
})
