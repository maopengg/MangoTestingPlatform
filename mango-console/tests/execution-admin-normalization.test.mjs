import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import ts from 'typescript'
import { parse,compileScript,compileTemplate,compileStyleAsync } from '@vue/compiler-sfc'
import { harness,deferred,flush } from './helpers/case-details-harness.mjs'
const base=path.resolve('src/views/system/execution-result')
const latest={};new Function('exports',ts.transpileModule(readFileSync('src/hooks/use-latest-request.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText)(latest)
const ok=(data,extra={})=>({code:200,data,...extra})
const configData=()=>({retention_days:7,expired_pending_count:0,cleanup_cron:'0 0 * * *',next_cleanup_at:'2026-11-10 00:00:00',source_type_options:[{key:'page',title:'页面'}],target_type_options:[{key:'api_case',title:'接口用例'}],status_options:[{key:0,title:'失败'}],test_env_options:[{key:0,title:'示例环境'}],result_state_options:[{key:'available',title:'结果可用'}],is_latest_options:[{key:'true',title:'最新结果'},{key:'false',title:'历史结果'}]})
const row=(id=1,extra={})=>({id,source_type:'page',target_type:'api_case',target_id:0,status:0,test_env:0,duration:'0.25',attempt_no:1,is_latest:false,has_result_data:true,result_cleaned:false,result_size:1024,...extra})
function setup(options={}){
 const route=vue.reactive({path:'/system/execution-result/index',fullPath:'/system/execution-result/index'}),user=vue.reactive({userId:1,roleId:1,token:'fixture',selected_environment:0}),permission=vue.reactive({permissionKeys:[]})
 const life={mount:[],activate:[],deactivate:[],unmount:[]},calls=[],dialogs=[],messages=[]
 const doc=Object.assign(new EventTarget(),{visibilityState:'visible'})
 const api={
  getExecutionResultAdminList:q=>{calls.push(['list',q]);return options.list?.(q)??Promise.resolve(ok([row()],{totalSize:1}))},
  getExecutionResultAdminConfig:()=>{calls.push(['config']);return options.config?.()??Promise.resolve(ok(configData()))},
  getUserName:()=>{calls.push(['users']);return options.users?.()??Promise.resolve(ok([{key:0,title:'Example'}]))},
  postExecutionResultAdminCleanup:()=>{calls.push(['cleanup']);return options.cleanup?.()??Promise.resolve(ok({updated_count:0}))},
 }
 const h=harness('index','conditionItems,rows,config,userOptions,cleanupLoading,listLoading,listError,configLoading,configError,usersLoading,usersError,enumLoading,enumError,pagination,cleanupReady,buildQuery,doRefresh,onSearch,onResetSearch,loadConfig,loadUsers,loadEnums,onCleanup,selectOptions,selectLoading,optionTagColor,resultState,formatDuration,formatBytes',{
  base,api,modules:{
   vue:{...vue,onMounted:f=>life.mount.push(f),onActivated:f=>life.activate.push(f),onDeactivated:f=>life.deactivate.push(f),onBeforeUnmount:f=>life.unmount.push(f)},
   'vue-router':{useRoute:()=>route},'@/store/modules/user':{default:()=>user},'@/store/modules/permission':{default:()=>permission},
   '@/hooks/use-latest-request':latest,
   '@/hooks/table':{useTable:()=>({indexColumn:{key:'index',width:100}}),useTableColumn:v=>v,useRowKey:()=> 'id',usePagination:(fn,loading)=>vue.reactive({page:1,pageSize:20,pageCount:0,setTotalSize(n){this.pageCount=n},onChange(){loading.value=true;return fn()}})},
   '@/store/modules/get-enum':{useEnum:()=>({colors:['blue','green'],getEnum:()=>options.enums?.()??Promise.resolve()})},
   '@arco-design/web-vue':{Message:Object.fromEntries(['success','error','warning'].map(kind=>[kind,text=>messages.push([kind,text])])),Modal:{confirm(config){const handle={config,closed:false,close(){this.closed=true}};dialogs.push(handle);return handle}}},
  },
 })
 let oldDoc,mounted=false
 return {...h,route,user,permission,life,calls,dialogs,messages,item:key=>h.conditionItems.find(item=>item.key===key),
  mount(){mounted=true;oldDoc=globalThis.document;globalThis.document=doc;life.mount.forEach(f=>f());life.activate.forEach(f=>f())},
  async visibility(value){doc.visibilityState=value;doc.dispatchEvent(new Event('visibilitychange'));await flush()},
  close(){if(mounted){life.unmount.forEach(f=>f());globalThis.document=oldDoc}h.close()},
 }
}
test('factory isolates condition arrays and custom ID ref with Chinese separators',t=>{
 const a=setup(),b=setup();t.after(a.close);t.after(b.close)
 a.item('id').value='2054、2014，2054';a.item('status').value.push(0);a.item('test_env').value.push(0);a.item('is_latest').value='false'
 assert.deepEqual(a.buildQuery(),{id__in:'2054,2014',status__in:'0',test_env__in:'0',is_latest:'false'})
 assert.deepEqual(b.buildQuery(),{});assert.equal(a.item('target_id').value,'');a.item('target_id').value='20、21';assert.equal(a.item('target_id').value,'')
 a.onResetSearch();assert.deepEqual(a.item('status').value,[]);assert.equal(a.item('is_latest').value,'')
})
test('whitelisted multi-select query preserves zero/long IDs and validates calendar ranges',t=>{
 const h=setup();t.after(h.close);const m=h.load('execution-admin.ts')
 h.item('source_type').value=['page','report','page'];h.item('target_type').value=['api_case'];h.item('trigger_user_id').value=[0,'90071992547409931234'];h.item('result_state').value=['available','cleaned'];h.item('create_time').value=['2024-02-29 00:00:00','2024-03-01 00:00:00']
 assert.deepEqual(h.buildQuery(),{source_type__in:'page,report',target_type__in:'api_case',trigger_user_id__in:'0,90071992547409931234',result_state__in:'available,cleaned',create_time_start:'2024-02-29 00:00:00',create_time_end:'2024-03-01 00:00:00'})
 for(const dates of [['2023-02-29 00:00:00','2023-03-01 00:00:00'],['2024-03-01 00:00:00','2024-02-29 00:00:00'],['2024-01-01 00:00:00']]){h.item('create_time').value=dates;assert.throws(h.buildQuery)}
 assert.deepEqual(m.buildExecutionAdminQuery([{key:'trace_id',value:' example '},{key:'status',value:null},{key:'test_env',value:undefined}]),{trace_id:'example'})
})
test('finite DTO parses nulls, zero IDs and booleans; malformed cleanup/config fails closed',t=>{
 const h=setup();t.after(h.close);const m=h.load('execution-admin.ts'),long='90071992547409931234'
 const result=m.parseExecutionAdminRows(ok([row(0),row(long,{test_suite:long,duration:null})],{totalSize:2}));assert.equal(result.rows[0].id,0);assert.equal(result.rows[0].target_id,0);assert.equal(result.rows[0].is_latest,false);assert.equal(result.rows[1].test_suite,long);assert.equal(result.rows[1].duration,null)
 assert.equal(m.parseExecutionAdminCleanup(ok({updated_count:0})),0);assert.throws(()=>m.parseExecutionAdminCleanup(ok({updated_count:'1'})))
 assert.throws(()=>m.parseExecutionAdminRows(ok([row(1,{is_latest:'false'})],{totalSize:1})))
 assert.throws(()=>m.parseExecutionAdminConfig(ok({...configData(),retention_days:0})))
 assert.throws(()=>m.parseExecutionAdminConfig(ok({...configData(),status_options:null})))
 assert.equal(m.parseExecutionAdminConfig(ok(configData())).options.test_env[0].key,0)
})
test('list loads independently of pending/failed metadata and all regions have retry',async t=>{
 const pending=deferred();let users=0;const h=setup({config:()=>pending.promise,users:()=>++users===1?Promise.reject(Error('offline')):Promise.resolve(ok([{key:0,title:'Recovered'}])),enums:()=>Promise.reject(Error('offline'))});t.after(h.close);h.mount();await flush()
 assert.equal(h.rows.value.length,1);assert.equal(h.listLoading.value,false);assert.equal(h.configLoading.value,true);assert.equal(h.cleanupReady.value,false)
 assert.ok(h.usersError.value);assert.ok(h.enumError.value);h.onCleanup();assert.equal(h.dialogs.length,0)
 pending.reject(Error('offline'));await flush();assert.equal(h.config.value,null);assert.ok(h.configError.value);assert.equal(h.configLoading.value,false)
 await h.loadUsers();assert.equal(h.usersError.value,'');assert.equal(h.userOptions.value[0].key,0)
})
test('search/reset page1, pagination retains page; list newest response and coalescing',async t=>{
 const a=deferred(),b=deferred();let n=0;const h=setup({list:()=>++n===1?a.promise:n===2?b.promise:Promise.resolve(ok([row(3)],{totalSize:50}))});t.after(h.close);h.mount();await flush()
 const same=h.doRefresh();assert.equal(h.calls.filter(c=>c[0]==='list').length,1);h.pagination.page=2;const newer=h.doRefresh();await flush();b.resolve(ok([row(2)],{totalSize:50}));await newer;a.resolve(ok([row(1)],{totalSize:50}));await same;assert.equal(h.rows.value[0].id,2)
 h.item('trace_id').value='example';await h.onSearch();assert.equal(h.calls.filter(c=>c[0]==='list').at(-1)[1].page,1)
 h.pagination.page=3;await h.pagination.onChange();assert.equal(h.calls.filter(c=>c[0]==='list').at(-1)[1].page,3)
 await h.onResetSearch();assert.deepEqual(h.calls.filter(c=>c[0]==='list').at(-1)[1],{page:1,pageSize:20})
})
test('invalid search stops older reads; later valid retry recovers local error',async t=>{
 const first=deferred();let n=0;const h=setup({list:()=>++n===1?first.promise:Promise.resolve(ok([row(2)],{totalSize:1}))});t.after(h.close);h.mount();await flush();h.item('create_time').value=['invalid'];await h.onSearch();assert.ok(h.listError.value)
 first.resolve(ok([row(99)],{totalSize:1}));await flush();assert.deepEqual(h.rows.value,[]);assert.equal(h.listLoading.value,false)
 await h.onResetSearch();assert.equal(h.rows.value[0].id,2);assert.equal(h.listError.value,'')
})
test('cleanup uses loaded retention, returns true after real success and refreshes both regions',async t=>{
 const h=setup();t.after(h.close);h.mount();await flush();h.onCleanup();const dialog=h.dialogs[0];assert.match(dialog.config.content,/7 天前/);assert.match(dialog.config.content,/0 条/)
 assert.equal(await dialog.config.onBeforeOk(),true);await flush();assert.match(h.messages.at(-1)[1],/0 条完整结果/);assert.equal(h.calls.filter(c=>c[0]==='cleanup').length,1);assert.equal(h.calls.filter(c=>c[0]==='config').length,2);assert.equal(h.calls.filter(c=>c[0]==='list').length,2);assert.equal(h.cleanupLoading.value,false)
})
test('cleanup failure keeps confirmation retryable; actual promise prevents duplicate writes',async t=>{
 const pending=deferred();let n=0;const h=setup({cleanup:()=>++n===1?Promise.reject({code:403}):pending.promise});t.after(h.close);h.mount();await flush();h.onCleanup();const dialog=h.dialogs[0]
 assert.equal(await dialog.config.onBeforeOk(),false);assert.equal(h.cleanupLoading.value,false);const operation=dialog.config.onBeforeOk();assert.equal(await dialog.config.onBeforeOk(),false);h.onCleanup();assert.equal(h.dialogs.length,1)
 pending.resolve(ok({updated_count:4}));assert.equal(await operation,true);assert.equal(h.calls.filter(c=>c[0]==='cleanup').length,2)
})
test('cancel/identity switch while cleanup pending retains physical lock and ignores old success',async t=>{
 const pending=deferred();const h=setup({cleanup:()=>pending.promise});t.after(h.close);h.mount();await flush();h.onCleanup();const dialog=h.dialogs[0];const operation=dialog.config.onBeforeOk();dialog.config.onCancel();h.user.roleId=2;await flush();h.onCleanup();assert.equal(h.dialogs.length,1);assert.equal(h.cleanupLoading.value,true)
 pending.resolve(ok({updated_count:3}));assert.equal(await operation,false);assert.equal(h.cleanupLoading.value,false);assert.equal(h.messages.filter(m=>m[0]==='success').length,0);assert.equal(h.cleanupReady.value,false);await flush();h.onCleanup();assert.equal(h.dialogs.length,2)
})
test('retained confirmation cannot send cleanup after background or role change',async t=>{
 const h=setup();t.after(h.close);h.mount();await flush();h.onCleanup();const old=h.dialogs[0];await h.visibility('hidden');assert.equal(old.closed,true);assert.equal(await old.config.onBeforeOk(),false);assert.equal(h.calls.filter(c=>c[0]==='cleanup').length,0)
 await h.visibility('visible');h.onCleanup();const next=h.dialogs[1];h.permission.permissionKeys.push('system.execution_result:read');await flush();assert.equal(next.closed,true);assert.equal(await next.config.onBeforeOk(),false)
})
test('all identity dependencies, KeepAlive and route changes invalidate old state',async t=>{
 const first=deferred();let n=0;const h=setup({list:()=>++n===1?first.promise:Promise.resolve(ok([row(2)],{totalSize:1}))});t.after(h.close);h.mount();await flush();h.user.userId=2;await flush();first.resolve(ok([row(99)],{totalSize:1}));await flush();assert.equal(h.rows.value[0].id,2)
 for(const change of [()=>h.user.token='changed-fixture',()=>h.user.selected_environment=3,()=>h.permission.permissionKeys.push('example'),()=>h.route.fullPath='/system/execution-result/index?example=1']){const count=h.calls.length;change();await flush();assert.ok(h.calls.length>count)}
 h.life.deactivate.forEach(f=>f());const count=h.calls.length;await h.doRefresh();assert.equal(h.calls.length,count);h.life.activate.forEach(f=>f());await flush();assert.ok(h.calls.length>count)
 h.route.path='/other';h.route.fullPath='/other';await flush();assert.deepEqual(h.rows.value,[]);assert.equal(h.config.value,null);assert.equal(h.listLoading.value,false)
})
test('formatters consume finite fields and latest boolean maps to backend option keys',async t=>{
 const h=setup();t.after(h.close);h.mount();await flush();assert.equal(h.formatDuration(null),'-');assert.equal(h.formatDuration(0),'0.00 秒');assert.equal(h.formatBytes(1024),'1.00 KB');assert.equal(h.optionTagColor('is_latest',false),'green');assert.equal(h.resultState(row(1,{result_cleaned:true})).text,'已清理')
})
test('page script, template and style compile',async()=>{
 const filename=path.join(base,'index.vue'),{descriptor,errors}=parse(readFileSync(filename,'utf8'),{filename});assert.deepEqual(errors,[]);const script=compileScript(descriptor,{id:filename});const template=compileTemplate({id:filename,filename,source:descriptor.template.content,compilerOptions:{bindingMetadata:script.bindings,expressionPlugins:['typescript']}});assert.deepEqual(template.errors,[])
 for(const style of descriptor.styles){const result=await compileStyleAsync({id:filename,filename,source:style.content,scoped:style.scoped});assert.deepEqual(result.errors,[])}
})
test('metadata from previous identity cannot replace retention policy or user options',async t=>{
 const config=deferred(),users=deferred();let c=0,u=0
 const h=setup({config:()=>++c===1?config.promise:Promise.resolve(ok({...configData(),retention_days:14})),users:()=>++u===1?users.promise:Promise.resolve(ok([{key:2,title:'Current'}]))});t.after(h.close);h.mount();await flush();h.user.roleId=2;await flush()
 config.resolve(ok(configData()));users.resolve(ok([{key:1,title:'Old'}]));await flush();assert.equal(h.config.value.retention_days,14);assert.equal(h.userOptions.value[0].key,2);assert.equal(h.configLoading.value,false)
})
test('config failure retries to enable cleanup; changed policy invalidates old confirmation',async t=>{
 let n=0;const h=setup({config:()=>++n===1?Promise.reject(Error('offline')):Promise.resolve(ok({...configData(),retention_days:n===2?7:14}))});t.after(h.close);h.mount();await flush()
 assert.equal(h.cleanupReady.value,false);await h.loadConfig();assert.equal(h.cleanupReady.value,true);h.onCleanup();const old=h.dialogs[0];await h.loadConfig();assert.equal(await old.config.onBeforeOk(),false);assert.equal(old.closed,true);assert.equal(h.calls.filter(c=>c[0]==='cleanup').length,0)
 h.onCleanup();assert.match(h.dialogs[1].config.content,/14 天前/)
})
test('failure of post-cleanup refresh does not turn successful write into repeatable failure',async t=>{
 let lists=0,configs=0;const h=setup({list:()=>++lists===1?Promise.resolve(ok([row()],{totalSize:1})):Promise.reject(Error('offline')),config:()=>++configs===1?Promise.resolve(ok(configData())):Promise.reject(Error('offline'))});t.after(h.close);h.mount();await flush();h.onCleanup();assert.equal(await h.dialogs[0].config.onBeforeOk(),true);await flush()
 assert.ok(h.listError.value);assert.ok(h.configError.value);assert.equal(h.cleanupLoading.value,false);assert.equal(h.calls.filter(c=>c[0]==='cleanup').length,1);assert.equal(h.messages.filter(m=>m[0]==='success').length,1)
})
test('cleanup completion forces reads newer than requests already pending before the write',async t=>{
 const oldList=deferred(),oldConfig=deferred(),cleanup=deferred();let lists=0,configs=0
 const h=setup({list:()=>++lists===2?oldList.promise:Promise.resolve(ok([row(lists)],{totalSize:1})),config:()=>++configs===2?oldConfig.promise:Promise.resolve(ok({...configData(),retention_days:configs===3?14:7})),cleanup:()=>cleanup.promise})
 t.after(h.close);h.mount();await flush();h.onCleanup();const operation=h.dialogs[0].config.onBeforeOk();const read=h.doRefresh(),metadata=h.loadConfig();await flush()
 cleanup.resolve(ok({updated_count:1}));assert.equal(await operation,true);await flush();assert.equal(lists,3);assert.equal(configs,3);assert.equal(h.rows.value[0].id,3);assert.equal(h.config.value.retention_days,14)
 oldList.resolve(ok([row(99)],{totalSize:1}));oldConfig.resolve(ok(configData()));await Promise.all([read,metadata]);assert.equal(h.rows.value[0].id,3);assert.equal(h.config.value.retention_days,14)
})
