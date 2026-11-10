import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { component, record, deferred, flush, config } from './helpers/auth-config-harness.mjs'

test('readonly code execution prevents duplicate runs and ignores results after reopening', async () => {
  const d=deferred();let calls=0
  const panel=component('AuthCustomCodePanel','customCodePanel,onRunCustomCode,customCodeRunningIds',{
    api:{postApiAuthConfigRefresh:()=>{calls++;return d.promise}},
  })
  const row=Object.freeze(record({auth_type:1,custom_code:'def auth(context): return {}'}))
  panel.handle.open(row);const first=panel.onRunCustomCode();await panel.onRunCustomCode()
  assert.equal(calls,1);assert.equal(panel.customCodeRunningIds.has(1),true)
  panel.handle.open({...row,id:2});d.resolve({data:{old:true}});await first
  assert.equal(panel.customCodePanel.result,null);assert.equal(panel.customCodePanel.code,row.custom_code)
  assert.equal(panel.customCodeRunningIds.size,0);assert.equal(panel.events.length,1);panel.cleanup()
})
test('code errors release loading and permit retry', async () => {
  let calls=0
  const panel=component('AuthCustomCodePanel','customCodePanel,onRunCustomCode,customCodeRunningIds',{
    api:{postApiAuthConfigRefresh:async()=>{if(++calls===1)throw new Error('failed');return {data:{ok:true}}}},
  })
  panel.handle.open(record({auth_type:1}));await panel.onRunCustomCode()
  assert.equal(panel.customCodePanel.error,'failed');assert.equal(panel.customCodeRunningIds.size,0)
  await panel.onRunCustomCode();assert.equal(panel.customCodePanel.result.ok,true);panel.cleanup()
})
test('cache drawer isolates records, handles failure and retries without repeating a write', async () => {
  const pending=[];let refreshed=0
  const panel=component('AuthCacheDrawer','cacheModal,cacheLoading,cacheError,retry',{
    api:{getApiAuthConfigCache:()=>{const d=deferred();pending.push(d);return d.promise},postApiAuthConfigRefresh:async()=>{refreshed++;throw new Error('failed')}},
  })
  const first=panel.handle.open(record());const second=panel.handle.open(record({id:2}))
  pending[1].resolve({data:{name:'new'}});await second;pending[0].resolve({data:{name:'old'}});await first
  assert.equal(panel.cacheModal.data.name,'new')
  await panel.handle.open(record(),true);assert.equal(panel.cacheError.value,'failed');assert.equal(panel.cacheLoading.value,false)
  panel.retry();pending[2].resolve({data:{name:'retry'}});await flush()
  assert.equal(panel.cacheModal.data.name,'retry');assert.equal(refreshed,1);panel.cleanup()
})
test('all page components compile and use permission-free shared controls', () => {
  const base='src/views/apitest/auth-config/'
  for(const file of ['index.vue',...readdirSync(base+'components').map(f=>'components/'+f)]) {
    const filename=base+file, source=readFileSync(filename,'utf8')
    assert.doesNotMatch(source,/v-permission|permission: ['"]/)
    const {descriptor,errors}=parse(source);assert.deepEqual(errors,[])
    const script=compileScript(descriptor,{id:file})
    assert.deepEqual(compileTemplate({source:descriptor.template.content,filename,id:file,compilerOptions:{bindingMetadata:script.bindings}}).errors,[])
  }
  assert.equal(config.tableColumns.find(c=>c.key==='name').width,240)
  assert.equal(config.tableColumns.find(c=>c.key==='actions').fixed,'right')
})
