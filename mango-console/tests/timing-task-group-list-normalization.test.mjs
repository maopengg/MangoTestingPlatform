import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { setupGroupList, groupRow, groupRecent, groupListResponse, groupListDetail, groupFilters, groupListBase } from './helpers/timing-task-group-list-harness.mjs'

test('group list DTOs isolate finite rows, preserve zero/long IDs and reject malformed counts/results', t => {
  const h=setupGroupList();t.after(h.close);const dto=h.load('task-group-list-records.ts'),source=groupRow({ extra:'omit' })
  const parsed=dto.readTaskGroupList(groupListResponse([source])).rows[0];assert.equal(parsed.id,0);assert.equal(parsed.recent_results[0].group_execution_id,0);assert.equal('extra' in parsed,false)
  parsed.test_envs.push(2);parsed.project_product.name='Draft';assert.deepEqual(source.test_envs,[0]);assert.equal(source.project_product.name,'Product')
  const id='90071992547409930000';assert.equal(dto.readTaskGroupRecord(groupRow({id,recent_results:[groupRecent({group_execution_id:id})]})).recent_results[0].group_execution_id,id)
  for(const response of [{code:403,data:{}},groupListResponse([], -1),{code:200,data:{items:null,count:0}},groupListResponse([groupRow({recent_results:[groupRecent({status_key:'unknown'})]})]),groupListResponse([groupRow({recent_results:null})]),groupListResponse([groupRow(),groupRow()])])assert.throws(()=>dto.readTaskGroupList(response))
  assert.throws(()=>dto.readTaskGroupUpdate({code:200,data:{item:groupRow({id:2})}},0))
})
test('query uses original array protocol, trims blanks, snapshots selections and preserves zero filters', t => {
  const h=setupGroupList();t.after(h.close);const dto=h.load('task-group-list-records.ts'),filters={...groupFilters(),name:'  Example  ',navigation_module_id:0,test_envs:[0],case_types:[1],execution_scenes:['regression_test'],status:0,is_notice:0}
  const query=dto.taskGroupQuery(0,filters,2,20);assert.deepEqual(query,{page:2,pageSize:20,project_product_id:0,module_ids:[0],name:'Example',test_envs:[0],case_types:[1],execution_scenes:['regression_test'],status:0,is_notice:0})
  filters.test_envs.push(2);assert.deepEqual(query.test_envs,[0]);assert.deepEqual(dto.taskGroupQuery(null,groupFilters(),1,20),{page:1,pageSize:20})
})
test('notice and trigger DTOs reject invalid data instead of showing successful empty results', t => {
  const h=setupGroupList();t.after(h.close);const dto=h.load('task-group-list-records.ts')
  assert.throws(()=>dto.readGroupNoticeExecutions({code:200,data:null}));assert.throws(()=>dto.readGroupNoticeExecutions({code:200,data:[{id:0,test_env:0},{id:0,test_env:0}]}))
  assert.throws(()=>dto.readGroupTriggerResult({code:200,data:{generated_count:'1',failed_count:0}}))
})
test('list is independent of pending/failed enums and both failures remain separately retryable', async t => {
  const enums=deferred(),h=setupGroupList({getEnum:()=>enums.promise});t.after(h.close);await h.mount()
  assert.equal(h.rows.value.length,1);assert.equal(h.loading.value,false);assert.equal(h.enumsLoading.value,true)
  enums.reject(Error('network'));await flush();assert.match(h.enumsError.value,/失败/);assert.equal(h.rows.value.length,1)
  h.enumStore.getEnum=async()=>{};await h.loadEnums();assert.equal(h.enumsError.value,'')
})
test('newer filters/products win late responses and old finally cannot clear current list loading', async t => {
  const first=deferred(),second=deferred();let calls=0
  const h=setupGroupList({getScheduledTaskGroups:()=>++calls===1?first.promise:second.promise});t.after(h.close);await h.mount()
  h.props.projectProductId=2;await flush();assert.equal(h.rows.value.length,0)
  first.resolve(groupListResponse([groupRow({name:'Old'})]));await flush();assert.equal(h.loading.value,true);assert.equal(h.rows.value.length,0)
  second.resolve(groupListResponse([groupRow({name:'Current'})]));await flush();assert.equal(h.rows.value[0].name,'Current');assert.equal(h.loading.value,false)
})
test('filters/search/page size reset or preserve pages appropriately and shrinking totals refetch a valid page', async t => {
  const h=setupGroupList({getScheduledTaskGroups:async query=>groupListResponse([groupRow()],query.page>1?1:5)});t.after(h.close);await h.mount()
  h.pagination.page=4;await h.list.load();assert.equal(h.pagination.page,1);assert.deepEqual(h.reads.filter(x=>x[0]==='getScheduledTaskGroups').slice(-2).map(x=>x[1].page),[4,1])
  h.pagination.page=2;h.props.filters.name='Example';await flush();assert.equal(h.pagination.page,1)
  h.pagination.page=3;await h.applyFilters();assert.equal(h.pagination.page,1);h.pagination.pageSize=50;await h.pagination.onChange();assert.equal(h.reads.at(-1)[1].pageSize,50)
})
test('failed list reads keep available data, release loading and permit a successful retry', async t => {
  let fail=false;const h=setupGroupList({getScheduledTaskGroups:async()=>fail?{code:403}:groupListResponse()});t.after(h.close);await h.mount();fail=true
  assert.equal(await h.list.load(),false);assert.equal(h.rows.value.length,1);assert.equal(h.loading.value,false);assert.match(h.listError.value,/失败/)
  fail=false;assert.equal(await h.list.load(),true);assert.equal(h.listError.value,'')
})
test('identical concurrent loads share one request, while a committed write invalidates an older pending list', async t => {
  const pending=deferred();let calls=0
  const h=setupGroupList({getScheduledTaskGroups:()=>++calls===2?pending.promise:Promise.resolve(groupListResponse([groupRow({name:calls>2?'After write':'Initial'})]))});t.after(h.close);await h.mount()
  const first=h.list.load(),same=h.list.load();assert.equal(first,same);await flush();assert.equal(calls,2)
  h.deleteGroup(groupRow());await h.confirmations[0].config.onBeforeOk();await flush();assert.equal(calls,3);assert.equal(h.rows.value[0].name,'After write')
  pending.resolve(groupListResponse([groupRow({name:'Stale'})]));await first;assert.equal(h.rows.value[0].name,'After write')
})
test('a synchronous read failure can retry and does not leave a resolved promise cached as pending', async t => {
  let fail=true;const h=setupGroupList({getScheduledTaskGroups:()=>{if(fail)throw Error('network');return Promise.resolve(groupListResponse())}});t.after(h.close);await h.mount()
  assert.match(h.listError.value,/失败/);fail=false;assert.equal(await h.list.load(),true);assert.equal(h.rows.value.length,1)
})
test('editor/member saved events force authority reload instead of sharing a pre-save pending list request', async t => {
  const pending=deferred();let calls=0
  const h=setupGroupList({getScheduledTaskGroups:()=>++calls===2?pending.promise:Promise.resolve(groupListResponse([groupRow({name:calls>2?'Saved':'Initial'})]))});t.after(h.close);await h.mount()
  const old=h.list.load();await flush();await h.refreshGroups();assert.equal(calls,3);assert.equal(h.rows.value[0].name,'Saved')
  pending.resolve(groupListResponse([groupRow({name:'Before save'})]));await old;assert.equal(h.rows.value[0].name,'Saved');assert.deepEqual(h.events,[['changed']])
})
test('editor/detail/export/filter/report calls carry fixed zero IDs and navigation defaults', async t => {
  const h=setupGroupList();t.after(h.close);await h.mount();await h.openCreate(0);h.openEdit(groupRow());h.openDetail(groupRow());h.openOfflineReport(groupRow());h.filterTasks(groupRow());await h.openGroupReport(groupRecent());await h.openGroupReport(undefined)
  assert.deepEqual(h.windows.editor,[['create',{projectProduct:0,module:0}],['edit',0]]);assert.deepEqual(h.windows.detail,[0]);assert.equal(h.offlineExport.sourceId,0)
  assert.deepEqual(h.events,[['filter-tasks',{id:0,name:'Example group'}]]);assert.equal(h.navigation.length,1);assert.equal(h.navigation[0].query.group_execution_id,0)
})
test('switch writes whitelist freshly read configuration and updates rows immutably; duplicate/conflicting operations are locked', async t => {
  const pending=deferred(),source=groupRow();const h=setupGroupList({updateScheduledTaskGroup:()=>pending.promise});t.after(h.close);await h.mount()
  const row=h.rows.value[0],saving=h.changeGroupSwitch(row,'is_notice',false);await flush();assert.equal(h.switchIds.has(0),true)
  assert.equal(await h.changeGroupSwitch(row,'status',false),false);h.deleteGroup(row);h.triggerGroup(row);assert.equal(h.confirmations.length,0)
  const payload=h.writes[0][1];assert.equal(payload.id,0);assert.equal(payload.is_notice,0);assert.equal(payload.fail_notice,0);assert.deepEqual(payload.module_ids,[0]);assert.equal('members' in payload,false);assert.equal('update_time' in payload,false);assert.equal('new_task_report_retention_policy' in payload,false)
  pending.resolve({code:200,data:{item:groupRow({is_notice:0,fail_notice:0})}});assert.equal(await saving,true);assert.equal(row.is_notice,1);assert.equal(source.is_notice,1);assert.equal(h.pendingGroups.size,0)
})
test('context change during switch detail preparation prevents a subsequent write', async t => {
  const pending=deferred(),h=setupGroupList({getScheduledTaskGroupDetail:()=>pending.promise});t.after(h.close);await h.mount()
  const saving=h.changeGroupSwitch(h.rows.value[0],'status',false);h.user.roleId++;pending.resolve({code:200,data:groupListDetail()});await saving;assert.equal(h.writes.length,0);assert.equal(h.pendingGroups.size,0)
})
test('switch network/business failure preserves row state; committed malformed reply is distinguished and reloaded', async t => {
  let attempt=0;const h=setupGroupList({updateScheduledTaskGroup:async()=>{if(++attempt===1)throw Error('network');return attempt===2?{code:403}:{code:200,data:{item:groupRow({id:2})}}}});t.after(h.close);await h.mount()
  for(let i=0;i<3;i++){assert.equal(await h.changeGroupSwitch(h.rows.value[0],'status',false),false);assert.equal(h.pendingGroups.size,0)}
  assert.match(h.operationError.value,/已提交/);assert.equal(h.rows.value[0].status,1)
})
test('trigger confirmation snapshots the ID, deduplicates confirms and reports partial generation failures', async t => {
  const pending=deferred(),h=setupGroupList({triggerScheduledTaskGroup:()=>pending.promise});t.after(h.close);await h.mount()
  const row=groupRow();h.triggerGroup(row);h.triggerGroup(row);assert.equal(h.confirmations.length,1);row.id=2
  const modal=h.confirmations[0],saving=modal.config.onBeforeOk();assert.equal(h.triggeringIds.has(0),true);assert.equal(await modal.config.onBeforeOk(),false);assert.deepEqual(h.writes,[['triggerScheduledTaskGroup',0]])
  pending.resolve({code:200,data:{generated_count:2,failed_count:1}});assert.equal(await saving,true);assert.equal(modal.closed,true);assert.match(h.messages[0][1],/生成 2 个执行报告，1 个子任务生成失败/);assert.equal(h.triggeringIds.size,0)
})
test('cancelled or context-invalidated confirmation callbacks cannot later trigger or delete', async t => {
  const h=setupGroupList();t.after(h.close);await h.mount();h.triggerGroup(groupRow());const cancelled=h.confirmations[0];cancelled.config.onCancel();assert.equal(await cancelled.config.onBeforeOk(),false)
  h.deleteGroup(groupRow());const stale=h.confirmations[1];h.props.projectProductId=2;assert.equal(stale.closed,true);assert.equal(await stale.config.onBeforeOk(),false);assert.equal(h.writes.length,0)
})
test('trigger failure releases physical loading and keeps confirmation retryable', async t => {
  let attempt=0;const h=setupGroupList({triggerScheduledTaskGroup:async()=>{if(++attempt===1)throw Error('network');return {code:attempt===2?403:200,data:{generated_count:1,failed_count:0}}}});t.after(h.close);await h.mount();h.triggerGroup(groupRow());const modal=h.confirmations[0]
  for(let i=0;i<2;i++){assert.equal(await modal.config.onBeforeOk(),false);assert.equal(modal.closed,false);assert.equal(h.triggeringIds.size,0)}
  assert.equal(await modal.config.onBeforeOk(),true);assert.equal(modal.closed,true)
})
test('delete uses the confirmed ID, deduplicates writes and treats subsequent list failure separately', async t => {
  const pending=deferred();let failRead=false;const h=setupGroupList({getScheduledTaskGroups:async()=>failRead?{code:403}:groupListResponse(),deleteScheduledTaskGroup:()=>pending.promise});t.after(h.close);await h.mount()
  const row=groupRow();h.deleteGroup(row);row.id=2;const modal=h.confirmations[0],saving=modal.config.onBeforeOk();assert.equal(await modal.config.onBeforeOk(),false);assert.deepEqual(h.writes,[['deleteScheduledTaskGroup',0]])
  failRead=true;pending.resolve({code:200});assert.equal(await saving,true);await flush();assert.equal(modal.closed,true);assert.match(h.listError.value,/失败/);assert.equal(h.deletingIds.size,0);assert.match(h.messages[0][1],/已删除/);assert.deepEqual(h.events,[['changed']])
})
test('delete rejection keeps the confirmation open and allows retry without early success', async t => {
  let fail=true;const h=setupGroupList({deleteScheduledTaskGroup:async()=>({code:fail?403:200})});t.after(h.close);await h.mount();h.deleteGroup(groupRow());const modal=h.confirmations[0]
  assert.equal(await modal.config.onBeforeOk(),false);assert.equal(modal.closed,false);assert.equal(h.messages.length,1);assert.equal(h.messages[0][0],'error');fail=false;assert.equal(await modal.config.onBeforeOk(),true)
})
test('notice loading, fixed batch zero and send retry are isolated from list state and duplicate submissions', async t => {
  const pending=deferred();let fail=true;const h=setupGroupList({resendTaskGroupNotice:()=>fail?Promise.resolve({code:403}):pending.promise});t.after(h.close);await h.mount();await h.openResendNotice(groupRow())
  assert.equal(h.noticeVisible.value,true);assert.equal(h.noticeExecutionId.value,0);assert.equal(h.noticeLoadingIds.size,0)
  assert.equal(await h.confirmResendNotice(),false);assert.equal(h.noticeVisible.value,true);assert.match(h.noticeError.value,/失败/);assert.equal(h.noticeSending.value,false)
  fail=false;const sending=h.confirmResendNotice();assert.equal(await h.confirmResendNotice(),false);h.noticeExecutionId.value=99
  assert.deepEqual(h.writes.at(-1),['resendTaskGroupNotice',0,0]);pending.resolve({code:200});assert.equal(await sending,true);assert.equal(h.noticeVisible.value,false);assert.equal(h.noticeSending.value,false)
})
test('notice metadata read failures can retry and do not masquerade as no executions', async t => {
  let fail=true;const h=setupGroupList({getLatestTaskGroupExecutions:async()=>fail?{code:403}:{code:200,data:[{id:0,test_env:0,planned_at:'2026-11-09',notice_group__name:null}]}});t.after(h.close);await h.mount();await h.openResendNotice(groupRow())
  assert.equal(h.noticeVisible.value,true);assert.equal(h.noticeError.value,'');assert.equal(await h.confirmResendNotice(),false)
  fail=false;await h.loadNoticeExecutions();assert.equal(h.noticeExecutionId.value,0);assert.equal(h.noticeError.value,'')
})
test('notice cancellation discards late batch reads, and missing/non-selected batches cannot be sent', async t => {
  const pending=deferred(),h=setupGroupList({getLatestTaskGroupExecutions:()=>pending.promise});t.after(h.close);await h.mount()
  const opening=h.openResendNotice(groupRow());assert.equal(h.noticeLoading.value,true);h.closeNotice();pending.resolve({code:200,data:[{id:0,test_env:0}]});await opening
  assert.equal(h.noticeVisible.value,false);assert.deepEqual(h.noticeExecutions.value,[]);assert.equal(h.noticeLoading.value,false);assert.equal(await h.confirmResendNotice(),false)
})
test('notice sends only a batch from the loaded options and rejects a manually injected batch ID', async t => {
  const h=setupGroupList();t.after(h.close);await h.mount();await h.openResendNotice(groupRow());h.noticeExecutionId.value=99
  assert.equal(await h.confirmResendNotice(),false);assert.equal(h.writes.length,0);h.noticeExecutionId.value=0;assert.equal(await h.confirmResendNotice(),true)
})
test('a late batch response from a cancelled window cannot clear a new window loading or replace its options', async t => {
  const first=deferred(),second=deferred(),h=setupGroupList({getLatestTaskGroupExecutions:id=>id===0?first.promise:second.promise});t.after(h.close);await h.mount()
  const old=h.openResendNotice(groupRow());h.closeNotice();const current=h.openResendNotice(groupRow({id:2}))
  first.resolve({code:200,data:[{id:0,test_env:0}]});await old;assert.equal(h.noticeLoading.value,true);assert.equal(h.noticeGroup.value.id,2);assert.deepEqual(h.noticeExecutions.value,[])
  second.resolve({code:200,data:[{id:69,test_env:1}]});await current;assert.equal(h.noticeExecutionId.value,69);assert.equal(h.noticeLoading.value,false)
})
test('empty execution lists retain the original no-executions feedback and never send', async t => {
  const h=setupGroupList({getLatestTaskGroupExecutions:async()=>({code:200,data:[]})});t.after(h.close);await h.mount();await h.openResendNotice(groupRow())
  assert.equal(h.noticeVisible.value,false);assert.match(h.messages[0][1],/暂无执行批次/);assert.equal(await h.confirmResendNotice(),false)
})
test('all identity changes clear previous rows/windows and suppress stale writes and confirms', async () => {
  for(const change of [h=>h.user.userId++,h=>h.user.roleId++,h=>h.user.token='example-new',h=>h.user.selected_environment++,h=>h.permission.permissionKeys.push('example:read'),h=>h.route.path='/other',h=>h.route.fullPath+='?id=2']) {
    const pending=deferred(),h=setupGroupList({triggerScheduledTaskGroup:()=>pending.promise})
    try {await h.mount();h.openOfflineReport(groupRow());h.triggerGroup(groupRow());const modal=h.confirmations[0],saving=modal.config.onBeforeOk();change(h);assert.equal(h.rows.value.length,0);assert.equal(h.offlineExport.visible,false);assert.equal(modal.closed,true);pending.resolve({code:200,data:{generated_count:1,failed_count:0}});await saving;assert.deepEqual(h.messages,[]);assert.equal(h.pendingGroups.size,0)}finally{h.close()}
  }
})
test('background/KeepAlive/unmount invalidate pending reads and prevent background requests; returning restores reads', async () => {
  for(const mode of ['background','deactivate','unmount']) {
    const pending=deferred();let count=0;const h=setupGroupList({getScheduledTaskGroups:()=>++count===1?pending.promise:Promise.resolve(groupListResponse([groupRow({name:'Restored'})]))})
    try{await h.mount();if(mode==='background')h.visibility('hidden');else h.callbacks[mode].forEach(fn=>fn());pending.resolve(groupListResponse([groupRow({name:'Old'})]));await flush();assert.equal(h.rows.value.length,0);assert.equal(h.loading.value,false);await h.list.load();assert.equal(count,1)
      if(mode==='background')h.visibility('visible');if(mode==='deactivate')h.callbacks.activate.forEach(fn=>fn());await flush();if(mode!=='unmount')assert.equal(h.rows.value[0].name,'Restored')
    }finally{h.close()}
  }
})
test('notice sending keeps physical lock after cancellation/identity invalidation until actual settlement', async t => {
  const pending=deferred(),h=setupGroupList({resendTaskGroupNotice:()=>pending.promise});t.after(h.close);await h.mount();await h.openResendNotice(groupRow());const sending=h.confirmResendNotice()
  h.user.roleId++;assert.equal(h.noticeVisible.value,false);assert.equal(h.noticeSending.value,true);await h.openResendNotice(groupRow({id:2}));assert.equal(h.noticeVisible.value,false)
  pending.resolve({code:200});await sending;assert.equal(h.noticeSending.value,false);assert.equal(h.pendingGroups.size,0);assert.deepEqual(h.messages,[])
})
test('write settlement after returning refreshes current conditions without replaying old success', async t => {
  const pending=deferred();let count=0;const h=setupGroupList({getScheduledTaskGroups:async()=>{count++;return groupListResponse()},deleteScheduledTaskGroup:()=>pending.promise});t.after(h.close);await h.mount();h.deleteGroup(groupRow());const saving=h.confirmations[0].config.onBeforeOk()
  h.visibility('hidden');h.visibility('visible');await flush();const before=count;pending.resolve({code:200});await saving;await flush();assert.equal(count,before+1);assert.deepEqual(h.messages,[])
})
test('group manager SFC bindings and styles compile without any page state or record mutation', async () => {
  const parent=readFileSync(path.join(groupListBase,'index.vue'),'utf8');assert.match(parent,/@changed="loadTaskGroupOptions"/)
  const filename=path.join(groupListBase,'components/TaskGroupManager.vue'),source=readFileSync(filename,'utf8'),{descriptor,errors}=parse(source,{filename});assert.deepEqual(errors,[])
  assert.doesNotMatch(descriptor.scriptSetup.content,/\bany\b|Object.assign\(record|\.\.\.data,/)
  const script=compileScript(descriptor,{id:'group-manager'}),template=compileTemplate({source:descriptor.template.content,filename,id:'group-manager',compilerOptions:{bindingMetadata:script.bindings}});assert.deepEqual(template.errors,[])
  assert.deepEqual([...new Set([...template.code.matchAll(/_ctx\.([A-Za-z_$]\w*)/g)].map(match=>match[1]))].filter(key=>!(key in script.bindings)),[])
  for(const style of descriptor.styles)assert.deepEqual((await compileStyleAsync({source:style.content,filename,id:'group-manager',scoped:true})).errors,[])
})
