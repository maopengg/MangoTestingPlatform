import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { computed, reactive, ref } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/apitest/headers')
const row = (id=1) => ({id,key:'X-Example',value:'example-value',status:0,project_product:{id:2,name:'Example product',api_client_type:0}})
const columns = {useTableIndexColumn:()=>({key:'index'}),useTableColumn:items=>items}
function editor(api={}) {
  return harness('HeaderEditor','open,save,visible,saving,editingId,draft,formItems',{base,api,modules:{'@/hooks/table':columns}})
}
function loadPure(file) {
  const result={}
  new Function('exports',ts.transpileModule(readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText)(result)
  return result
}
function page(api={},options={}) {
  const confirmations=[]
  const selection=ref([])
  const table={dataList:reactive([]),tableLoading:ref(false),handleSuccess:response=>table.dataList.splice(0,table.dataList.length,...response.data)}
  const pagination=reactive({page:1,pageSize:20,pageCount:0,setTotalSize(total){this.pageCount=total}})
  const state=harness('index','doRefresh,onSearchRefresh,onResetSearch,onDelete,onModifyStatus,loadUsers,deactivate,conditionItems,projectProductCondition,sidebarResetKey,statusUpdatingIds,deletingIds,userOptions,userOptionsLoading,pageActive,navigationCreateRef,editorRef,onAdd',{base,api,
    Modal:{confirm:config=>{const handle={config,closed:false,close(){handle.closed=true;config.onClose?.()}};confirmations.push(handle);return handle}},
    modules:{
      '@/hooks/table':{...columns,useTable:()=>table,usePagination:()=>pagination,useRowKey:()=> 'id'},
      '@/hooks/use-latest-request':loadPure('src/hooks/use-latest-request.ts'),
      '@/hooks/use-project-locked-row-selection':{useProjectLockedRowSelection:()=>({selectedRowKeys:selection,showCheckedAll:ref(true),selectableDataList:computed(()=>table.dataList),onSelectionChange:()=>{},validateSingleProject:()=> options.validProduct !== false})},
    },
  })
  return {...state,selection,table,pagination,confirmations}
}

test('headers entry, editor and shared search component compile',()=>{
  for (const file of [path.join(base,'index.vue'),path.join(base,'components/HeaderEditor.vue'),path.resolve('src/components/business/ApiResourceSearchFilters.vue')]) {
    const {descriptor,errors}=parse(readFileSync(file,'utf8'))
    assert.deepEqual(errors,[])
    const script=compileScript(descriptor,{id:file})
    assert.deepEqual(compileTemplate({filename:file,source:descriptor.template.content,id:file,compilerOptions:{bindingMetadata:script.bindings}}).errors,[])
  }
})

test('search factories isolate client and updater collections including enum zero',()=>{
  const state=editor(),{createConditionItems}=state.load('config.ts')
  const first=createConditionItems(),second=createConditionItems()
  for(const key of ['project_product__api_client_type','update_user']) {
    const item=first.find(i=>i.key===key)
    assert.equal(item.multiple,true)
    item.value=[0,1]
    assert.deepEqual(second.find(i=>i.key===key).value,[])
    const {getFormItems}=state.load('../../../utils/datacleaning.ts')
    assert.equal(getFormItems(first)[key+'__in'],'0,1')
    item.reset();assert.deepEqual(item.value,[])
  }
  state.close()
})

test('editor cancel isolates the list record and new drafts reset prior ID and values',()=>{
  const state=editor(),source=row()
  state.open(source);state.draft.key='changed';state.draft.value='changed'
  state.exposed.close()
  assert.equal(source.key,'X-Example');assert.equal(source.value,'example-value')
  state.open(undefined,8)
  assert.equal(state.editingId.value,null);assert.equal(state.draft.project_product,8)
  assert.equal(state.draft.key,'');assert.equal(state.draft.value,'')
  state.close()
})

test('editor validates before writing and creates only whitelisted fields with the product leaf',async()=>{
  const writes=[],state=editor({postApiHeaders:async value=>{writes.push(value);return {msg:'ok'}}})
  state.open();assert.equal(await state.save(),false);assert.deepEqual(writes,[])
  Object.assign(state.draft,{project_product:[],key:'X-Example',value:'value'})
  assert.equal(await state.save(),false);assert.deepEqual(writes,[])
  Object.assign(state.draft,{project_product:[8,9],key:'X-Example',value:'value'})
  assert.equal(await state.save(),true)
  assert.deepEqual(writes,[{project_product:9,key:'X-Example',value:'value'}])
  assert.equal(state.visible.value,false);assert.deepEqual(state.events,[['saved']])
  state.close()
})

test('metadata-only edit freezes values, blocks duplicate submission and keeps failed draft',async()=>{
  const pending=deferred(),writes=[]
  const state=editor({putApiHeaders:value=>{writes.push(value);return pending.promise}})
  state.open({...row(),update_user:{id:4,name:'Example'}})
  const saving=state.save();assert.equal(state.saving.value,true)
  assert.equal(await state.save(),false)
  state.draft.value='retry value'
  assert.deepEqual(writes,[{id:1,project_product:2,key:'X-Example',value:'example-value'}])
  pending.reject(Error('offline'));assert.equal(await saving,false)
  assert.equal(state.visible.value,true);assert.equal(state.saving.value,false)
  assert.equal(state.draft.value,'retry value')
  state.close()
})

test('closing the editor invalidates a pending successful write',async()=>{
  const pending=deferred(),state=editor({putApiHeaders:()=>pending.promise})
  state.open(row());const saving=state.save();state.exposed.close()
  pending.resolve({msg:'ok'});assert.equal(await saving,false)
  assert.deepEqual(state.events,[])
  state.open(row(2));assert.equal(state.editingId.value,2)
  state.close()
})

test('list queries strip empty fields, resolve product leaves and retain collection zero',async()=>{
  const queries=[],state=page({getApiHeaders:async query=>{queries.push(query);return {data:[],totalSize:0}}})
  state.projectProductCondition.value.value=[8,9]
  state.conditionItems.find(i=>i.key==='project_product__api_client_type').value=[0,1]
  state.pagination.page=3
  await state.doRefresh()
  assert.deepEqual(queries,[{project_product:9,project_product__api_client_type__in:'0,1',page:3,pageSize:20}])
  state.selection.value=[1];state.onResetSearch();await flush()
  assert.equal(state.pagination.page,1);assert.deepEqual(state.selection.value,[])
  assert.deepEqual(queries[1],{page:1,pageSize:20});assert.equal(state.sidebarResetKey.value,1)
  state.close()
})

test('late list responses cannot replace current data and failures release loading without losing rows',async()=>{
  const requests=[],state=page({getApiHeaders:()=>{const pending=deferred();requests.push(pending);return pending.promise}})
  const old=state.doRefresh(),current=state.doRefresh()
  requests[1].resolve({data:[row(2)],totalSize:1});await current
  requests[0].resolve({data:[row(1)],totalSize:1});await old
  assert.equal(state.table.dataList[0].id,2)
  const failed=state.doRefresh();requests[2].reject(Error('offline'));await failed
  assert.equal(state.table.dataList[0].id,2);assert.equal(state.table.tableLoading.value,false)
  state.close()
})

test('deactivation ignores list and option responses and closes owned windows',async()=>{
  const list=deferred(),users=deferred(),state=page({getApiHeaders:()=>list.promise,getUserName:()=>users.promise})
  let closes=0;state.editorRef.value={close(){closes++}}
  const reading=state.doRefresh(),options=state.loadUsers()
  state.onDelete(row());state.deactivate()
  list.resolve({data:[row()],totalSize:1});users.resolve({data:[{key:1,title:'Old'}]})
  await Promise.all([reading,options])
  assert.deepEqual(state.table.dataList,[]);assert.deepEqual(state.userOptions.value,[])
  assert.equal(state.table.tableLoading.value,false);assert.equal(state.userOptionsLoading.value,false)
  assert.equal(closes,1);assert.equal(state.confirmations[0].closed,true)
  state.close()
})

test('deletion freezes IDs at confirmation and failure retains selection for retry',async()=>{
  const pending=deferred(),writes=[],state=page({deleteApiHeaders:ids=>{writes.push(ids);return pending.promise}})
  state.selection.value=['1','2'];state.onDelete(null);state.onDelete(null)
  assert.equal(state.confirmations.length,1)
  state.selection.value=['3']
  const deleting=state.confirmations[0].config.onBeforeOk()
  assert.equal(await state.confirmations[0].config.onBeforeOk(),false)
  assert.equal(state.deletingIds.size,2)
  pending.reject(Error('offline'));assert.equal(await deleting,false)
  assert.deepEqual(writes,[['1','2']]);assert.deepEqual(state.selection.value,['3'])
  assert.equal(state.deletingIds.size,0)
  state.close()
})

test('successful deletion removes only its original selection and refreshes current records',async()=>{
  const writes=[],state=page({deleteApiHeaders:async ids=>{writes.push(ids);return {msg:'ok'}},getApiHeaders:async()=>({data:[row(3)],totalSize:1})})
  state.selection.value=['1'];state.onDelete(null);state.selection.value=['1','3']
  assert.equal(await state.confirmations[0].config.onBeforeOk(),true)
  assert.deepEqual(writes,[['1']]);assert.deepEqual(state.selection.value,['3'])
  state.close()
})

test('invalid mixed-product batches never open deletion confirmation',()=>{
  const state=page({}, {validProduct:false})
  state.selection.value=['1','2'];state.onDelete(null)
  assert.equal(state.confirmations.length,0)
  state.close()
})

test('status switch waits for success, blocks duplicates and retains original state after failure',async()=>{
  const requests=[],state=page({putApiHeaders:payload=>{const pending=deferred();requests.push({pending,payload});return pending.promise}})
  state.table.dataList.push(row())
  const update=state.onModifyStatus(true,1)
  assert.equal(state.table.dataList[0].status,0);assert.equal(state.statusUpdatingIds.has(1),true)
  assert.equal(await state.onModifyStatus(true,1),false)
  requests[0].pending.reject(Error('offline'));assert.equal(await update,false)
  assert.equal(state.table.dataList[0].status,0);assert.equal(state.statusUpdatingIds.size,0)
  const retry=state.onModifyStatus(true,1);requests[1].pending.resolve({code:200,msg:'ok'})
  assert.equal(await retry,true);assert.equal(state.table.dataList[0].status,1)
  assert.deepEqual(requests[1].payload,{id:1,status:1})
  state.close()
})

test('status completion cannot change a row after leaving the page',async()=>{
  const pending=deferred(),state=page({putApiHeaders:()=>pending.promise})
  state.table.dataList.push(row());const updating=state.onModifyStatus(true,1)
  state.deactivate();pending.resolve({code:200,msg:'ok'})
  assert.equal(await updating,false);assert.equal(state.table.dataList[0].status,0)
  assert.equal(state.statusUpdatingIds.size,0)
  state.close()
})

test('new header inherits the active navigation product',()=>{
  const state=page(),opened=[]
  state.navigationCreateRef.value={getCreateDefaults:()=>({projectProduct:7,module:null})}
  state.editorRef.value={open:(...args)=>opened.push(args),close(){}}
  state.onAdd();assert.deepEqual(opened,[[undefined,7]])
  state.close()
})
