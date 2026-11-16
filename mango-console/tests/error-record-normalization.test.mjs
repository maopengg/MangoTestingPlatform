import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse,compileScript,compileTemplate,compileStyleAsync } from '@vue/compiler-sfc'
import { harness,deferred,flush } from './helpers/case-details-harness.mjs'
const base=path.resolve('src/views/system/error-record')
const row=(id=1,extra={})=>({source:'system_error_event',event_source:'http',object_id:id,title:'Example',message:'Failure',status:'warning',status_name:'待排查',traceback:'Line 1\nLine 2',...extra})
const ok=(data=[row()],totalSize=data.length)=>({code:200,data,totalSize})
test('recovered health incidents keep their evidence and use success colors in list and detail',t=>{
  const h=setup();t.after(h.close);const m=h.load('error-record.ts')
  const recovered=row(343,{status:'success',status_name:'已恢复',exception_type:'DatasourceExecutionHealth',traceback:'{"active":false,"resolved_at":1}'})
  const parsed=m.parseErrorRecords(ok([recovered])).rows[0]
  assert.equal(parsed.status_name,'已恢复');assert.equal(parsed.traceback,recovered.traceback)
  assert.equal(m.errorRecordStatusColor(parsed.status),'green')
  assert.equal(m.errorRecordStatusColor('warning'),'orange');assert.equal(m.errorRecordStatusColor('error'),'red')
  assert.equal(m.errorRecordStatusColor(4),'red');assert.equal(m.errorRecordStatusColor(null),'red')
  const source=readFileSync(path.join(base,'index.vue'),'utf8')
  assert.ok(source.includes('errorRecordStatusColor(record.status)'))
  assert.ok(source.includes('errorRecordStatusColor(detail.record.status)'))
})
function setup(options={}) {
  const life={mount:[],activate:[],deactivate:[],unmount:[]},calls=[],messages=[],navigations=[],windows=[],copies=[]
  const route=vue.reactive({path:'/system/error-record/index',fullPath:'/system/error-record/index'})
  const user=vue.reactive({userId:1,roleId:1,token:'fixture',selected_environment:0}),permission=vue.reactive({permissionKeys:[]})
  const doc=Object.assign(new EventTarget(),{visibilityState:'visible'})
  const h=harness('index','conditionItems,rows,pagination,listLoading,listError,enumLoading,enumError,detail,tracebackLineCount,copying,sourceOpening,buildQuery,doRefresh,onSearch,onResetSearch,loadEnums,openDetail,closeDetail,copyText,copyErrorDetail,openLog,openSource,sourceTypeColor',{
    base, transformSource:source=>source.replace('import.meta.env.VITE_APP_LOG_PLATFORM_URL',JSON.stringify(options.logUrl||'')),
    api:{getSystemErrorRecordList:query=>{calls.push({...query});return options.list?.(query)??Promise.resolve(ok())}},
    modules:{
      vue:{...vue,onMounted:f=>life.mount.push(f),onActivated:f=>life.activate.push(f),onDeactivated:f=>life.deactivate.push(f),onBeforeUnmount:f=>life.unmount.push(f)},
      'vue-router':{useRoute:()=>route,useRouter:()=>({push:route=>{navigations.push(route);return options.navigate?.(route)??Promise.resolve()}})},
      '@/store/modules/user':{default:()=>user},'@/store/modules/permission':{default:()=>permission},
      '@/hooks/table':{useTableColumn:v=>v,usePagination:(fn,loading)=>vue.reactive({page:1,pageSize:20,pageCount:0,setTotalSize(n){this.pageCount=n},onChange(){loading.value=true;return fn()}})},
      '@/store/modules/get-enum':{useEnum:()=>({colors:['blue'],getEnum:()=>options.enums?.()??Promise.resolve()})},
      '@arco-design/web-vue':{Message:Object.fromEntries(['success','error','warning'].map(kind=>[kind,message=>messages.push([kind,message])]))},
      '@arco-design/web-vue/es/icon':{IconCopy:{}},
    },
  })
  const clipboard={writeText:value=>{copies.push(value);return options.copy?.(value)??Promise.resolve()}}
  let oldDoc,oldNav,oldWindow,mounted=false
  return {...h,calls,messages,navigations,windows,copies,life,route,user,permission,
    item:key=>h.conditionItems.find(item=>item.key===key),
    mount(){mounted=true;oldDoc=globalThis.document;oldNav=Object.getOwnPropertyDescriptor(globalThis,'navigator');oldWindow=globalThis.window;globalThis.document=doc;Object.defineProperty(globalThis,'navigator',{configurable:true,value:{clipboard:options.noClipboard?undefined:clipboard}});globalThis.window={location:{origin:'https://example.com'},open:(...args)=>windows.push(args)};life.mount.forEach(f=>f());life.activate.forEach(f=>f())},
    async visibility(value){doc.visibilityState=value;doc.dispatchEvent(new Event('visibilitychange'));await flush()},
    close(){if(mounted){life.unmount.forEach(f=>f());globalThis.document=oldDoc;globalThis.window=oldWindow;if(oldNav)Object.defineProperty(globalThis,'navigator',oldNav);else delete globalThis.navigator}h.close()},
  }
}
test('condition factory separates arrays/options and preserves custom comma protocol',t=>{
  const a=setup(),b=setup();t.after(a.close);t.after(b.close)
  a.item('source').value.push('http,drf','http,drf','scheduler');a.item('category').value='schedule_fire';a.item('keyword').value='  Example  '
  assert.deepEqual(a.buildQuery(),{category:'schedule_fire',keyword:'Example',source:'http,drf,scheduler'})
  assert.deepEqual(b.buildQuery(),{});assert.equal(a.item('category').multiple,undefined);assert.equal(a.item('source').multiple,true)
  a.item('source').optionItems.push({label:'Extra',value:'extra'});assert.equal(b.item('source').optionItems.length,10)
  a.onResetSearch();assert.deepEqual(a.item('source').value,[]);assert.equal(a.pagination.page,1)
})
test('finite response parses zero/long ID, composite key, count/status and redacted fields',t=>{
  const h=setup();t.after(h.close);const m=h.load('error-record.ts')
  const long='90071992547409931234';const result=m.parseErrorRecords(ok([row(0,{count:0}),row(long),row(0,{source:'schedule_fire',status:3}),row(0)]))
  assert.equal(result.rows.length,3);assert.equal(result.rows[0].count,0);assert.equal(result.rows[1].object_id,long);assert.equal(result.rows[2].status,3)
  assert.notEqual(result.rows[0].__rowKey,result.rows[2].__rowKey)
  assert.match(m.errorRecordDetail(result.rows[0]),/记录ID：0/)
  assert.throws(()=>m.parseErrorRecords({code:403,data:[],totalSize:0}));assert.throws(()=>m.parseErrorRecords(ok({},1)));assert.deepEqual(m.parseErrorRecords(ok([],null)),{rows:[],total:0})
  assert.equal(m.parseErrorRecords(ok([row(1,{traceback:undefined,link:undefined,log_query:undefined})])).rows[0].traceback,'')
})
test('list runs independently of enum failure; retry, local loading and coalescing work',async t=>{
  let n=0;const first=deferred();const h=setup({list:()=>++n===1?first.promise:Promise.resolve(ok([row(2)])),enums:()=>Promise.reject(Error('offline'))});t.after(h.close)
  h.mount();await flush();assert.equal(h.calls.length,1);const same=h.doRefresh();assert.equal(h.calls.length,1)
  first.reject(Error('offline'));await same;assert.equal(h.listLoading.value,false);assert.match(h.listError.value,/重试/);assert.ok(h.enumError.value)
  await h.doRefresh();assert.equal(h.rows.value[0].object_id,2);assert.equal(h.listError.value,'')
})
test('search and reset return to page1; pagination keeps page and newest response wins',async t=>{
  const a=deferred(),b=deferred();let n=0;const h=setup({list:()=>++n===1?a.promise:n===2?b.promise:Promise.resolve(ok())});t.after(h.close)
  h.mount();await flush();h.pagination.page=3;const refresh=h.doRefresh();await flush();b.resolve(ok([row(3)],100));await refresh;a.resolve(ok([row(1)],100));await flush();assert.equal(h.rows.value[0].object_id,3)
  h.item('keyword').value='Example';await h.onSearch();assert.equal(h.calls.at(-1).page,1)
  h.pagination.page=2;await h.pagination.onChange();assert.equal(h.calls.at(-1).page,2)
  await h.onResetSearch();assert.deepEqual(h.calls.at(-1),{page:1,pageSize:20})
})
test('detail owns a snapshot; copy has physical duplicate guard and stale feedback suppressed',async t=>{
  const copy=deferred();const h=setup({copy:()=>copy.promise});t.after(h.close);h.mount();await flush()
  const source=h.rows.value[0];h.openDetail(source);source.message='Changed';assert.equal(h.detail.record.message,'Failure');assert.equal(h.tracebackLineCount.value,2)
  const pending=h.copyErrorDetail();await h.copyErrorDetail();assert.equal(h.copies.length,1);h.closeDetail();h.openDetail(row(2));assert.equal(h.copying.value,true)
  copy.resolve();await pending;assert.equal(h.messages.filter(m=>m[0]==='success').length,0);assert.equal(h.copying.value,false);assert.equal(h.detail.record.object_id,2)
})
test('copy failure recovers and log fallback waits for real clipboard result',async t=>{
  let n=0;const h=setup({copy:()=>++n===1?Promise.reject(Error('denied')):Promise.resolve()});t.after(h.close);h.mount();await flush()
  await h.openLog('service="example"');assert.equal(h.messages.at(-1)[0],'error');assert.equal(h.copying.value,false)
  await h.openLog('service="example"');assert.deepEqual(h.messages.at(-1),['success','日志查询条件已复制'])
})
test('missing clipboard reports failure; closing panel clears the selected snapshot',async t=>{
  const h=setup({noClipboard:true});t.after(h.close);h.mount();await flush();h.openDetail(h.rows.value[0]);await h.copyErrorDetail();assert.equal(h.messages.at(-1)[0],'error')
  h.detail.visible=false;await flush();assert.equal(h.detail.record,null)
})
test('log URL retains query/hash with safe encoding and opener isolation',async t=>{
  const h=setup({logUrl:'https://example.org/logs?tenant=example#search'});t.after(h.close);h.mount();await flush();await h.openLog('message="a&b"')
  const [url,target,features]=h.windows[0];assert.equal(target,'_blank');assert.equal(features,'noopener,noreferrer');const parsed=new URL(url);assert.equal(parsed.searchParams.get('tenant'),'example');assert.equal(parsed.searchParams.get('query'),'message="a&b"');assert.equal(parsed.hash,'#search')
  const m=h.load('error-record.ts');assert.equal(m.errorRecordLogUrl('javascript:alert(1)','x','https://example.com'),null)
  assert.equal(m.errorRecordLogUrl('https://user:password@example.org','x','https://example.com'),null)
})
test('source route guards external links; rejected navigation unlocks retry',async t=>{
  const pending=deferred();const h=setup({navigate:()=>pending.promise});t.after(h.close);h.mount();await flush()
  await h.openSource('//example.org');assert.equal(h.navigations.length,0)
  const request=h.openSource('/timing/fire-record/index');await h.openSource('/timing/fire-record/index');assert.equal(h.navigations.length,1)
  pending.reject(Error('cancelled'));await request;assert.equal(h.sourceOpening.value,false);assert.equal(h.messages.at(-1)[0],'error')
})
test('identity/background/KeepAlive invalidate rows and detail and resume fresh reads',async t=>{
  const first=deferred();let n=0;const h=setup({list:()=>++n===1?first.promise:Promise.resolve(ok([row(2)]))});t.after(h.close)
  h.mount();await flush();h.openDetail(row(1));h.user.roleId=2;await flush();assert.equal(h.detail.visible,false)
  first.resolve(ok([row(99)]));await flush();assert.equal(h.rows.value[0].object_id,2)
  await h.visibility('hidden');const count=h.calls.length;await h.doRefresh();assert.equal(h.calls.length,count)
  await h.visibility('visible');assert.ok(h.calls.length>count)
  h.life.deactivate.forEach(f=>f());const before=h.calls.length;await h.doRefresh();assert.equal(h.calls.length,before);h.life.activate.forEach(f=>f());await flush();assert.ok(h.calls.length>before)
  h.route.path='/other';h.route.fullPath='/other';await flush();assert.deepEqual(h.rows.value,[])
})
test('all identity dependencies close detail and trigger an authorized fresh read',async t=>{
  const h=setup();t.after(h.close);h.mount();await flush()
  for(const change of [()=>h.user.userId=2,()=>h.user.token='changed-fixture',()=>h.user.selected_environment=3,()=>h.permission.permissionKeys.push('system.error_record:read'),()=>h.route.fullPath='/system/error-record/index?example=1']){
    h.openDetail(h.rows.value[0]);const count=h.calls.length;change();await flush();assert.equal(h.detail.visible,false);assert.ok(h.calls.length>count)
  }
})
test('enum retry clears its own failure without delaying or clearing the list',async t=>{
  let n=0;const h=setup({enums:()=>++n===1?Promise.reject(Error('offline')):Promise.resolve()});t.after(h.close);h.mount();await flush()
  assert.ok(h.enumError.value);assert.equal(h.rows.value.length,1);await h.loadEnums();assert.equal(h.enumError.value,'');assert.equal(h.enumLoading.value,false);assert.equal(h.calls.length,1)
})
test('actual page, public side panel scripts/templates/styles compile',async()=>{
  for(const filename of [path.join(base,'index.vue'),path.resolve('src/components/overlays/BaseSidePanel.vue')]){
    const {descriptor,errors}=parse(readFileSync(filename,'utf8'),{filename});assert.deepEqual(errors,[])
    const script=compileScript(descriptor,{id:filename});const template=compileTemplate({id:filename,filename,source:descriptor.template.content,compilerOptions:{bindingMetadata:script.bindings,expressionPlugins:['typescript']}});assert.deepEqual(template.errors,[])
    for(const style of descriptor.styles){const result=await compileStyleAsync({id:filename,filename,source:style.content,scoped:style.scoped});assert.deepEqual(result.errors,[])}
  }
})
