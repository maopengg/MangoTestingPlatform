import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import ts from 'typescript'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8')
const modal = read('../src/components/overlays/TestExecutionModal.vue')
test('batch execution offers all three versions and shared modal compiles', () => {
  const { descriptor } = parse(modal)
  const script = compileScript(descriptor, { id: 'batch-version' })
  const output = compileTemplate({ source: descriptor.template.content, filename: 'TestExecutionModal.vue', id: 'batch-version', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(output.errors, [])
  for (const value of ['editing', 'prepublished', 'published']) assert.ok(modal.includes(`value="${value}"`))
  assert.match(modal, /预发布固定待审核修订/)
  assert.match(read('../src/api/apitest/case.ts'), /'editing' \| 'prepublished' \| 'published'/)
})
test('page submits prepublished and blocks missing candidates without a fallback', async () => {
  const source = parse(read('../src/views/apitest/case/index.vue')).descriptor.scriptSetup.content
  const ast = ts.createSourceFile('case.ts', source, ts.ScriptTarget.Latest, true)
  const fn = ast.statements.find(n => ts.isFunctionDeclaration(n) && n.name.text === 'onConfirmCaseBatchRun')
  const js = ts.transpileModule(fn.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const writes = [], warnings = [], rows = [{ id: 1, name: '待审核', prepublished_revision_id: 101 }]
  const run = new Function('pendingBatchRunCaseIds', 'pendingBatchRows', 'pageVersion', 'pageActive', 'Message', 'batchRunModalRef', 'caseRunning', 'postApiCaseBatchRun', 'doRefresh', 'hasPublishedCaseVersion', js + ';return onConfirmCaseBatchRun')(
    { value: [1] }, {value: rows}, 1, {value:true}, { warning: s => warnings.push(s), error: () => {}, success: () => {} },
    { value: { setConfirmLoading: () => {}, close: () => {} } }, { value: false },
    async (...args) => { writes.push(args); return { data: {} } }, () => {}, () => false)
  rows[0].prepublished_revision_id = null
  await run({ executionName: 'candidate', testEnv: 0, executionVersion: 'prepublished' })
  assert.equal(writes.length, 0)
  assert.match(warnings[0], /1-待审核/)
  rows[0].prepublished_revision_id = 101
  await run({ executionName: 'candidate', testEnv: 0, executionVersion: 'prepublished' })
  assert.equal(writes[0][4], 'prepublished')
})

const ready = (id, changes={}) => ({id,name:`Case ${id}`,status:1,publication_status:'unpublished',
  has_product_owner:true,prepublished_revision_id:null,published_revision_id:null,published_release_id:null,
  has_unpublished_changes:false,update_time:'2026-11-17 10:00:00',...changes})
function submission(rows=[ready(1),ready(2)], overrides={}) {
  const source=parse(read('../src/views/apitest/case/index.vue')).descriptor.scriptSetup.content
  const ast=ts.createSourceFile('case.ts',source,ts.ScriptTarget.Latest,true)
  const names=['hasPublishedCaseVersion','canSubmitCasePrepublication','batchPrepublicationWarning',
    'generateAndSubmitPrepublication','batchSubmitPrepublication']
  const code=ast.statements.filter(node=>ts.isFunctionDeclaration(node)&&names.includes(node.name.text))
    .map(node=>ts.transpileModule(node.getText(ast),{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText).join('\n')
  const writes=[],messages=[],dialogs=[],selection={value:rows.map(row=>row.id)},pending={value:null},active={value:true}
  const table={dataList:rows}, user={userId:1,roleId:1,token:'fixture',selected_environment:0}, pagination={page:1,pageSize:20}
  let refreshes=0
  const context={publicationActionCaseId:{value:null},batchPublicationAction:pending,selectedRowKeys:selection,table,
    Message:Object.fromEntries(['warning','success','error'].map(kind=>[kind,text=>messages.push([kind,text])])),
    Modal:{confirm:options=>dialogs.push(options)},pageActive:active,getFormItems:()=>({}),conditionItems:[],
    sidebarModuleIds:{value:[]},activePublicationStatus:{value:'unpublished'},pagination,userStore:user,
    createApiCaseRevision:async payload=>{writes.push(['revision',payload.case_id]);return overrides.create?overrides.create(payload):{data:{id:100+payload.case_id}}},
    submitApiCasePrepublication:async(id,revision)=>{writes.push(['submit',id,revision]);return overrides.submit?.(id,revision)},
    doRefresh:async()=>{refreshes++}}
  const invoke=new Function(...Object.keys(context),'let pageVersion=1;'+code+';return batchSubmitPrepublication')(...Object.values(context))
  return {invoke,writes,messages,dialogs,selection,pending,active,table,user,pagination,refreshes:()=>refreshes}
}

test('API batch submission freezes selected IDs, creates exact revisions and submits only prepublication',async()=>{
  const h=submission();h.invoke();h.selection.value=[2]
  assert.equal(h.writes.length,0)
  assert.match(h.dialogs[0].content,/2 个用例/)
  assert.equal(await h.dialogs[0].onBeforeOk(),true)
  assert.deepEqual(h.writes,[['revision',1],['submit',1,101],['revision',2],['submit',2,102]])
  assert.deepEqual(h.selection.value,[]);assert.equal(h.pending.value,null);assert.equal(h.refreshes(),1)
})

test('API batch rejects empty selection, old candidates, failed cases, unchanged releases and missing owners before writes',()=>{
  for(const [rows,pattern] of [
    [[],/请选择/],[[ready(1,{prepublished_revision_id:9})],/旧候选/],
    [[ready(1,{status:0})],/执行通过/],[[ready(1,{has_product_owner:false})],/负责人/],
    [[ready(1,{publication_status:'published',published_release_id:1,published_revision_id:1})],/无需重复提交/],
  ]) {
    const h=submission(rows);h.invoke();assert.equal(h.dialogs.length,0);assert.equal(h.writes.length,0)
    assert.match(h.messages[0][1],pattern)
  }
})

test('API batch supports a changed published case like single submission and preserves failed selections',async()=>{
  const h=submission([ready(1,{publication_status:'published',published_release_id:1,published_revision_id:1,has_unpublished_changes:true}),ready(2),ready(3)],
    {submit:async id=>{if(id===2)throw Error('rejected')}})
  h.invoke();await h.dialogs[0].onBeforeOk()
  assert.deepEqual(h.selection.value,[2]);assert.match(h.messages.at(-1)[1],/成功 2 条，失败 1 条/)
  assert.equal(h.writes.length,6)
})

test('API batch rejects changed rows and duplicate confirmation, ignores stale results and stops after cancellation',async()=>{
  const changed=submission();changed.invoke();changed.table.dataList[0].status=0
  assert.equal(await changed.dialogs[0].onBeforeOk(),false);assert.equal(changed.writes.length,0)
  const pending=deferred(),h=submission(undefined,{create:()=>pending.promise})
  h.invoke();const saving=h.dialogs[0].onBeforeOk();await flush()
  assert.equal(h.pending.value,'submit');assert.equal(await h.dialogs[0].onBeforeOk(),false)
  h.dialogs[0].onCancel();pending.resolve({data:{id:101}});await saving
  assert.deepEqual(h.writes,[['revision',1]]);assert.equal(h.pending.value,null);assert.equal(h.refreshes(),0)
})

test('API batch cannot continue submitting to a changed user or page scope',async()=>{
  const pending=deferred(),h=submission(undefined,{submit:()=>pending.promise})
  h.invoke();const saving=h.dialogs[0].onBeforeOk();await flush()
  h.user.roleId=2;pending.resolve({code:200});await saving
  assert.deepEqual(h.writes,[['revision',1],['submit',1,101]])
  assert.equal(h.messages.length,0);assert.equal(h.refreshes(),0)
})

test('API and UI expose compact batch submission buttons separately from approval',()=>{
  for(const domain of ['apitest','uitest']) {
    const source=read(`../src/views/${domain}/case/index.vue`)
    const {descriptor}=parse(source)
    const button=descriptor.template.content.match(/<a-button\b[\s\S]*?<\/a-button>/g)
      .find(button=>button.includes('>批量预发布'))
    assert.match(button,/size="small"/);assert.match(button,/:loading=/);assert.match(button,/:disabled=/)
  }
})
