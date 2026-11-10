import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/system/department')
const ok = (data=[],extra={}) => ({code:200,data,msg:'ok',...extra})
const row = (id=1) => ({id,name:'Example department',status:1,description:'Description'})
function setup(options={}) {
  const life={mount:[],activate:[],deactivate:[],unmount:[]}, calls=[], dialogs=[]
  const route=vue.reactive({path:'/organization-permission/department/index',fullPath:'/organization-permission/department/index'})
  const user=vue.reactive({userId:1,roleId:1,token:'fixture',selected_environment:0}), permission=vue.reactive({permissionKeys:[]})
  const doc=Object.assign(new EventTarget(),{visibilityState:'visible'})
  const api=Object.fromEntries(['getUserDepartment','postUserDepartment','putUserDepartment','deleteUserDepartment','getUserProduct','getUserDepartmentProductScope','putUserDepartmentProductScope'].map(name=>[name,payload=>{
    calls.push([name,payload]); return options[name]?.(payload) ?? Promise.resolve(name==='getUserDepartment'?ok([row()],{totalSize:1}):ok())
  }]))
  const h=harness('index','rows,listLoading,listError,pagination,form,actionTitle,editorId,editorVisible,saving,writeBusy,modalDialogRef,scopeDrawer,onAdd,onUpdate,closeEditor,onDataForm,onStatusChange,onDelete,onScope,loadScope,closeScope,onSaveScope,doRefresh',{
    base,api,modules:{
      vue:{...vue,onMounted:f=>life.mount.push(f),onActivated:f=>life.activate.push(f),onDeactivated:f=>life.deactivate.push(f),onBeforeUnmount:f=>life.unmount.push(f)},
      'vue-router':{useRoute:()=>route},
      '@/store/modules/user':{default:()=>user},'@/store/modules/permission':{default:()=>permission},
      '@/hooks/table':{useTable:()=>({indexColumn:{key:'index',width:100}}),useTableColumn:v=>v,useRowKey:()=> 'id',usePagination:(fn,loading)=>vue.reactive({page:1,pageSize:20,pageCount:0,setTotalSize(n){this.pageCount=n},onChange(){loading.value=true;return fn()}})},
      '@arco-design/web-vue':{Message:{success(){},error(){}},Modal:{confirm(config){const handle={config,closed:false,close(){this.closed=true}};dialogs.push(handle);return handle}}},
    },
  })
  const shell={visible:false,loading:false,show(){this.visible=true},close(){this.visible=false;this.loading=false},setConfirmLoading(v){this.loading=v}}
  h.modalDialogRef.value=shell
  let previous, mounted=false
  return {...h,calls,dialogs,life,route,user,permission,shell,
    mount(){mounted=true;previous=globalThis.document;globalThis.document=doc;life.mount.forEach(f=>f());life.activate.forEach(f=>f())},
    async visibility(value){doc.visibilityState=value;doc.dispatchEvent(new Event('visibilitychange'));await flush()},
    close(){if(mounted){const current=globalThis.document;globalThis.document=doc;life.unmount.forEach(f=>f());globalThis.document=current===doc?previous:current}h.close()},
  }
}
test('finite boundary preserves zero/long IDs; rejects broken scope, status and envelopes',t=>{
  const h=setup();t.after(h.close);const m=h.load('department.ts')
  assert.equal(m.departmentId(0),0);assert.equal(m.departmentId('90071992547409931234'),'90071992547409931234')
  for(const bad of [null,'',false,{},1.5,-1,Number.MAX_SAFE_INTEGER+1]) assert.equal(m.departmentId(bad),null)
  assert.throws(()=>m.parseDepartments(ok([row()],{totalSize:'1'})))
  assert.throws(()=>m.parseDepartments(ok([{...row(),status:null}],{totalSize:1})))
  assert.throws(()=>m.parseDepartmentScope(ok([{project_product:null}])))
  assert.throws(()=>m.departmentSuccess({code:403}))
  assert.deepEqual(m.parseDepartmentScope(ok([{project_product:{id:0}},{project_product:{id:0}}])),[0])
  assert.deepEqual(m.scopeSelection(['1',99],[{id:1,name:'Example',project:null}]),[1,99])
})
test('list newest page wins; failed load clears loading and supports retry; last page clamps',async t=>{
  const first=deferred(),second=deferred();let n=0
  const h=setup({getUserDepartment:()=>++n===1?first.promise:n===2?second.promise:Promise.resolve(ok([row(3)],{totalSize:1}))});t.after(h.close)
  h.mount();h.pagination.page=2;const refresh=h.doRefresh();second.resolve(ok([row(2)],{totalSize:40}));await refresh
  first.resolve(ok([row(1)],{totalSize:20}));await flush();assert.equal(h.rows.value[0].id,2)
  h.pagination.page=8;await h.doRefresh();await flush();assert.equal(h.pagination.page,1);assert.equal(h.rows.value[0].id,3)
  const failing=setup({getUserDepartment:()=>{throw Error('offline')}});t.after(failing.close);failing.mount();await flush()
  assert.equal(failing.listLoading.value,false);assert.match(failing.listError.value,/重试/)
})
test('editor draft isolation, reset, zero ID, whitelist and duplicate guard',async t=>{
  const save=deferred();const h=setup({putUserDepartment:()=>save.promise});t.after(h.close);h.mount();await flush()
  const source=row(0);h.onUpdate(source);h.form.name='Changed';assert.equal(source.name,'Example department')
  const pending=h.onDataForm();await h.onDataForm();assert.equal(h.calls.filter(c=>c[0]==='putUserDepartment').length,1)
  assert.deepEqual(h.calls.find(c=>c[0]==='putUserDepartment')[1],{id:0,name:'Changed',status:1,description:'Description'})
  h.closeEditor();h.onAdd();assert.equal(h.editorVisible.value,false);assert.equal(h.writeBusy.value,true)
  save.resolve(ok());await pending;h.onAdd();assert.equal(h.actionTitle.value,'新增');assert.equal(h.form.name,'')
  await h.onDataForm();assert.equal(h.calls.filter(c=>c[0]==='postUserDepartment').length,0)
})
test('save rejection retains draft, retry succeeds and closes deterministic modal',async t=>{
  let n=0;const h=setup({postUserDepartment:()=>++n===1?Promise.reject({msg:'Rejected'}):Promise.resolve(ok())});t.after(h.close);h.mount();await flush()
  h.onAdd();h.form.name='New';await h.onDataForm();assert.equal(h.editorVisible.value,true);assert.equal(h.form.name,'New');assert.equal(h.saving.value,false)
  await h.onDataForm();assert.equal(h.editorVisible.value,false);assert.equal(h.shell.visible,false)
})
test('controlled status only changes after success; error recovers',async t=>{
  const request=deferred();const h=setup({putUserDepartment:()=>request.promise});t.after(h.close);h.mount();await flush()
  const target=h.rows.value[0];const pending=h.onStatusChange(target,false);assert.equal(target.status,1)
  assert.equal(await h.onStatusChange(target,false),false);request.resolve(ok());assert.equal(await pending,true);assert.equal(target.status,0)
})
test('delete confirmation Promise closes on success and can retry after failure',async t=>{
  let n=0;const request=deferred();const h=setup({deleteUserDepartment:()=>++n===1?Promise.reject({msg:'blocked'}):request.promise});t.after(h.close);h.mount();await flush()
  h.onDelete(row(0));const dialog=h.dialogs[0];assert.equal(await dialog.config.onBeforeOk(),false)
  const pending=dialog.config.onBeforeOk();assert.equal(await dialog.config.onBeforeOk(),false)
  assert.equal(h.calls.filter(c=>c[0]==='deleteUserDepartment').length,2)
  request.resolve(ok());assert.equal(await pending,true)
  h.onDelete(row(2));assert.equal(h.dialogs.length,2)
})
test('scope target replacement ignores late load; failed read prevents clearing and allows retry',async t=>{
  const a=deferred(),b=deferred();const h=setup({getUserDepartmentProductScope:id=>id===1?a.promise:b.promise,getUserProduct:()=>Promise.resolve(ok([{id:0,name:'Product',project:{name:'Project'}}]))});t.after(h.close);h.mount();await flush()
  h.onScope(row(1));h.onScope(row(2));b.resolve(ok([{project_product:{id:0}}]));await flush()
  a.resolve(ok([{project_product:{id:9}}]));await flush();assert.deepEqual(h.scopeDrawer.selectedProductIds,[0]);assert.equal(h.scopeDrawer.departmentId,2)
  h.scopeDrawer.ready=false;await h.onSaveScope();assert.equal(h.calls.filter(c=>c[0]==='putUserDepartmentProductScope').length,0)
})
test('scope submit snapshots selection; cancel retains physical busy and old result cannot close next window',async t=>{
  const save=deferred();const h=setup({putUserDepartmentProductScope:()=>save.promise});t.after(h.close);h.mount();await flush()
  h.onScope(row(0));await flush();h.scopeDrawer.selectedProductIds=[0];const pending=h.onSaveScope();h.scopeDrawer.selectedProductIds.push(2)
  assert.deepEqual(h.calls.find(c=>c[0]==='putUserDepartmentProductScope')[1],{department_id:0,project_product_ids:[0]})
  h.closeScope();h.onScope(row(3));assert.equal(h.scopeDrawer.visible,false);save.resolve(ok());await pending;h.onScope(row(3));await flush();assert.equal(h.scopeDrawer.departmentId,3)
})
test('scope read failure blocks writes; retry restores bindings; failed save retains selection',async t=>{
  let reads=0,saves=0
  const h=setup({getUserDepartmentProductScope:()=>++reads===1?Promise.reject(Error('offline')):Promise.resolve(ok([{project_product:{id:9}}])),putUserDepartmentProductScope:()=>++saves===1?Promise.reject({msg:'Denied'}):Promise.resolve(ok())})
  t.after(h.close);h.mount();await flush();h.onScope(row());await flush()
  assert.equal(h.scopeDrawer.ready,false);assert.equal(h.scopeDrawer.loading,false);assert.match(h.scopeDrawer.error,/重试/)
  await h.onSaveScope();assert.equal(saves,0);await h.loadScope();assert.deepEqual(h.scopeDrawer.selectedProductIds,[9])
  await h.onSaveScope();assert.equal(h.scopeDrawer.visible,true);assert.equal(h.scopeDrawer.saving,false);assert.deepEqual(h.scopeDrawer.selectedProductIds,[9])
  await h.onSaveScope();assert.equal(h.scopeDrawer.visible,false)
})
test('status rejection recovers and old identity response never changes new rows',async t=>{
  let n=0;const pending=deferred()
  const h=setup({putUserDepartment:()=>++n===1?Promise.reject({msg:'Denied'}):pending.promise})
  t.after(h.close);h.mount();await flush();const target=h.rows.value[0]
  assert.equal(await h.onStatusChange(target,false),false);assert.equal(target.status,1);assert.equal(h.writeBusy.value,false)
  const result=h.onStatusChange(target,false);h.user.selected_environment=2;await flush();assert.equal(h.writeBusy.value,true)
  pending.resolve(ok());assert.equal(await result,false);assert.equal(h.rows.value[0].status,1);assert.equal(h.writeBusy.value,false)
})
test('changing to editor invalidates a retained delete callback',async t=>{
  const h=setup();t.after(h.close);h.mount();await flush();h.onDelete(row());const dialog=h.dialogs[0]
  h.onAdd();assert.equal(dialog.closed,true);assert.equal(await dialog.config.onBeforeOk(),false)
  assert.equal(h.calls.filter(c=>c[0]==='deleteUserDepartment').length,0)
})
test('permission rejection does not create a frontend permission precheck',async t=>{
  const h=setup({postUserDepartment:()=>Promise.reject({code:403,msg:'Denied'})});t.after(h.close);h.mount();await flush()
  h.permission.permissionKeys=[];h.onAdd();h.form.name='Example';await h.onDataForm()
  assert.equal(h.calls.filter(c=>c[0]==='postUserDepartment').length,1);assert.equal(h.editorVisible.value,true);assert.equal(h.saving.value,false)
})
test('identity, background, KeepAlive and route transitions invalidate reads and confirmation',async t=>{
  const pending=deferred();let n=0;const h=setup({getUserDepartment:()=>++n===1?pending.promise:Promise.resolve(ok([row(2)],{totalSize:1}))});t.after(h.close)
  h.mount();h.onDelete(row());const dialog=h.dialogs[0];h.user.roleId=2;await flush();assert.equal(dialog.closed,true)
  assert.equal(await dialog.config.onBeforeOk(),false);assert.equal(h.calls.filter(c=>c[0]==='deleteUserDepartment').length,0)
  pending.resolve(ok([row(99)],{totalSize:1}));await flush();assert.equal(h.rows.value[0].id,2)
  h.onAdd();await h.visibility('hidden');assert.equal(h.editorVisible.value,false)
  const count=h.calls.length;await h.doRefresh();assert.equal(h.calls.length,count);await h.visibility('visible');assert.ok(h.calls.length>count)
  h.life.deactivate.forEach(f=>f());const before=h.calls.length;await h.doRefresh();assert.equal(h.calls.length,before);h.life.activate.forEach(f=>f());await flush();assert.ok(h.calls.length>before)
  h.route.path='/other';h.route.fullPath='/other';await flush();const away=h.calls.length;await h.doRefresh();assert.equal(h.calls.length,away)
})
test('department page and public modal compile with actual templates/styles',async()=>{
  for(const filename of [path.join(base,'index.vue'),path.resolve('src/components/overlays/ModalDialog.vue')]){
    const {descriptor,errors}=parse(readFileSync(filename,'utf8'),{filename});assert.deepEqual(errors,[])
    if(descriptor.scriptSetup)compileScript(descriptor,{id:filename})
    const template=compileTemplate({id:filename,filename,source:descriptor.template.content,compilerOptions:{expressionPlugins:['typescript']}});assert.deepEqual(template.errors,[])
    for(const style of descriptor.styles){const result=await compileStyleAsync({id:filename,filename,source:style.content,scoped:style.scoped});assert.deepEqual(result.errors,[])}
  }
})
