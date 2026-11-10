import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { setupGroupEditor, groupDetail, groupTree, groupPreview, groupEditorBase } from './helpers/timing-task-group-editor-harness.mjs'

async function ready(h, values = {}) { await h.openEdit(0); await flush(); Object.assign(h.form, values) }
test('group draft/payload whitelist fields, isolate arrays and keep initialization policy creation-only even for ID zero', t => {
  const h = setupGroupEditor(); t.after(h.close); const dto = h.load('task-group-editor-records.ts')
  const original = groupDetail(), { draft } = dto.readTaskGroupEditorDetail({ code: 200, data: original }, 0)
  draft.module_ids.push(1); assert.equal(original.members.length, 1); const a = dto.createTaskGroupDraft(), b = dto.createTaskGroupDraft(); a.test_envs.push(0); assert.deepEqual(b.test_envs, [])
  const create = dto.taskGroupPayload({ ...draft, new_task_report_retention_policy: 'abnormal_only' }, null), edit = dto.taskGroupPayload(draft, 0)
  assert.equal(create.new_task_report_retention_policy, 'abnormal_only'); assert.equal('id' in create, false); assert.equal(edit.id, 0); assert.equal('new_task_report_retention_policy' in edit, false)
  assert.equal('revision' in edit, false); assert.equal('members' in edit, false); assert.equal('extra' in edit, false); assert.equal(edit.task_name_template, '【${{任务组名称}}】${{模块名称}}')
  draft.module_ids.push(2); assert.deepEqual(edit.module_ids, [0,1]); assert.equal(dto.validateTaskGroupDraft(draft), '')
  assert.throws(() => dto.readTaskGroupEditorDetail({ code: 200, data: original }, 2))
  assert.throws(() => dto.readTaskGroupEditorDetail({ code: 200, data: { ...original, members: null } }, 0))
  assert.throws(() => dto.readTaskGroupDraft({ test_envs: [false] }))
})
test('module hierarchy normalization deduplicates descendants, preserves zero/long IDs and never mutates metadata', t => {
  const h = setupGroupEditor(); t.after(h.close); const dto = h.load('task-group-editor-records.ts'), tree = dto.readTaskModuleTree(groupTree())
  assert.deepEqual(dto.normalizeTaskGroupModules([0,1,2,0], tree), [0]); assert.deepEqual(dto.normalizeTaskGroupModules([2,1], tree), [1])
  const decorated = dto.taskGroupSelectableTree(tree, [0]); assert.equal(decorated[0].children[0].disableCheckbox, true); assert.equal(tree[0].children[0].disableCheckbox, false)
  const long = '90071992547409930000', longTree = dto.readTaskModuleTree([{ key: long, title: 'Long', children: [] }]); assert.deepEqual(dto.normalizeTaskGroupModules([long],longTree), [long])
  assert.deepEqual(dto.normalizeTaskGroupModules(['0'], tree), [0]); assert.deepEqual(dto.normalizeTaskGroupModules([99],tree), [99])
  assert.throws(() => dto.readTaskModuleTree([{ key: 0, title: 'Root', children: [{ key: 0, title: 'Duplicate' }] }]))
  assert.throws(() => dto.readTaskModuleTree(null))
})
test('production scene restrictions stay bidirectionally exclusive while selected legacy conflicts remain removable', t => {
  const h = setupGroupEditor(); t.after(h.close); const dto = h.load('task-group-editor-records.ts'), options = h.enumStore.automation_execution_scene
  const disabled = scenes => dto.groupSceneOptions(options,[2],scenes).filter(item => item.disabled).map(item => item.key)
  assert.deepEqual(disabled(['stability_monitoring']), ['production_inspection','production_regression'])
  assert.deepEqual(disabled(['production_inspection','production_regression']), ['stability_monitoring'])
  assert.deepEqual(disabled(['stability_monitoring','production_inspection','production_regression']), [])
  assert.equal(dto.hasStabilitySceneConflict(['production_inspection','production_regression']), false)
  assert.equal(dto.groupSceneOptions(options,[0],[]).some(item => item.key === 'stability_monitoring'), false)
})
test('create initializes product/module zero, cancels cleanly and reopens with fresh default arrays', async t => {
  const h = setupGroupEditor(); t.after(h.close); await h.openCreate({ projectProduct: 0, module: 0 })
  assert.equal(h.form.project_product_id, 0); assert.deepEqual(h.form.module_ids, [0]); assert.equal(h.editorVisible.value, true)
  h.form.name = 'Draft'; h.form.test_envs.push(0); h.closeEditor(); assert.equal(h.form.name, ''); assert.equal(h.editorVisible.value, false)
  await h.openCreate({ projectProduct: 2, module: 99 }); assert.equal(h.form.project_product_id, 2); assert.deepEqual(h.form.module_ids, []); assert.deepEqual(h.form.test_envs, [])
})
test('navigation module prefill does not overwrite selection made while the tree loads', async t => {
  const pending = deferred(), h = setupGroupEditor({ getUserModuleTree: () => pending.promise }); t.after(h.close)
  const opening = h.openCreate({ projectProduct: 0, module: 0 }); await flush(); h.onModuleCheck([1])
  pending.resolve({ code: 200, data: groupTree() }); await opening; assert.deepEqual(h.form.module_ids, [1])
})
test('edit ID zero owns a finite draft, preserves selected labels and keeps product immutable', async t => {
  const source = groupDetail(), h = setupGroupEditor({ getScheduledTaskGroupDetail: async () => ({ code: 200, data: source }) }); t.after(h.close); await ready(h)
  assert.equal(h.editingId.value, 0); assert.equal(h.availableUsers.value[0].title, 'Another owner'); assert.equal(h.availableUsers.value.find(item => item.key === 0).title, 'Group owner')
  assert.equal(h.availableTimings.value[0].title, 'Hourly'); assert.equal(h.availableNotices.value[0].title, 'Notice option')
  h.form.name = 'Draft'; h.form.test_envs.push(2); assert.equal(source.name, 'Example group'); assert.deepEqual(source.test_envs, [0])
  h.productSelection.value = 2; await h.onEditorProductChange(2); assert.equal(h.form.project_product_id, 0)
})
test('late detail response from a cancelled edit cannot populate a new creation window', async t => {
  const pending = deferred(), h = setupGroupEditor({ getScheduledTaskGroupDetail: () => pending.promise }); t.after(h.close)
  const opening = h.openEdit(1); await flush(); h.closeEditor(); await h.openCreate({ projectProduct: 0, module: 0 }); h.form.name = 'New draft'
  pending.resolve({ code: 200, data: groupDetail({ id: 1 }) }); await opening
  assert.equal(h.editingId.value, null); assert.equal(h.form.name, 'New draft'); assert.deepEqual(h.form.module_ids, [0]); assert.equal(h.editorLoading.value, false)
})
test('overlapping edits keep the latest ID and reject a mismatched detail response', async t => {
  const old = deferred(), h = setupGroupEditor({ getScheduledTaskGroupDetail: id => id === 1 ? old.promise : Promise.resolve({ code: 200, data: groupDetail({ id: id === 3 ? 4 : id }) }) }); t.after(h.close)
  const opening = h.openEdit(1); await h.openEdit(2); old.resolve({ code: 200, data: groupDetail({ id: 1, name: 'Old' }) }); await opening; await flush()
  assert.equal(h.editingId.value, 2); assert.equal(h.form.name, 'Example group')
  h.closeEditor(); await h.openEdit(3); assert.equal(h.detailReady.value, false); assert.match(h.detailError.value, /失败/)
})
test('detail failure remains retryable without mixing configuration from a previous record', async t => {
  let fail = true
  const h = setupGroupEditor({ getScheduledTaskGroupDetail: async id => ({ code: fail ? 403 : 200, data: groupDetail({ id }) }) }); t.after(h.close)
  await h.openEdit(0); assert.equal(h.detailReady.value, false); assert.match(h.detailError.value, /失败/); assert.equal(h.editorLoading.value, false); assert.equal(h.form.name, '')
  await h.openPreview(); assert.equal(h.previews.length, 0); fail = false; await h.loadDetail(); await flush(); assert.equal(h.detailReady.value, true); assert.equal(h.form.project_product_id, 0)
})
test('metadata regions load independently and required module loading blocks premature preview', async t => {
  const tree = deferred(), owner = deferred(), h = setupGroupEditor({ getUserModuleTree: () => tree.promise, getUserName: () => owner.promise }); t.after(h.close)
  const opening = h.openCreate({ projectProduct: 0, module: 0 }); await flush()
  assert.equal(h.editorLoading.value, false); assert.equal(h.moduleLoading.value, true); assert.equal(h.usersLoading.value, true); assert.equal(h.timingsLoading.value, false); assert.equal(h.noticesLoading.value, false)
  await h.openPreview(); assert.match(h.previewError.value, /加载/); assert.equal(h.previews.length, 0)
  tree.resolve({ code: 200, data: groupTree() }); await flush(); assert.equal(h.moduleLoading.value, false); assert.equal(h.usersLoading.value, true)
  owner.resolve({ code: 200, data: [] }); await opening; assert.equal(h.metadataLoading.value, false)
})
test('failed module and enum retries cannot reuse stale ready state to preview', async () => {
  for (const kind of ['tree','enums']) {
    let fail = false
    const h = setupGroupEditor({ getUserModuleTree: async () => ({ code: fail && kind === 'tree' ? 403 : 200, data: groupTree() }), getEnum: async () => { if (fail && kind === 'enums') throw Error('network') } })
    try { await ready(h); fail = true; await h.retryMetadata(); await h.openPreview(); assert.equal(h.previews.length, 0); assert.match(h.previewError.value, /加载/); fail = false; await h.retryMetadata(); await h.openPreview(); assert.equal(h.previewVisible.value, true) }
    finally { h.close() }
  }
})
test('a failed metadata region can retry while an unrelated region remains pending', async t => {
  const pending = deferred(); let attempts = 0
  const h = setupGroupEditor({ getUserName: () => pending.promise, getSystemTimingList: async () => ({ code: ++attempts === 1 ? 403 : 200, data: [{ key: 0, title: 'Recovered schedule' }] }) }); t.after(h.close)
  const opening = h.openCreate({ projectProduct: 0, module: 0 }); await flush()
  assert.equal(h.usersLoading.value, true); assert.match(h.metadataErrors.value.join(), /定时策略/)
  await h.loadTimings(); assert.equal(h.usersLoading.value, true); assert.equal(h.timingsLoading.value, false)
  assert.equal(h.metadataErrors.value.length, 0); assert.equal(h.availableTimings.value[0].title, 'Recovered schedule')
  pending.resolve({ code: 200, data: [] }); await opening
  h.closeEditor(); await h.loadUsers(); await h.loadModules(); await h.loadNotices(); await h.loadEnums()
  assert.equal(h.metadataLoading.value, false)
})
test('optional notice lookup failure remains local and does not prevent valid no-notice preview', async t => {
  const h = setupGroupEditor({ getSystemNoticeName: async () => { throw Error('network') } }); t.after(h.close); await ready(h,{ notice_group: null, is_notice: 0 })
  assert.match(h.metadataErrors.value.join(), /通知组/); await h.openPreview(); assert.equal(h.previewVisible.value, true)
})
test('product changes clear dependent selections and discard late module/notice responses', async t => {
  const old = deferred(), current = deferred()
  const h = setupGroupEditor({ getUserModuleTree: product => product === 1 ? old.promise : product === 2 ? current.promise : Promise.resolve({ code: 200, data: groupTree() }) }); t.after(h.close)
  await h.openCreate({ projectProduct: 0, module: 0 }); h.form.notice_group = 0
  const first = h.onEditorProductChange(1), second = h.onEditorProductChange(2)
  assert.deepEqual(h.form.module_ids, []); assert.equal(h.form.notice_group, null)
  current.resolve({ code: 200, data: [{ key: 2, title: 'Current', children: [] }] }); await second; old.resolve({ code: 200, data: [{ key: 1, title: 'Old', children: [] }] }); await first
  assert.equal(h.moduleTree.value[0].title, 'Current'); assert.equal(h.moduleLoading.value, false); assert.equal(h.form.project_product_id, 2)
})
test('local validation covers required fields, empty owner normalization and conflicting scenes', async t => {
  const h = setupGroupEditor(); t.after(h.close); await ready(h)
  for (const [field,value,message] of [['name','  ','名称'],['case_people','','负责人'],['module_ids',[],'模块'],['execution_scenes',['stability_monitoring','production_regression'],'不能']]) {
    const before = h.form[field]; h.form[field] = value; await h.openPreview(); assert.match(h.previewError.value, new RegExp(message)); assert.equal(h.previews.length, 0); h.form[field] = before
  }
})
test('manual environment change during enum loading applies after recovery without erasing initial legacy scenes', async t => {
  const pending = deferred(), h = setupGroupEditor({ getEnum: () => pending.promise, getScheduledTaskGroupDetail: async () => ({ code: 200, data: groupDetail({ execution_scenes: ['stability_monitoring','regression_test'] }) }) }); t.after(h.close)
  const opening = h.openCreate({ projectProduct: 0, module: 0 }); await flush()
  h.form.test_envs = [0]; h.form.execution_scenes = ['stability_monitoring','regression_test']; h.onEnvironmentChange()
  pending.resolve(); await opening; assert.deepEqual(h.form.execution_scenes, ['regression_test'])
  h.closeEditor(); await h.openEdit(0); await flush(); assert.deepEqual(h.form.execution_scenes, ['stability_monitoring','regression_test'])
})
test('preview uses a fixed payload and prevents duplicate requests while in flight', async t => {
  const pending = deferred(), h = setupGroupEditor({ previewScheduledTaskGroup: () => pending.promise }); t.after(h.close); await ready(h)
  const previewing = h.openPreview(); await h.openPreview(); assert.equal(h.previews.length, 1); assert.equal(h.previewLoading.value, true)
  h.form.test_envs.push(2); assert.deepEqual(h.previews[0][1].test_envs, [0]); pending.resolve({ code: 200, data: groupPreview() }); await previewing
  assert.equal(h.previewVisible.value, true); assert.equal(h.previewLoading.value, false); assert.equal(h.editorLocked.value, true)
})
test('cancelled preview does not reopen after a late response and the next preview has fresh counts', async t => {
  const pending = deferred(); let calls = 0
  const h = setupGroupEditor({ previewScheduledTaskGroup: () => ++calls === 1 ? pending.promise : Promise.resolve({ code: 200, data: groupPreview({ create_count: 0, update_count: 1 }) }) }); t.after(h.close); await ready(h)
  const old = h.openPreview(); h.closePreview(); await h.openPreview(); pending.resolve({ code: 200, data: groupPreview({ remove_count: 9 }) }); await old
  assert.equal(h.preview.value.remove_count, 0); assert.equal(h.preview.value.update_count, 1); assert.equal(h.previewLoading.value, false)
})
test('confirmation saves the reviewed snapshot and edit zero never sends initial child retention', async t => {
  const pending = deferred(), h = setupGroupEditor({ updateScheduledTaskGroup: () => pending.promise }); t.after(h.close); await ready(h)
  await h.openPreview(); h.form.name = 'Changed behind preview'; h.form.module_ids.push(2)
  const saving = h.saveGroup(); await h.saveGroup(); assert.equal(h.writes.length, 1); assert.equal(h.writes[0][0], 'updateScheduledTaskGroup')
  assert.equal(h.writes[0][1].id, 0); assert.equal(h.writes[0][1].name, 'Example group'); assert.deepEqual(h.writes[0][1].module_ids,[0]); assert.equal('new_task_report_retention_policy' in h.writes[0][1], false)
  pending.resolve({ code: 200 }); assert.equal(await saving, true); assert.equal(h.editorVisible.value, false); assert.deepEqual(h.events,[['saved']])
})
test('create confirmation sends only whitelisted creation fields with selected initial retention', async t => {
  const h = setupGroupEditor(); t.after(h.close); const dto = h.load('task-group-editor-records.ts')
  await h.openCreate({ projectProduct: 0, module: 0 }); Object.assign(h.form,dto.readTaskGroupEditorDetail({ code: 200, data: groupDetail() },0).draft); h.form.new_task_report_retention_policy = 'abnormal_only'
  await h.openPreview(); assert.equal(await h.saveGroup(),true); const payload = h.writes[0][1]
  assert.equal(h.writes[0][0],'createScheduledTaskGroup'); assert.equal('id' in payload,false); assert.equal(payload.new_task_report_retention_policy,'abnormal_only'); assert.equal('revision' in payload,false)
})
test('network/business failures retain the preview and reviewed snapshot for retry', async t => {
  let attempts = 0
  const h = setupGroupEditor({ updateScheduledTaskGroup: async () => { if (++attempts === 1) throw Error('network'); return { code: attempts === 2 ? 403 : 200 } } }); t.after(h.close); await ready(h); await h.openPreview()
  for (let i=0;i<2;i++) { assert.equal(await h.saveGroup(),false); assert.equal(h.previewVisible.value,true); assert.equal(h.saveLoading.value,false); assert.match(h.saveError.value,/失败/); assert.equal(h.events.length,0) }
  assert.equal(await h.saveGroup(),true); assert.equal(h.writes.length,3)
})
test('preview failure releases loading, malformed response is rejected and retry remains available', async t => {
  let fail = true
  const h = setupGroupEditor({ previewScheduledTaskGroup: async () => fail ? { code: 200, data: groupPreview({ create_count: '1' }) } : { code: 200, data: groupPreview() } }); t.after(h.close); await ready(h)
  await h.openPreview(); assert.equal(h.previewVisible.value,false); assert.match(h.previewError.value,/失败/); assert.equal(h.previewLoading.value,false); assert.equal(await h.saveGroup(),false)
  fail = false; await h.openPreview(); assert.equal(h.previewVisible.value,true)
})
test('cancelled preview cannot save later without another review', async t => {
  const h = setupGroupEditor(); t.after(h.close); await ready(h); await h.openPreview(); h.closePreview(); assert.equal(await h.saveGroup(),false); assert.equal(h.writes.length,0); assert.equal(h.editorVisible.value,true)
})
test('cancel during write keeps physical lock and emits refresh without stale window feedback', async t => {
  const pending = deferred(), h = setupGroupEditor({ updateScheduledTaskGroup: () => pending.promise }); t.after(h.close); await ready(h); await h.openPreview()
  const saving = h.saveGroup(); h.closeEditor(); await h.openEdit(2); await h.openCreate(); assert.equal(h.editorVisible.value,false); assert.equal(h.saveLoading.value,true)
  pending.resolve({ code: 200 }); await saving; assert.equal(h.editorVisible.value,false); assert.deepEqual(h.messages,[]); assert.deepEqual(h.events,[['saved']]); assert.equal(h.saveLoading.value,false)
})
test('all identity dimensions invalidate configuration and suppress old save feedback', async () => {
  for (const change of [h=>h.user.userId++,h=>h.user.roleId++,h=>h.user.token='example-new',h=>h.user.selected_environment++,h=>h.permission.permissionKeys.push('example:read'),h=>h.route.path='/elsewhere',h=>h.route.fullPath+='?id=2']) {
    const pending = deferred(), h = setupGroupEditor({ updateScheduledTaskGroup: () => pending.promise })
    try { await ready(h); await h.openPreview(); const saving=h.saveGroup(); change(h); assert.equal(h.editorVisible.value,false); assert.equal(h.previewVisible.value,false); assert.equal(h.form.name,''); pending.resolve({ code:200 }); await saving; assert.deepEqual(h.messages,[]); assert.deepEqual(h.events,[]) }
    finally { h.close() }
  }
})
test('background, KeepAlive and unmount discard pending detail reads and keep closed windows closed', async () => {
  for (const mode of ['background','deactivate','unmount']) {
    const pending = deferred(), h = setupGroupEditor({ getScheduledTaskGroupDetail:()=>pending.promise })
    try { await h.mount(); const opening=h.openEdit(0); await flush(); if(mode==='background')h.visibility('hidden');else h.callbacks[mode].forEach(fn=>fn()); pending.resolve({ code:200,data:groupDetail() }); await opening; assert.equal(h.editorVisible.value,false); assert.equal(h.editorLoading.value,false); assert.equal(h.moduleTree.value,null); await h.openCreate(); assert.equal(h.editorVisible.value,false) }
    finally { h.close() }
  }
})
test('background, KeepAlive and unmount during saving do not replay old success on return', async () => {
  for (const mode of ['background','deactivate','unmount']) {
    const pending = deferred(), h = setupGroupEditor({ updateScheduledTaskGroup:()=>pending.promise })
    try {
      await h.mount(); await ready(h); await h.openPreview(); const saving=h.saveGroup(); if(mode==='background')h.visibility('hidden');else h.callbacks[mode].forEach(fn=>fn())
      assert.equal(h.saveLoading.value,true); pending.resolve({ code:200 }); await saving; assert.deepEqual(h.messages,[]); assert.deepEqual(h.events,[])
      if(mode==='background')h.visibility('visible');if(mode==='deactivate')h.callbacks.activate.forEach(fn=>fn()); await flush(); assert.equal(h.editorVisible.value,false)
    } finally { h.close() }
  }
})
test('parent delegates only record ID/navigation defaults and affected SFC bindings/styles compile', async () => {
  const source=readFileSync(path.join(groupEditorBase,'components/TaskGroupManager.vue'),'utf8')
  assert.match(source,/<TaskGroupEditorDialog ref="groupEditorRef" @saved="refreshGroups"/); assert.doesNotMatch(source,/const form = reactive|const preview = reactive|JSON\.parse\(JSON\.stringify\(form\)\)/)
  for(const file of ['TaskGroupManager','TaskGroupEditorDialog']) {
    const filename=path.join(groupEditorBase,'components',file+'.vue'),{ descriptor,errors }=parse(readFileSync(filename,'utf8'),{ filename });assert.deepEqual(errors,[])
    const script=compileScript(descriptor,{ id:file }),template=compileTemplate({ source:descriptor.template.content,filename,id:file,compilerOptions:{ bindingMetadata:script.bindings } });assert.deepEqual(template.errors,[])
    assert.deepEqual([...new Set([...template.code.matchAll(/_ctx\.([A-Za-z_$]\w*)/g)].map(match=>match[1]))].filter(name=>!(name in script.bindings)),[])
    for(const style of descriptor.styles)assert.deepEqual((await compileStyleAsync({ source:style.content,filename,id:file,scoped:true })).errors,[])
  }
})
