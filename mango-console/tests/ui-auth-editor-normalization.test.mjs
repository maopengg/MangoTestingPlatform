import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse,compileScript,compileTemplate,compileStyleAsync } from '@vue/compiler-sfc'
import { deferred,flush,method } from './helpers/case-details-harness.mjs'
import { setupUiAuthEditor,uiAuthRecord,readyUiAuth,uiAuthBase } from './helpers/ui-auth-editor-harness.mjs'

test('finite drafts clone only editable fields, preserve leaf/zero/long IDs and isolate JSON documents', t=>{
  const h=setupUiAuthEditor();t.after(h.close);const dto=h.load('auth-editor-records.ts'),source=uiAuthRecord(),draft=dto.readUiAuthDraft(source),json=dto.readUiAuthJsonDraft(source)
  assert.equal(draft.project_product,0);assert.equal(draft.api_info,0);assert.equal(draft.page_step,0);assert.equal(draft.time_task,0);assert.equal(draft.notice_group,0);assert.equal('cache_data' in draft,false);assert.equal('update_time' in draft,false)
  json.manual='{}';draft.name='Changed';assert.equal(source.manual_config.headers.example,'value');assert.equal(source.name,'Example auth')
  assert.equal(dto.uiAuthId([1,'90071992547409930000']),'90071992547409930000');assert.equal(dto.uiAuthId(null),null);assert.throws(()=>dto.uiAuthId(false));assert.throws(()=>dto.uiAuthId('bad'))
  const first=dto.createUiAuthDraft(),second=dto.createUiAuthDraft();first.name='Changed';assert.equal(second.name,'');assert.equal(second.test_env,null)
})
test('payload is a fixed whitelist and keeps conditional page/timing/notice/API contracts including zero', t=>{
  const h=setupUiAuthEditor();t.after(h.close);const dto=h.load('auth-editor-records.ts'),source=uiAuthRecord(),draft=dto.readUiAuthDraft(source),json=dto.readUiAuthJsonDraft(source)
  const edited=dto.uiAuthPayload(draft,json,0);assert.equal(edited.id,0);assert.equal(edited.test_env,0);assert.equal(edited.project_product,0);assert.equal(edited.page_step,null);assert.equal(edited.notice_group,null);assert.equal(edited.api_config.api_info,0)
  assert.equal('cache_data' in edited,false);assert.equal('last_refresh_status' in edited,false);source.manual_config.headers.example='Changed';assert.equal(edited.manual_config.headers.example,'value')
  for(const [auth_type,refresh_mode,page_step,time_task,notice_group] of [[3,2,0,null,null],[2,1,null,0,null],[2,2,null,null,0],[1,2,null,null,0]]) {
    const payload=dto.uiAuthPayload({...draft,auth_type,refresh_mode},json,null);assert.equal('id' in payload,false);assert.equal(payload.page_step,page_step);assert.equal(payload.time_task,time_task);assert.equal(payload.notice_group,notice_group);assert.equal(payload.refresh_mode,auth_type===3?0:refresh_mode)
  }
})
test('JSON parser accepts object documents and leaves nested config semantics to backend validation', t=>{
  const h=setupUiAuthEditor();t.after(h.close);const dto=h.load('auth-editor-records.ts')
  for(const text of ['[]','null','true','"text"','{'])assert.throws(()=>dto.parseUiAuthJson(text))
  assert.deepEqual(dto.parseUiAuthJson('{"cookies":[],"storage_state":{"origins":[]}}'),{cookies:[],storage_state:{origins:[]}})
})
test('draft validation keeps environment zero, supported modes, required relationships and reminder limits', t=>{
  const h=setupUiAuthEditor();t.after(h.close);const dto=h.load('auth-editor-records.ts'),base=dto.readUiAuthDraft(uiAuthRecord())
  assert.equal(dto.validateUiAuthDraft(base),'')
  for(const [patch,message] of [[{project_product:null},'产品'],[{test_env:null},'被测环境'],[{name:' '},'名称'],[{auth_type:4},'暂未开放'],[{auth_type:3,page_step:null},'页面步骤'],[{auth_type:1,refresh_mode:1},'定时刷新'],[{auth_type:2,refresh_mode:1,time_task:null},'定时策略'],[{refresh_mode:2,notice_group:null},'通知组'],[{token_ttl:0},'有效期'],[{refresh_mode:2,expire_notice_minutes:9},'提醒'],[{refresh_mode:2,expire_notice_minutes:1440},'提醒']])assert.match(dto.validateUiAuthDraft({...base,...patch}),new RegExp(message))
})
test('create preserves navigation product zero while requiring an explicit environment, with clean cancel and reopen', async t=>{
  const h=setupUiAuthEditor();t.after(h.close);await h.openCreate([2,0]);assert.equal(h.form.project_product,0);assert.equal(h.form.test_env,null);assert.equal(h.editorVisible.value,true)
  h.form.name='Draft';h.json.manual='{"cookies":[]}';h.closeEditor();assert.equal(h.form.project_product,null);await h.openCreate(2);assert.equal(h.form.name,'');assert.equal(h.json.manual,h.load('auth-editor-records.ts').createUiAuthJsonDraft().manual)
  assert.equal(h.reads.filter(x=>x[0]==='getUiSteps')[0][1].project_product,0)
})
test('edit zero preserves relation labels and copies config text without mutating the source record', async t=>{
  const source=uiAuthRecord(),h=setupUiAuthEditor();t.after(h.close);await h.openEdit(source)
  assert.equal(h.editingId.value,0);assert.equal(h.pageStepOptions.value[0].title,'Login steps');assert.equal(h.timeTaskOptions.value[0].title,'Daily');assert.equal(h.noticeOptions.value[0].title,'Current notice');assert.equal(h.apiInfoOptions.value[0].title,'Login API / /login')
  h.form.name='Draft';h.json.auto='{}';assert.equal(source.name,'Example auth');assert.equal(source.auto_auth_config.url,'https://example.com')
})
test('metadata loading/error/retry is independent across options and enums', async t=>{
  const pages=deferred(),enums=deferred();let fail=true
  const h=setupUiAuthEditor({getUiSteps:()=>pages.promise,getEnum:()=>enums.promise,getSystemNoticeName:async()=>({code:fail?403:200,data:[{key:0,title:'Recovered'}]})});t.after(h.close)
  const opening=h.openCreate(0);await flush();assert.equal(h.pages.loading.value,true);assert.equal(h.enumsLoading.value,true);assert.equal(h.apis.loading.value,false);assert.equal(h.timings.loading.value,false);assert.match(h.notices.error.value,/失败/)
  fail=false;await h.loadNoticeList();assert.equal(h.noticeOptions.value[0].title,'Recovered');assert.equal(h.pages.loading.value,true)
  pages.resolve({code:200,data:[]});enums.reject(Error('network'));await opening;assert.equal(h.pages.loading.value,false);assert.match(h.enumsError.value,/失败/)
  h.enumStore.getEnum=async()=>{};await h.loadEnums();assert.equal(h.enumsError.value,'')
})
test('product changes clear dependent relations and ignore old option results without clearing newer loading', async t=>{
  const old=deferred(),current=deferred(),h=setupUiAuthEditor({getUiSteps:query=>query.project_product===1?old.promise:query.project_product===2?current.promise:Promise.resolve({code:200,data:[]})});t.after(h.close);await readyUiAuth(h)
  const first=h.onFormProjectProductChange(1),second=h.onFormProjectProductChange(2);assert.equal(h.form.page_step,null);assert.equal(h.form.api_info,null);assert.equal(h.form.notice_group,null)
  old.resolve({code:200,data:[{id:1,name:'Old'}]});await first;assert.equal(h.pages.loading.value,true);assert.deepEqual(h.pageStepOptions.value,[])
  current.resolve({code:200,data:[{id:2,name:'Current'}]});await second;assert.equal(h.pageStepOptions.value[0].title,'Current');assert.equal(h.pages.loading.value,false)
})
test('cancelled edit option reads cannot overwrite a new create session', async t=>{
  const pending=deferred();let calls=0
  const h=setupUiAuthEditor({getUiSteps:()=>++calls===1?pending.promise:Promise.resolve({code:200,data:[{id:2,name:'New'}]})});t.after(h.close)
  const old=h.openEdit(uiAuthRecord());await flush();h.closeEditor();await h.openCreate(2);h.form.name='New draft'
  pending.resolve({code:200,data:[{id:0,name:'Old'}]});await old;assert.equal(h.editingId.value,null);assert.equal(h.form.name,'New draft');assert.equal(h.pageStepOptions.value[0].title,'New')
})
test('auth type and refresh changes preserve four supported modes and clear only incompatible relationships', async t=>{
  const h=setupUiAuthEditor();t.after(h.close);await readyUiAuth(h)
  h.form.auth_type=2;h.form.refresh_mode=1;h.onAuthTypeChange();assert.equal(h.form.time_task,0);assert.equal(h.refreshModeOptions.value.length,3)
  h.form.auth_type=1;h.onAuthTypeChange();assert.equal(h.form.refresh_mode,0);assert.equal(h.form.time_task,null);assert.equal(h.refreshModeOptions.value.some(x=>x.key===1),false)
  h.form.auth_type=3;h.form.notice_group=0;h.onAuthTypeChange();assert.equal(h.form.notice_group,null);assert.equal(h.form.refresh_mode,0);assert.equal(h.enabledAuthTypeOptions.value.some(x=>x.key===4),false)
  h.form.refresh_mode=0;h.form.time_task=0;h.form.notice_group=0;h.onRefreshModeChange();assert.equal(h.form.time_task,null);assert.equal(h.form.notice_group,null)
})
test('JSON drawer keeps cancel isolated, rejects nonobjects and applies valid text only on explicit save', async t=>{
  const h=setupUiAuthEditor();t.after(h.close);await readyUiAuth(h);const original=h.json.manual
  h.openJson('manual');assert.equal(h.jsonText.value,original);assert.equal(h.locked.value,true);assert.equal(await h.onSubmit(),false)
  h.jsonVisible.value=false;assert.equal(h.json.manual,original);h.openJson('auto');h.saveJson('[]');assert.equal(h.jsonVisible.value,true);assert.match(h.messages.at(-1)[1],/JSON/)
  h.saveJson('{"timeout":120}');assert.equal(h.json.auto,'{"timeout":120}');assert.equal(h.jsonVisible.value,false);assert.equal(h.json.manual,original)
  h.openJson('api');h.closeEditor();h.saveJson('{"api_info":2}');assert.equal(h.json.api,h.load('auth-editor-records.ts').createUiAuthJsonDraft().api)
})
test('save freezes IDs/JSON before asynchronous form validation and duplicate submissions remain blocked', async t=>{
  const validation=deferred(),pending=deferred(),h=setupUiAuthEditor({putUiAuthConfig:()=>pending.promise});t.after(h.close);await readyUiAuth(h)
  h.formRef.value={validate:()=>validation.promise,clearValidate(){}};const saving=h.onSubmit();assert.equal(h.saving.value,true);assert.equal(await h.onSubmit(),false)
  h.form.name='Changed behind disabled form';h.json.manual='{}';validation.resolve(undefined);await flush();assert.equal(h.writes.length,1);assert.equal(h.writes[0][0],'putUiAuthConfig');assert.equal(h.writes[0][1].id,0);assert.equal(h.writes[0][1].name,'Example auth');assert.equal(h.writes[0][1].manual_config.headers.example,'value')
  pending.resolve({code:200});assert.equal(await saving,true);assert.equal(h.editorVisible.value,false);assert.deepEqual(h.events,[['saved']])
})
test('create saves through POST with product/environment/API zero and no audit fields or creation ID', async t=>{
  const h=setupUiAuthEditor();t.after(h.close);await h.openCreate(0);h.form.name='New';h.form.test_env=0;h.form.auth_type=2;h.form.api_info=0
  assert.equal(await h.onSubmit(),true);const payload=h.writes[0][1];assert.equal(h.writes[0][0],'postUiAuthConfig');assert.equal('id' in payload,false);assert.equal(payload.project_product,0);assert.equal(payload.test_env,0);assert.equal(payload.api_config.api_info,0);assert.equal('cache_data' in payload,false)
})
test('local validation, JSON errors and form validation failures do not submit and release the save lock', async t=>{
  const h=setupUiAuthEditor();t.after(h.close);await h.openCreate(0);assert.equal(await h.onSubmit(),false);assert.match(h.saveError.value,/被测环境/)
  await readyUiAuth(h);h.json.manual='[]';assert.equal(await h.onSubmit(),false);assert.match(h.saveError.value,/JSON/);h.json.manual='{}';h.formRef.value={validate:async()=>({test_env:'invalid'}),clearValidate(){}};assert.equal(await h.onSubmit(),false);assert.equal(h.saving.value,false);assert.equal(h.writes.length,0)
})
test('cancel while form validation is pending prevents the later write and guards reopen until validation settles', async t=>{
  const validation=deferred(),h=setupUiAuthEditor();t.after(h.close);await readyUiAuth(h);h.formRef.value={validate:()=>validation.promise,clearValidate(){}}
  const saving=h.onSubmit();h.closeEditor();await h.openCreate(2);assert.equal(h.editorVisible.value,false);validation.resolve(undefined);assert.equal(await saving,false);assert.equal(h.writes.length,0);assert.equal(h.saving.value,false)
})
test('network/business save failures retain the draft and permit retry without premature success', async t=>{
  let attempt=0;const h=setupUiAuthEditor({putUiAuthConfig:async()=>{if(++attempt===1)throw Error('network');return {code:attempt===2?403:200}}});t.after(h.close);await readyUiAuth(h)
  for(let i=0;i<2;i++){assert.equal(await h.onSubmit(),false);assert.equal(h.editorVisible.value,true);assert.equal(h.form.name,'Example auth');assert.equal(h.saving.value,false);assert.match(h.saveError.value,/失败/);assert.deepEqual(h.events,[])}
  assert.equal(await h.onSubmit(),true);assert.equal(h.writes.length,3)
})
test('cancel during actual save retains its physical lock and only refreshes parent on valid same-identity settlement', async t=>{
  const pending=deferred(),h=setupUiAuthEditor({putUiAuthConfig:()=>pending.promise});t.after(h.close);await readyUiAuth(h)
  const saving=h.onSubmit();await flush();h.closeEditor();await h.openEdit(uiAuthRecord({id:2}));assert.equal(h.editorVisible.value,false);assert.equal(h.saving.value,true)
  pending.resolve({code:200});await saving;assert.equal(h.editorVisible.value,false);assert.deepEqual(h.messages,[]);assert.deepEqual(h.events,[['saved']]);assert.equal(h.saving.value,false)
})
test('every identity dimension closes the window and suppresses stale write feedback and parent events', async()=>{
  for(const change of [h=>h.user.userId++,h=>h.user.roleId++,h=>h.user.token='example-new',h=>h.user.selected_environment++,h=>h.permission.permissionKeys.push('example:read'),h=>h.route.path='/other',h=>h.route.fullPath+='?id=2']) {
    const pending=deferred(),h=setupUiAuthEditor({putUiAuthConfig:()=>pending.promise})
    try{await readyUiAuth(h);const saving=h.onSubmit();await flush();change(h);assert.equal(h.editorVisible.value,false);assert.equal(h.form.name,'');pending.resolve({code:200});await saving;assert.deepEqual(h.events,[]);assert.deepEqual(h.messages,[])}finally{h.close()}
  }
})
test('background, KeepAlive and unmount invalidate option reads and do not reopen cancelled windows', async()=>{
  for(const mode of ['background','deactivate','unmount']) {
    const pending=deferred(),h=setupUiAuthEditor({getUiSteps:()=>pending.promise})
    try{h.mount();const opening=h.openEdit(uiAuthRecord());await flush();if(mode==='background')h.visibility('hidden');else h.callbacks[mode].forEach(fn=>fn());pending.resolve({code:200,data:[{id:0,name:'Late'}]});await opening;assert.equal(h.editorVisible.value,false);assert.equal(h.pages.loading.value,false);assert.deepEqual(h.pageStepOptions.value,[]);await h.openCreate(0);assert.equal(h.editorVisible.value,false)}finally{h.close()}
  }
})
test('write settling after background return refreshes data without reopening the editor or replaying success', async t=>{
  const pending=deferred(),h=setupUiAuthEditor({putUiAuthConfig:()=>pending.promise});t.after(h.close);h.mount();await readyUiAuth(h);const saving=h.onSubmit();await flush();h.visibility('hidden');h.visibility('visible');pending.resolve({code:200});await saving
  assert.equal(h.editorVisible.value,false);assert.deepEqual(h.messages,[]);assert.deepEqual(h.events,[['saved']])
})
test('malformed rows do not open an editable partial record or turn a bad edit into creation', async t=>{
  const h=setupUiAuthEditor();t.after(h.close);await h.openEdit(uiAuthRecord({id:null}));assert.equal(h.editorVisible.value,false);await h.openEdit(uiAuthRecord({manual_config:[]}));assert.equal(h.editorVisible.value,false);assert.equal(h.writes.length,0)
})
test('parent delegates navigation zero and row editing while editor/shared JSON drawer SFC bindings compile', async()=>{
  const parentFile=path.join(uiAuthBase,'index.vue'),parent=readFileSync(parentFile,'utf8'),calls=[],editorRef={value:{openCreate:value=>calls.push(['create',value]),openEdit:value=>calls.push(['edit',value])}},navigationCreateRef={value:{getCreateDefaults:()=>({projectProduct:0,module:null})}}
  method('onAdd',{editorRef,navigationCreateRef},parentFile)();method('onEdit',{editorRef,available:()=>true,busy:()=>false},parentFile)(uiAuthRecord());assert.equal(calls[0][1],0);assert.equal(calls[1][1].id,0)
  assert.match(parent,/<UiAuthEditorDialog ref="editorRef" @saved="refreshAfterEditor"/);assert.doesNotMatch(parent,/const form = reactive|parseJson<|manualConfigText/)
  for(const filename of [parentFile,path.join(uiAuthBase,'components/UiAuthEditorDialog.vue'),path.resolve('src/components/editors/MangoJsonEditDrawer.vue')]) {
    const {descriptor,errors}=parse(readFileSync(filename,'utf8'),{filename});assert.deepEqual(errors,[]);const script=compileScript(descriptor,{id:filename}),template=compileTemplate({source:descriptor.template.content,filename,id:filename,compilerOptions:{bindingMetadata:script.bindings}});assert.deepEqual(template.errors,[])
    assert.deepEqual([...new Set([...template.code.matchAll(/_ctx\.([A-Za-z_$]\w*)/g)].map(match=>match[1]))].filter(key=>!(key in script.bindings)),[])
    for(const style of descriptor.styles)assert.deepEqual((await compileStyleAsync({source:style.content,filename,id:filename,scoped:true})).errors,[])
  }
})
