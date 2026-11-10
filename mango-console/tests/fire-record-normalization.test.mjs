import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import ts from 'typescript'
import { parse,compileTemplate,compileStyleAsync } from '@vue/compiler-sfc'
import { deferred,flush } from './helpers/case-details-harness.mjs'
const base=path.resolve('src/views/system/fire-record')
const compile=source=>ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText
const ok=(data,extra={})=>({code:200,data,...extra})
const row=(id=1,extra={})=>({id,task_name:'Example fire',source_type:0,source_type_name:'测试套执行',status:0,status_name:'待分发',test_suite:{id:0},...extra})
function setup(options={}) {
 const route=vue.reactive({path:'/timing/fire-record/index',fullPath:'/timing/fire-record/index'}),user=vue.reactive({userId:1,roleId:1,token:'fixture',selected_environment:0}),permission=vue.reactive({permissionKeys:[]})
 const doc=Object.assign(new EventTarget(),{visibilityState:'visible'}),life={mount:[],activate:[],deactivate:[],unmount:[]},calls=[],navigation=[],messages=[]
 const modules={
  vue:{...vue,onMounted:f=>life.mount.push(f),onActivated:f=>life.activate.push(f),onDeactivated:f=>life.deactivate.push(f),onBeforeUnmount:f=>life.unmount.push(f)},
  '@arco-design/web-vue':{Message:{error:message=>messages.push(message)}},
  'vue-router':{useRoute:()=>route,useRouter:()=>({push:q=>{navigation.push(q);return options.navigate?.(q)??Promise.resolve()}})},
  '@/store/modules/user':{default:()=>user},'@/store/modules/permission':{default:()=>permission},
  '@/store/modules/get-enum':{useEnum:()=>({colors:['blue','green'],getEnum:()=>options.enums?.()??Promise.resolve()})},
  '@/hooks/table':{useTableIndexColumn:()=>({key:'index',width:100}),useTableColumn:v=>v,useRowKey:()=> 'id',usePagination:(fn,loading)=>vue.reactive({page:1,pageSize:20,pageCount:0,setTotalSize(n){this.pageCount=n},onChange(){loading.value=true;return fn()}})},
  '@/api/system/tasks':{getSystemTaskFireRecord:query=>{calls.push(query);return options.list?.(query)??Promise.resolve(ok([row()],{totalSize:1}))}},
 }
 const cache=new Map()
 function resolve(id,dir){
  if(id in modules)return modules[id]
  if(id.startsWith('.'))return load(path.resolve(dir,id)+'.ts')
  if(id.startsWith('@/'))return load(path.resolve('src',id.slice(2))+'.ts')
  { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error('Unmocked '+id) }
 }
 function load(file){if(cache.has(file))return cache.get(file);const exports={};cache.set(file,exports);new Function('exports','require',compile(readFileSync(file,'utf8')))(exports,id=>resolve(id,path.dirname(file)));return exports}
 const file=path.join(base,'index.vue'),descriptor=parse(readFileSync(file,'utf8')).descriptor,exports={}
 new Function('exports','require',compile(descriptor.script.content))(exports,id=>resolve(id,base))
 const scope=vue.effectScope(),page=scope.run(()=>exports.default.setup())
 let previous,mounted=false
 return {...page,route,user,permission,life,calls,navigation,messages,component:exports.default,
  item:key=>page.conditionItems.find(item=>item.key===key),load:()=>load(path.join(base,'fire-record.ts')),
  mount(){mounted=true;previous=globalThis.document;globalThis.document=doc;life.mount.forEach(f=>f());life.activate.forEach(f=>f())},
  async visibility(value){doc.visibilityState=value;doc.dispatchEvent(new Event('visibilitychange'));await flush()},
  close(){if(mounted){life.unmount.forEach(f=>f());globalThis.document=previous}scope.stop()},
 }
}
test('Options API name retained and factory owns independent arrays/options with multi-select reset',t=>{
 const a=setup(),b=setup();t.after(a.close);t.after(b.close);assert.equal(a.component.name,'TimingFireRecord')
 a.item('status').value.push(0,4);a.item('source_type').value.push(0);a.item('task_name').value=' Example '
 assert.deepEqual(a.buildQuery(),{task_name:'Example',status__in:'0,4',source_type__in:'0'});assert.deepEqual(b.buildQuery(),{})
 a.item('source_type').optionItems[0].label='Changed';assert.equal(b.item('source_type').optionItems[0].label,'测试套执行')
 a.onResetSearch();assert.deepEqual(a.item('source_type').value,[]);assert.deepEqual(a.item('status').value,[]);assert.equal(a.item('task_name').value,'')
})
test('DTO preserves ID0/long report links and finite status; rejects malformed envelopes',t=>{
 const h=setup();t.after(h.close);const m=h.load(),long='90071992547409931234'
 const r=m.parseFireRecords(ok([row(0,{time_task:{name:'Example policy'}}),row(long,{test_suite:long,status:4}),row(0)],{totalSize:2}))
 assert.equal(r.rows.length,2);assert.equal(r.rows[0].id,0);assert.equal(r.rows[0].test_suite,0);assert.equal(r.rows[0].time_task.name,'Example policy');assert.equal(r.rows[1].test_suite,long)
 assert.equal(m.fireReportId({id:long}),long);for(const value of [null,{},false,'',-1,1.5,Number.MAX_SAFE_INTEGER+1])assert.equal(m.fireReportId(value),null)
 assert.equal(m.parseFireRecords(ok([row(1,{test_suite:null,status:null})],{totalSize:1})).rows[0].status,null)
 assert.throws(()=>m.parseFireRecords({code:403,data:[],totalSize:0}));assert.throws(()=>m.parseFireRecords(ok({}, {totalSize:1})));assert.throws(()=>m.parseFireRecords(ok([],{totalSize:'0'})))
})
test('list does not wait for enum request and independent enum retry recovers',async t=>{
 const pending=deferred();let n=0;const h=setup({enums:()=>++n===1?pending.promise:Promise.resolve()});t.after(h.close);h.mount();await flush()
 assert.equal(h.rows.value.length,1);assert.equal(h.listLoading.value,false);assert.equal(h.enumLoading.value,true)
 pending.reject(Error('offline'));await flush();assert.equal(h.enumLoading.value,false);assert.ok(h.enumError.value);await h.loadEnums();assert.equal(h.enumError.value,'');assert.equal(h.calls.length,1)
})
test('same reads coalesce, latest page wins, search/reset return to page1',async t=>{
 const a=deferred(),b=deferred();let n=0;const h=setup({list:()=>++n===1?a.promise:n===2?b.promise:Promise.resolve(ok([row(3)],{totalSize:60}))});t.after(h.close);h.mount();await flush()
 const same=h.doRefresh();assert.equal(h.calls.length,1);h.pagination.page=2;const refresh=h.doRefresh();await flush();b.resolve(ok([row(2)],{totalSize:60}));await refresh;a.resolve(ok([row(1)],{totalSize:60}));await same;assert.equal(h.rows.value[0].id,2)
 h.item('status').value=[0];await h.onSearch();assert.deepEqual(h.calls.at(-1),{status__in:'0',page:1,pageSize:20})
 h.pagination.page=3;await h.pagination.onChange();assert.equal(h.calls.at(-1).page,3);await h.onResetSearch();assert.deepEqual(h.calls.at(-1),{page:1,pageSize:20})
})
test('list rejection clears loading and supports repeat without frontend permission gating',async t=>{
 let n=0;const h=setup({list:()=>++n===1?Promise.reject({code:403}):Promise.resolve(ok([row(2)],{totalSize:1}))});t.after(h.close);h.mount();await flush();assert.ok(h.listError.value);assert.equal(h.listLoading.value,false);assert.deepEqual(h.rows.value,[])
 await h.doRefresh();assert.equal(h.calls.length,2);assert.equal(h.rows.value[0].id,2);assert.equal(h.listError.value,'');assert.deepEqual(h.permission.permissionKeys,[])
})
test('report navigation permits zero/string IDs, ignores missing values, prevents duplicate and unlocks failure',async t=>{
 const pending=deferred();let n=0;const h=setup({navigate:()=>++n===1?pending.promise:Promise.resolve()});t.after(h.close);h.mount();await flush()
 await h.openReport({...h.rows.value[0],test_suite:null});assert.equal(h.navigation.length,0)
 const operation=h.openReport(h.rows.value[0]);await h.openReport(h.rows.value[0]);assert.equal(h.navigation.length,1);assert.deepEqual(h.navigation[0],{path:'/report/system/details',query:{id:0}})
 pending.reject(Error('aborted'));await operation;assert.equal(h.reportOpening.value,false);assert.ok(h.messages.length)
 await h.openReport({...h.rows.value[0],test_suite:'90071992547409931234'});assert.equal(h.navigation[1].query.id,'90071992547409931234')
})
test('resolved navigation failure is visible and stale rejection does not affect new context',async t=>{
 let n=0;const pending=deferred();const h=setup({navigate:()=>++n===1?Promise.resolve({type:4}):pending.promise});t.after(h.close);h.mount();await flush();await h.openReport(h.rows.value[0]);assert.equal(h.messages.length,1)
 const operation=h.openReport(h.rows.value[0]);h.user.roleId=2;await flush();assert.equal(h.reportOpening.value,true);await h.openReport(h.rows.value[0]);assert.equal(h.navigation.length,2)
 pending.reject(Error('old'));await operation;assert.equal(h.messages.length,1);assert.equal(h.reportOpening.value,false)
})
test('identity changes reject old data and all dependencies issue current reads',async t=>{
 const first=deferred();let n=0;const h=setup({list:()=>++n===1?first.promise:Promise.resolve(ok([row(2)],{totalSize:1}))});t.after(h.close);h.mount();await flush();h.user.roleId=2;await flush();first.resolve(ok([row(99)],{totalSize:1}));await flush();assert.equal(h.rows.value[0].id,2)
 for(const change of [()=>h.user.userId=2,()=>h.user.token='changed-fixture',()=>h.user.selected_environment=3,()=>h.permission.permissionKeys.push('timing.fire_record:read'),()=>h.route.fullPath='/timing/fire-record/index?example=1']){const count=h.calls.length;change();await flush();assert.ok(h.calls.length>count)}
})
test('background/KeepAlive/route pause reads and resume reloads, without a page timer',async t=>{
 const h=setup();t.after(h.close);h.mount();await flush();await h.visibility('hidden');const count=h.calls.length;await h.doRefresh();assert.equal(h.calls.length,count);assert.equal(h.listLoading.value,false)
 await h.visibility('visible');assert.ok(h.calls.length>count);h.life.deactivate.forEach(f=>f());const before=h.calls.length;await h.doRefresh();assert.equal(h.calls.length,before);h.life.activate.forEach(f=>f());await flush();assert.ok(h.calls.length>before)
 h.route.path='/other';h.route.fullPath='/other';await flush();assert.deepEqual(h.rows.value,[]);const away=h.calls.length;await h.doRefresh();assert.equal(h.calls.length,away)
})
test('source0/status presentation matches backend schedule-fire choices',()=>{
 const h=setup();try{assert.equal(h.sourceTypeColor(0),'blue');assert.equal(h.statusColor(0),'orange');assert.equal(h.statusColor(3),'green');assert.equal(h.statusColor(4),'red');assert.equal(h.statusColor(6),'gray')}finally{h.close()}
})
test('actual Options API script, template and styles compile',async()=>{
 const filename=path.join(base,'index.vue'),{descriptor,errors}=parse(readFileSync(filename,'utf8'),{filename});assert.deepEqual(errors,[]);assert.equal(descriptor.scriptSetup,null)
 const diagnostics=ts.transpileModule(descriptor.script.content,{reportDiagnostics:true,compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).diagnostics;assert.deepEqual(diagnostics,[])
 const template=compileTemplate({id:filename,filename,source:descriptor.template.content,compilerOptions:{expressionPlugins:['typescript']}});assert.deepEqual(template.errors,[])
 for(const style of descriptor.styles){const result=await compileStyleAsync({id:filename,filename,source:style.content,scoped:style.scoped});assert.deepEqual(result.errors,[])}
})
