import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { reactive } from 'vue'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base=path.resolve('src/components/business')
const summary=(name='a')=>({data:{total:3,untagged:1,items:[{name,count:2}]}})
function tagHarness(name, bindings, overrides={}) {
  const user=reactive({userId:1,roleId:1,token:'fixture'})
  const h=harness(name,bindings,{base,filename:path.join(base,`${name}.vue`),...overrides,modules:{
    '@/store/modules/user':{default:()=>user},'@arco-design/web-vue/es/icon':{},...overrides.modules,
  }})
  return {...h,user}
}

test('categories occupy the table body only and both columns follow default-enabled',()=>{
  for(const kind of ['api','ui']) {
    const source=readFileSync(`src/views/${kind}test/public/index.vue`,'utf8')
    assert.ok(source.indexOf('<VariableTagWorkbench')>source.indexOf('<template #toolbar>'))
    assert.ok(source.indexOf('<a-table')>source.indexOf('<VariableTagWorkbench'))
    assert.ok(source.indexOf('</VariableTagWorkbench>')>source.indexOf('</a-table>'))
    const config=readFileSync(`src/views/${kind}test/public/config.ts`,'utf8')
    assert.ok(config.indexOf("title: '分类标签'")>config.indexOf("title: '默认开启'"))
  }
  const source=readFileSync(`${base}/VariableTagWorkbench.vue`,'utf8')
  assert.match(source,/IconLeft/);assert.match(source,/IconRight/)
  assert.match(source,/grid-template-columns: 160px/)
  assert.doesNotMatch(readFileSync(`${base}/VariableTagCell.vue`,'utf8'),/—/)
})

test('summary strips pagination and selection, ignores old product responses and filters names locally',async()=>{
  const pending=[],queries=[]
  const h=tagHarness('VariableTagWorkbench','summary,entries,keyword,refresh',{
    props:{modelValue:null,query:{project_product:1,page:4,tag:'selected'},read:query=>{queries.push(query);const d=deferred();pending.push(d);return d.promise}},
  })
  assert.deepEqual(queries[0],{project_product:1,tag_summary:true})
  h.props.query={project_product:2};await flush()
  pending[1].resolve(summary('new'));await flush()
  pending[0].resolve(summary('old'));await flush()
  assert.equal(h.summary.value.items[0].name,'new')
  assert.deepEqual(h.entries.value.map(item=>item.value),[null,'','new'])
  h.keyword.value='missing';await flush()
  assert.deepEqual(h.entries.value.map(item=>item.value),[null,''])
  h.close()
})

test('role changes immediately clear classification counts and reject old results',async()=>{
  const pending=[]
  const h=tagHarness('VariableTagWorkbench','summary',{
    props:{modelValue:'old',query:{},read:()=>{const d=deferred();pending.push(d);return d.promise}},
  })
  h.user.roleId=2;await flush()
  pending[0].resolve(summary('old'));await flush()
  assert.equal(h.summary.value.total,0)
  pending[1].resolve(summary('allowed'));await flush()
  assert.deepEqual(h.summary.value.items,[{name:'allowed',count:2}])
  h.close()
})

test('pagination and classification changes do not request summaries; identical in-flight reads merge',async()=>{
  const pending=[],queries=[]
  const h=tagHarness('VariableTagWorkbench','refresh,summary',{
    props:{modelValue:null,query:{project_product:1,name:'fixture',page:1,pageSize:20},read:query=>{
      queries.push(query);const d=deferred();pending.push(d);return d.promise
    }},
  })
  const first=h.refresh(),second=h.refresh()
  assert.equal(first,second)
  assert.equal(queries.length,1)
  pending[0].resolve(summary());await first;await flush()
  h.props.modelValue='a'
  h.props.query={page:2,pageSize:50,tag:'a',name:'fixture',project_product:1};await flush()
  assert.equal(queries.length,1)
  h.props.query={project_product:1,name:'changed',page:2,pageSize:50};await flush()
  assert.equal(queries.length,2)
  pending[1].resolve(summary('new'));await flush()
  assert.equal(h.summary.value.items[0].name,'new')
  h.close()
})

test('mutation forces a fresh summary and an older request cannot overwrite the updated result',async()=>{
  const pending=[]
  const h=tagHarness('VariableTagWorkbench','refreshAfterMutation,summary,loading',{
    props:{modelValue:null,query:{},read:()=>{const d=deferred();pending.push(d);return d.promise}},
  })
  const updated=h.refreshAfterMutation()
  assert.equal(pending.length,2)
  pending[1].resolve(summary('updated'));await updated
  pending[0].resolve(summary('before-save'));await flush()
  assert.equal(h.summary.value.items[0].name,'updated')
  assert.equal(h.loading.value,false)
  h.close()
})

test('identity and product changes in one update produce only one replacement summary request',async()=>{
  const pending=[]
  const h=tagHarness('VariableTagWorkbench','summary',{
    props:{modelValue:null,query:{project_product:1},read:()=>{const d=deferred();pending.push(d);return d.promise}},
  })
  h.user.roleId=2;h.props.query={project_product:2};await flush()
  assert.equal(pending.length,2)
  pending[0].resolve(summary('old'));pending[1].resolve(summary('current'));await flush()
  assert.equal(h.summary.value.items[0].name,'current')
  h.close()
})

test('failed summary releases the pending request and supports retry',async()=>{
  const pending=[]
  const h=tagHarness('VariableTagWorkbench','refresh,failed,loading',{
    props:{modelValue:null,query:{},read:()=>{const d=deferred();pending.push(d);return d.promise}},
  })
  pending[0].reject(Error('fixture'));await flush()
  assert.equal(h.failed.value,true);assert.equal(h.loading.value,false)
  const retry=h.refresh();assert.equal(pending.length,2)
  pending[1].resolve(summary());await retry
  assert.equal(h.failed.value,false);assert.equal(h.loading.value,false)
  h.close()
})

test('API and UI only force classification refresh after successful writes, not table reads',()=>{
  for(const kind of ['api','ui']) {
    const source=parse(readFileSync(`src/views/${kind}test/public/index.vue`,'utf8')).descriptor.scriptSetup.content
    const functions=Object.fromEntries([...source.matchAll(/(?:async )?function (\w+)\(/g)].map((match,index,all)=>
      [match[1],source.slice(match.index,all[index+1]?.index??source.length)]))
    assert.doesNotMatch(functions.doRefresh,/tagWorkbenchRef/)
    for(const name of ['onSaved','onDelete','onModifyStatus']) assert.match(functions[name],/refreshAfterMutation/)
  }
})

test('tag editor isolates product option requests, trims duplicates and rejects limits',async()=>{
  const pending=[]
  const h=tagHarness('VariableTagSelect','names,changeTags',{
    props:{modelValue:['existing'],productId:1,read:()=>{const d=deferred();pending.push(d);return d.promise}},
  })
  h.props.productId=2;await flush()
  pending[1].resolve(summary('new'));await flush()
  pending[0].resolve(summary('old'));await flush()
  assert.deepEqual(h.names.value,['new'])
  h.changeTags([' a ','a','']);assert.deepEqual(h.events.at(-1),['update:modelValue',['a']])
  const count=h.events.length
  h.changeTags(['a'.repeat(33)]);assert.equal(h.events.length,count)
  h.close()
})

test('all shared category components compile with the project Vue compiler',()=>{
  for(const name of ['VariableTagWorkbench','VariableTagSelect','VariableTagCell','VariableTagBatchDialog']) {
    const filename=`${base}/${name}.vue`,descriptor=parse(readFileSync(filename,'utf8')).descriptor
    const script=compileScript(descriptor,{id:filename})
    const result=compileTemplate({source:descriptor.template.content,filename,id:filename,compilerOptions:{bindingMetadata:script.bindings}})
    assert.deepEqual(result.errors,[])
  }
})

test('variable tags reuse execution scene layout and stable global palette colors',()=>{
  const h=tagHarness('VariableTagCell','names,options,colors',{
    props:{tags:['文昂租户','事件回调','文昂租户','  ']},
    modules:{'@/store/modules/get-enum':{useEnum:()=>({colors:['blue','gold','green','purple']})}},
  })
  assert.deepEqual(h.names.value,['文昂租户','事件回调'])
  const before=new Map(h.options.value.map((option,index)=>[option.key,h.colors.value[index]]))
  h.props.tags=['其他分类','事件回调','文昂租户']
  h.options.value.forEach((option,index)=>{
    assert.ok(['blue','gold','green','purple'].includes(h.colors.value[index]))
    if(before.has(option.key)) assert.equal(h.colors.value[index],before.get(option.key))
  })
  const source=readFileSync(`${base}/VariableTagCell.vue`,'utf8')
  assert.match(source,/<ExecutionSceneTagGrid/)
  assert.match(source,/:max-visible-tags="3"/)
  assert.match(source,/查看更多分类标签/)
  assert.doesNotMatch(source,/<a-space|<a-tag/)
  h.close()
})

test('shared tag grid bounds categories to two rows and keeps scene defaults unchanged',()=>{
  const filename=path.resolve('src/components/display/ExecutionSceneTagGrid.vue')
  const h=harness('ExecutionSceneTagGrid','visibleValues,hasOverflow,tooltipContent',{
    filename,props:{values:[],maxVisibleTags:3},
  })
  for(const count of [0,1,2,3,4,20]) {
    h.props.values=Array.from({length:count},(_,index)=>`分类${index+1}`)
    assert.equal(h.visibleValues.value.length,Math.min(count,3))
    assert.equal(h.hasOverflow.value,count>3)
    assert.equal(h.tooltipContent.value,h.props.values.join('、'))
  }
  h.props.maxVisibleTags=4
  h.props.values=['a','b','c','d']
  assert.equal(h.visibleValues.value.length,4)
  assert.equal(h.hasOverflow.value,false)
  h.close()
})
