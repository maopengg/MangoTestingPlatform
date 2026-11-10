import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/timing/tasks')
const member = (values = {}) => ({ id: 0, module: { id: 0, full_path: 'Root / Child' }, task_id: 0, task_name: 'Example task', child_enabled: false, effective_enabled: false, sync_status: 'synced', ...values })
const detail = (values = {}) => ({ id: 0, name: 'Example group', module_count: 1, enabled_task_count: 0, sync_status: 'synced', members: [member()], ...values })
function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], writes = [], messages = []
  const route = vue.reactive({ path: '/timing/tasks/index', fullPath: '/timing/tasks/index' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-token', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: [] })
  const h = harness('TaskGroupDetailDrawer', 'visible,recordId,detail,loading,error,operationError,pendingMembers,memberKey,open,loadDetail,changeMemberStatus,closeDrawer:close', { base,
    api: {
      getScheduledTaskGroupDetail: id => { reads.push(id); return overrides.read ? overrides.read(id) : Promise.resolve({ code: 200, data: detail({ id }) }) },
      updateScheduledTaskGroupMemberStatus: (...args) => { writes.push(args); return overrides.write ? overrides.write(...args) : Promise.resolve({ code: 200, data: member({ child_enabled: args[2], effective_enabled: args[2] }) }) },
    }, modules: {
      vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success','error'].map(key => [key, value => messages.push([key,value])])) },
    },
  })
  return { ...h, route, user, permission, callbacks, reads, writes, messages,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous },
  }
}
test('finite group detail and member DTOs preserve zero/long IDs and exclude unrelated server fields', t => {
  const h = setup(); t.after(h.close); const dto = h.load('task-group-detail-records.ts'), source = detail({ extra: 'omit' })
  const parsed = dto.readTaskGroupDetail({ code: 200, data: source }, 0)
  parsed.members[0].module.full_path = 'Draft'; assert.equal(source.members[0].module.full_path, 'Root / Child'); assert.equal('extra' in parsed, false)
  assert.equal(parsed.members[0].task_id, 0)
  const id = '90071992547409930000'; assert.equal(dto.readTaskGroupDetail({ code: 200, data: detail({ id }) }, id).id, id)
  for (const data of [detail({ id: 1 }), detail({ members: null }), detail({ members: [member(),member()] }), detail({ module_count: -1 }), detail({ members: [member({ child_enabled: 1 })] })]) assert.throws(() => dto.readTaskGroupDetail({ code: 200, data }, 0))
  assert.throws(() => dto.readTaskGroupMemberUpdate({ code: 200, data: member({ id: 1 }) }, member()))
  assert.throws(() => dto.readTaskGroupMemberUpdate({ code: 200, data: member({ module: { id: 1, full_path: 'Other' } }) }, member()))
})
test('zero ID detail opens with isolated loading and no prior record survives cancel/reopen', async t => {
  const h = setup(); t.after(h.close); await h.open(0)
  assert.equal(h.detail.value.id, 0); assert.equal(h.visible.value, true); h.closeDrawer(); assert.equal(h.detail.value, null)
  await h.open(2); assert.equal(h.detail.value.id, 2); assert.equal(h.loading.value, false)
})
test('late reads cannot overwrite a newer record or clear its loading', async t => {
  const first = deferred(), second = deferred(), h = setup({ read: id => id === 1 ? first.promise : second.promise }); t.after(h.close)
  const a = h.open(1), b = h.open(2); first.resolve({ code: 200, data: detail({ id: 1 }) }); await a
  assert.equal(h.detail.value, null); assert.equal(h.loading.value, true)
  second.resolve({ code: 200, data: detail({ id: 2 }) }); await b; assert.equal(h.detail.value.id, 2)
})
test('failed detail is retryable and rejected/mismatched responses do not display another group', async t => {
  let attempt = 0; const h = setup({ read: async () => ({ code: ++attempt === 1 ? 403 : 200, data: detail({ id: attempt === 2 ? 2 : 0 }) }) }); t.after(h.close)
  await h.open(0); assert.match(h.error.value, /失败/); await h.loadDetail(); assert.equal(h.detail.value, null)
  await h.loadDetail(); assert.equal(h.detail.value.id, 0); assert.equal(h.error.value, ''); assert.equal(h.loading.value, false)
})
test('member update fixes zero IDs, prevents duplicate writes and replaces rows without mutating source objects', async t => {
  const source = detail(), pending = deferred(), h = setup({ read: async () => ({ code: 200, data: source }), write: () => pending.promise }); t.after(h.close); await h.open(0)
  const original = h.detail.value, originalMember = original.members[0], saving = h.changeMemberStatus(originalMember, true)
  assert.equal(h.pendingMembers.has(h.memberKey(0)), true); assert.equal(await h.changeMemberStatus(originalMember, false), false); assert.deepEqual(h.writes, [[0,0,true]])
  pending.resolve({ code: 200, data: member({ child_enabled: true, effective_enabled: true }) }); assert.equal(await saving, true)
  assert.equal(h.detail.value.members[0].child_enabled, true); assert.equal(h.detail.value.enabled_task_count, 1)
  assert.equal(originalMember.child_enabled, false); assert.equal(source.members[0].child_enabled, false); assert.notEqual(h.detail.value, original); assert.deepEqual(h.events,[['changed']]); assert.equal(h.pendingMembers.size,0)
})
test('member failure preserves current state and permits retry after releasing the physical lock', async t => {
  let attempt = 0; const h = setup({ write: async () => { if (++attempt === 1) throw Error('network'); return { code: attempt === 2 ? 403 : 200, data: member({ child_enabled: true, effective_enabled: true }) } } }); t.after(h.close); await h.open(0)
  for (let i=0;i<2;i++) { assert.equal(await h.changeMemberStatus(h.detail.value.members[0], true), false); assert.equal(h.detail.value.members[0].child_enabled,false); assert.match(h.operationError.value,/失败/); assert.equal(h.pendingMembers.size,0) }
  assert.equal(await h.changeMemberStatus(h.detail.value.members[0],true),true)
})
test('a committed malformed member response is identified and authority is reloaded instead of reporting a clean rollback', async t => {
  let changed = false
  const h = setup({ read: async () => ({ code:200,data:detail({ members:[member({ child_enabled:changed,effective_enabled:changed })],enabled_task_count:Number(changed) }) }), write: async () => { changed=true;return { code:200,data:member({ id:2 }) } } }); t.after(h.close); await h.open(0)
  assert.equal(await h.changeMemberStatus(h.detail.value.members[0],true),false); assert.match(h.operationError.value,/已提交/)
  assert.equal(h.detail.value.enabled_task_count,1); assert.equal(h.reads.length,2); assert.deepEqual(h.events,[['changed']])
})
test('a pending read started before a member commit cannot restore outdated state', async t => {
  const pending = deferred(); let attempt=0
  const h = setup({ read: () => ++attempt === 1 ? Promise.resolve({ code:200,data:detail() }) : pending.promise }); t.after(h.close); await h.open(0)
  const saving = h.changeMemberStatus(h.detail.value.members[0],true), reading = h.loadDetail(); await saving
  pending.resolve({ code:200,data:detail() }); await reading; assert.equal(h.detail.value.members[0].child_enabled,true); assert.equal(h.loading.value,false)
})
test('cancel/reopen retains the same member physical lock until the prior write settles', async t => {
  let committed = false
  const pending = deferred(), h = setup({ write: () => pending.promise, read: async () => ({ code:200,data:detail({ members:[member({ child_enabled:committed,effective_enabled:committed })],enabled_task_count:Number(committed) }) }) }); t.after(h.close); await h.open(0)
  const saving=h.changeMemberStatus(h.detail.value.members[0],true); h.closeDrawer(); await h.open(0)
  assert.equal(await h.changeMemberStatus(h.detail.value.members[0],true),false)
  committed=true; pending.resolve({ code:200,data:member({ child_enabled:true,effective_enabled:true }) }); await saving
  assert.equal(h.detail.value.members[0].child_enabled,true); assert.equal(h.reads.length,3); assert.deepEqual(h.messages,[]); assert.deepEqual(h.events,[['changed']]); assert.equal(h.pendingMembers.size,0)
})
test('identity changes close the drawer and suppress old write feedback for every identity dimension', async () => {
  for (const change of [h=>h.user.userId++,h=>h.user.roleId++,h=>h.user.token='example-new',h=>h.user.selected_environment++,h=>h.permission.permissionKeys.push('example:read'),h=>h.route.path='/other',h=>h.route.fullPath+='?id=2']) {
    const pending=deferred(),h=setup({ write:()=>pending.promise })
    try { await h.open(0);const saving=h.changeMemberStatus(h.detail.value.members[0],true);change(h);assert.equal(h.visible.value,false);assert.equal(h.detail.value,null);pending.resolve({ code:200,data:member() });await saving;assert.deepEqual(h.messages,[]);assert.deepEqual(h.events,[]) } finally { h.close() }
  }
})
test('background, KeepAlive and unmount invalidate detail reads without reopening the drawer', async () => {
  for (const mode of ['background','deactivate','unmount']) {
    const pending=deferred(),h=setup({ read:()=>pending.promise })
    try { h.mount();const opening=h.open(0);if(mode==='background')h.visibility('hidden');else h.callbacks[mode].forEach(fn=>fn());pending.resolve({ code:200,data:detail() });await opening;assert.equal(h.visible.value,false);assert.equal(h.loading.value,false);assert.equal(h.detail.value,null);await h.open(0);assert.equal(h.visible.value,false) } finally { h.close() }
  }
})
test('write settlement after returning refreshes the parent without applying stale drawer state', async t => {
  const pending=deferred(),h=setup({ write:()=>pending.promise });t.after(h.close);h.mount();await h.open(0)
  const saving=h.changeMemberStatus(h.detail.value.members[0],true);h.visibility('hidden');h.visibility('visible')
  pending.resolve({ code:200,data:member() });await saving;assert.equal(h.visible.value,false);assert.deepEqual(h.messages,[]);assert.deepEqual(h.events,[['changed']])
})
test('an old member write never refreshes or patches a different group opened in the meantime', async t => {
  const pending=deferred(),h=setup({ write:()=>pending.promise });t.after(h.close);await h.open(0)
  const saving=h.changeMemberStatus(h.detail.value.members[0],true);await h.open(2)
  pending.resolve({ code:200,data:member({ child_enabled:true,effective_enabled:true }) });await saving
  assert.deepEqual(h.reads,[0,2]);assert.equal(h.detail.value.id,2);assert.equal(h.detail.value.members[0].child_enabled,false);assert.deepEqual(h.messages,[])
})
test('hidden, deactivated and unmounted drawers suppress pending write feedback and release physical locks only on settlement', async () => {
  for(const mode of ['background','deactivate','unmount']) {
    const pending=deferred(),h=setup({ write:()=>pending.promise })
    try {
      h.mount();await h.open(0);const key=h.memberKey(0),saving=h.changeMemberStatus(h.detail.value.members[0],true)
      if(mode==='background')h.visibility('hidden');else h.callbacks[mode].forEach(fn=>fn())
      assert.equal(h.pendingMembers.has(key),true);pending.resolve({ code:200,data:member() });await saving
      assert.equal(h.pendingMembers.size,0);assert.equal(h.visible.value,false);assert.deepEqual(h.messages,[]);assert.deepEqual(h.events,[])
    } finally { h.close() }
  }
})
test('detail drawer and parent bindings compile and parent delegates only the fixed record ID', async () => {
  const parent=readFileSync(path.join(base,'components/TaskGroupManager.vue'),'utf8')
  assert.match(parent,/<TaskGroupDetailDrawer ref="groupDetailRef" @changed="refreshGroups"/);assert.doesNotMatch(parent,/const detail = reactive|Number\(detail.id\)|Object.assign\(member/)
  for(const name of ['TaskGroupDetailDrawer','TaskGroupManager']) {
    const filename=path.join(base,'components',name+'.vue'),{ descriptor,errors }=parse(readFileSync(filename,'utf8'),{filename});assert.deepEqual(errors,[])
    const script=compileScript(descriptor,{id:name}),template=compileTemplate({source:descriptor.template.content,filename,id:name,compilerOptions:{bindingMetadata:script.bindings}});assert.deepEqual(template.errors,[])
    assert.deepEqual([...new Set([...template.code.matchAll(/_ctx\.([A-Za-z_$]\w*)/g)].map(match=>match[1]))].filter(key=>!(key in script.bindings)),[])
    for(const style of descriptor.styles)assert.deepEqual((await compileStyleAsync({source:style.content,filename,id:name,scoped:true})).errors,[])
  }
})
