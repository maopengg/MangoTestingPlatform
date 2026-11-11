import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import * as Vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
import { loadTableHooks } from './helpers/table-hooks.mjs'

function setup(read, { initialLoading = false, initialRows = [{id:'9007199254740993'},{id:2}] } = {}) {
  const rows=Vue.ref(initialRows), listLoading=Vue.ref(initialLoading)
  const user=Vue.reactive({userId:1,roleId:1,token:'fixture'}), feedback=[],cleanups=[], activations=[], deactivations=[]
  let closes=0
  const modules={vue:{...Vue,onBeforeUnmount:fn=>cleanups.push(fn),onDeactivated:fn=>deactivations.push(fn),onActivated:fn=>activations.push(fn)},
    '@/store/modules/user':{default:()=>user},'@/utils/load-error':{reportLoadError:error=>feedback.push(error)}}
  const exports={}
  const code=ts.transpileModule(readFileSync('src/hooks/useCaseReferenceCounts.ts','utf8'),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},
  }).outputText
  new Function('exports','require',code)(exports,id=>modules[id])
  const scope=Vue.effectScope(),columns=[{key:'name'},{key:'status'},{key:'tags'},{key:'project_product'},{key:'actions'}]
  const state=scope.run(()=>exports.useCaseReferenceCounts(()=>rows.value,columns,read,()=>listLoading.value,()=>closes++))
  return {...state,rows,listLoading,user,feedback,columns,closes:()=>closes,
    activate:()=>activations.forEach(fn=>fn()),deactivate:()=>deactivations.forEach(fn=>fn()),
    close:()=>{cleanups.forEach(fn=>fn());scope.stop()}}
}

test('counts load automatically for the current page, preserve IDs and always show the count column',async()=>{
  const calls=[],state=setup(async ids=>{calls.push(ids);return {data:{'9007199254740993':3,'2':0,'3':5}}})
  await flush()
  assert.deepEqual(calls,[['9007199254740993',2]])
  assert.equal(state.counts.value['2'],0)
  assert.deepEqual(state.tableColumns.value.map(column=>column.key),['name','status','case_reference_count','tags','project_product','actions'])
  state.rows.value=[...state.rows.value];await flush();assert.equal(calls.length,1)
  state.rows.value=[{id:3}];await flush();assert.equal(calls.length,2)
  assert.deepEqual(state.counts.value,{'3':5})
  state.close()
})

test('page changes reject late counts, wait for lists and refresh only the new page',async()=>{
  const requests=[],state=setup(ids=>{const pending=deferred();requests.push({ids,pending});return pending.promise})
  state.listLoading.value=true;await flush()
  requests[0].pending.resolve({data:{'9007199254740993':99,'2':99}});await flush()
  assert.deepEqual(state.counts.value,{})
  state.rows.value=[{id:3}];state.listLoading.value=false;await flush()
  assert.equal(requests.length,2);assert.deepEqual(requests[1].ids,[3])
  requests[1].pending.resolve({data:{3:5}});await flush()
  assert.deepEqual(state.counts.value,{'3':5})
  state.close()
})

test('role switch and deactivation clear counts, close details and ignore old results',async()=>{
  const pending=deferred(),state=setup(()=>pending.promise)
  state.user.roleId=2
  pending.resolve({data:{'9007199254740993':9,'2':9}});await flush()
  assert.deepEqual(state.counts.value,{})
  assert.ok(state.closes()>0)
  state.close()
})

test('in-place table row replacement also reloads the current-page counts',async()=>{
  const calls=[],state=setup(async ids=>{calls.push(ids);return {data:Object.fromEntries(ids.map(id=>[id,1]))}})
  await flush()
  state.rows.value.splice(0,state.rows.value.length,{id:3});await flush()
  assert.deepEqual(calls,[['9007199254740993',2],[3]])
  assert.deepEqual(state.counts.value,{'3':1})
  state.close()
})

test('default-enabled assets are excluded from the count request, including zero-request default-only pages',async()=>{
  const calls=[],state=setup(async ids=>{calls.push(ids);return {data:{2:0}}},
    {initialRows:[{id:1,status:1},{id:2,status:0}]})
  await flush()
  assert.deepEqual(calls,[[2]])
  assert.deepEqual(state.counts.value,{'2':0})
  state.rows.value[1].status=1;await flush()
  assert.equal(calls.length,1);assert.deepEqual(state.counts.value,{})
  assert.equal(state.loading.value,false)
  state.close()
})

test('enabling a default clears stale numbers and disabling it automatically restarts counting',async()=>{
  const requests=[],state=setup(ids=>{const pending=deferred();requests.push({ids,pending});return pending.promise},
    {initialRows:[{id:1,status:0}]})
  state.rows.value[0].status=1;await flush()
  requests[0].pending.resolve({data:{1:99}});await flush()
  assert.deepEqual(state.counts.value,{})
  state.rows.value[0].status=0;await flush()
  assert.equal(requests.length,2);assert.deepEqual(requests[1].ids,[1])
  requests[1].pending.resolve({data:{1:3}});await flush()
  assert.deepEqual(state.counts.value,{'1':3})
  state.close()
})

test('failed or malformed counts never look like zero and may be retried',async()=>{
  let invalid=true
  const state=setup(async()=>({data:invalid?{}:{'9007199254740993':1,'2':0}}))
  await flush();assert.deepEqual(state.counts.value,{})
  assert.equal(state.loading.value,false);assert.equal(state.feedback.length,1)
  invalid=false;await state.refresh()
  assert.equal(state.counts.value['2'],0)
  state.close()
})

test('all three pages and the reused drawer compile and use the independent readers',()=>{
  const files=['src/views/apitest/public/index.vue','src/views/apitest/headers/index.vue',
    'src/views/uitest/public/index.vue','src/views/apitest/info/components/ApiInfoBoundCases.vue']
  for(const filename of files){
    const source=readFileSync(filename,'utf8'),{descriptor}=parse(source),script=compileScript(descriptor,{id:filename})
    assert.deepEqual(compileTemplate({source:descriptor.template.content,filename,id:filename,compilerOptions:{bindingMetadata:script.bindings}}).errors,[])
    if(filename.includes('/info/'))continue
    assert.match(source,/useCaseReferenceCounts/)
    assert.match(source,/<ApiInfoBoundCases[^>]+reference-mode/)
    assert.match(source,/case_reference_count/)
    assert.doesNotMatch(source,/查看引用Case数|隐藏引用Case数|toggleReferences|referencesVisible/)
    assert.match(source, /<span v-if="record\.status === 1" class="mango-muted-text">不统计默认开启<\/span>/)
  }
})

test('automatic reads wait for the list and skip empty pages',async()=>{
  const calls=[],state=setup(async ids=>{calls.push(ids);return {data:{'9007199254740993':1,'2':0}}},{initialLoading:true})
  await flush();assert.equal(calls.length,0)
  state.listLoading.value=false;await flush();assert.equal(calls.length,1)
  state.rows.value=[];await flush();assert.equal(calls.length,1);assert.deepEqual(state.counts.value,{})
  state.close()
})

test('cached pages pause automatic reads while inactive and refresh counts after activation',async()=>{
  const calls=[],state=setup(async ids=>{calls.push(ids);return {data:{'9007199254740993':1,'2':0,'3':5}}})
  await flush();state.activate();await flush();assert.equal(calls.length,1)
  state.deactivate();state.rows.value=[{id:3}];await flush()
  assert.equal(calls.length,1);assert.deepEqual(state.counts.value,{})
  state.activate();await flush()
  assert.equal(calls.length,2);assert.deepEqual(calls[1],[3]);assert.deepEqual(state.counts.value,{'3':5})
  state.close()
})

test('reference drawer paginates, supports UI and ignores responses after closing',async()=>{
  const requests=[],user=Vue.reactive({userId:1,roleId:1,token:'fixture'})
  const state=harness('ApiInfoBoundCases','open,pagination,rows,loading,casePanel,openCase,close',{
    base:path.resolve('src/views/apitest/info'),props:{referenceMode:true,domain:'ui',readCases:(id,page,pageSize)=>{
      const pending=deferred();requests.push({id,page,pageSize,pending});return pending.promise}},
    modules:{'@/store/modules/user':{default:()=>user},'@/hooks/table':loadTableHooks()},
  })
  const first=state.open({id:7,name:'Variable'})
  assert.deepEqual([requests[0].id,requests[0].page,requests[0].pageSize],[7,1,20])
  requests[0].pending.resolve({data:[{case_id:8,case_name:'Example'}],totalSize:21});await first
  state.pagination.page=2;state.pagination.onChange();assert.equal(requests[1].page,2)
  state.exposed.close();requests[1].pending.resolve({data:[{case_id:99}]});await flush()
  assert.deepEqual(state.rows.value,[]);assert.equal(state.loading.value,false)
  state.close()
})

test('reference page size is sent to the server and reopening restores the default pagination',async()=>{
  const requests=[]
  const state=harness('ApiInfoBoundCases','open,pagination,rows,loading,close',{
    base:path.resolve('src/views/apitest/info'),props:{referenceMode:true,readCases:async(id,page,pageSize)=>{
      requests.push({id,page,pageSize});return {data:[{case_id:page,case_name:'Example'}],totalSize:57}}},
    modules:{'@/store/modules/user':{default:()=>({})},'@/hooks/table':loadTableHooks()},
  })
  await state.open({id:7,name:'Variable'})
  state.pagination.page=1;state.pagination.pageSize=50;await state.pagination.onChange()
  assert.deepEqual(requests[1],{id:7,page:1,pageSize:50})
  assert.equal(state.pagination.pageCount,57)
  state.exposed.close();await state.open({id:8,name:'Next'})
  assert.deepEqual(requests[2],{id:8,page:1,pageSize:20})
  state.close()
})

test('unpaginated bound cases use local pages without refetching the same snapshot',async()=>{
  let reads=0
  const all=Array.from({length:45},(_,index)=>({case_id:index+1,case_name:'Example'}))
  const state=harness('ApiInfoBoundCases','open,pagination,rows,loading',{
    base:path.resolve('src/views/apitest/info'),api:{getApiInfoBoundCases:async()=>{reads++;return {data:all}}},
    modules:{'@/store/modules/user':{default:()=>({})},'@/hooks/table':loadTableHooks()},
  })
  await state.open({id:7,name:'API'})
  assert.equal(state.rows.value.length,20);assert.equal(state.pagination.pageCount,45)
  state.pagination.page=3;await state.pagination.onChange()
  assert.equal(state.rows.value.length,5);assert.equal(state.rows.value[0].case_id,41)
  state.pagination.page=1;state.pagination.pageSize=50;await state.pagination.onChange()
  assert.equal(state.rows.value.length,45);assert.equal(reads,1);assert.equal(state.loading.value,false)
  state.close()
})
