import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { reactive } from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

function setup(t, chart) {
  const previousWindow = globalThis.window
  globalThis.window = { removeEventListener() {}, matchMedia:()=>({matches:false}) }
  const inventoryRequests=[],moduleRequests=[]
  const state=harness('CoverageOverview',
    'inventory,inventoryLoading,modules,modulesLoading,pagination,keyword,progressFilters,searchModules,scanChart,entryChart,render,scanLabel', {
      base:path.resolve('src/views/apitest/module-coverage'),
      props:{loading:true,error:false,scope:{project_product:3},refreshKey:1},
      api:{
        getCoverageInventory:params=>{const task=deferred();inventoryRequests.push({params,task});return task.promise},
        getCoverageModuleProgress:params=>{const task=deferred();moduleRequests.push({params,task});return task.promise},
      },
      modules:{
        'echarts/core':{use(){},dispose(){}},'echarts/components':{TitleComponent:{}},
        '@/hooks/useEcharts':{default(){return chart}},
        '@/hooks/table':{usePagination:callback=>reactive({page:1,pageSize:20,pageCount:0,
          onChange:callback,setTotalSize(value){this.pageCount=value}})},
      },
    })
  t.after(()=>{state.close();globalThis.window=previousWindow})
  return {...state,inventoryRequests,moduleRequests}
}
const inventoryResult={data:{project_inventory_summary:{leaf_count:50,inventoried_count:30,uninventoried_count:20,inventory_rate:60}}}
const moduleResult=(id,count=50)=>({data:{items:[{id}],count,page:1,page_size:20}})

test('inventory review is a distinct chart segment, label and filter, not never inventoried', async t=>{
  const originalDocument=globalThis.document, originalStyle=globalThis.getComputedStyle
  globalThis.document={documentElement:{}}
  globalThis.getComputedStyle=()=>({fontFamily:'sans-serif',getPropertyValue:key=>key})
  t.after(()=>{globalThis.document=originalDocument;globalThis.getComputedStyle=originalStyle})
  const events={};let options
  const state=setup(t,{setOption:value=>{options=value},off(){},on:(name,handler)=>{events[name]=handler}})
  state.inventoryRequests[0].task.resolve({data:{project_inventory_summary:{leaf_count:121,
    inventoried_count:62,inventory_review_count:38,uninventoried_count:21,inventory_rate:51.24}}})
  await flush()
  state.scanChart.value={clientWidth:600}
  state.render()
  assert.deepEqual(options.series[0].data.map(row=>[row.name,row.value]),
    [['已盘点',62],['版本待复核',38],['未盘点',21]])
  assert.equal(new Set(options.color).size,3)
  for(const [dataIndex,filter] of ['inventoried','inventory_review','scan'].entries()){
    events.click({dataIndex})
    assert.deepEqual(state.progressFilters.inventory_progress,[filter])
  }
  assert.equal(state.scanLabel({inventory_status:'review',inventory_scan_ids:[2414]}),
    '版本待复核 · 盘点基线 #2414')
  const groups=state.load('config.ts').overviewFilterGroups
  assert.equal(groups.find(group=>group.key==='inventory_progress').options
    .find(item=>item.value==='inventory_review').label,'版本待复核')
})

test('excluded chart segment has a distinct deferred color and selects its own labeled filter', async t=>{
  const originalDocument=globalThis.document, originalStyle=globalThis.getComputedStyle
  globalThis.document={documentElement:{}}
  globalThis.getComputedStyle=()=>({fontFamily:'sans-serif',getPropertyValue:key=>key})
  t.after(()=>{globalThis.document=originalDocument;globalThis.getComputedStyle=originalStyle})
  const events={};let options
  const state=setup(t,{setOption:value=>{options=value},off(){},on:(name,handler)=>{events[name]=handler}})
  state.props.data={summary:{analyzed_interface_count:2,pending_analysis_count:1,analysis_gap_count:0,
    analysis_review_count:0,deferred_analysis_count:3,excluded_interface_count:4}}
  state.entryChart.value={clientWidth:600}
  state.render()
  assert.notEqual(options.color[4],options.color[5])
  state.progressFilters.coverage_progress=['partial']
  events.click({dataIndex:5})
  assert.deepEqual(state.progressFilters.analysis_progress,['analysis_excluded'])
  assert.deepEqual(state.progressFilters.coverage_progress,['partial'])
  const groups=state.load('config.ts').overviewFilterGroups
  assert.equal(groups.find(group=>group.key==='analysis_progress').options.find(item=>item.value==='analysis_excluded').label,'含已排除接口')
  events.click({dataIndex:4})
  assert.deepEqual(state.progressFilters.analysis_progress,['analysis_deferred'])
})

test('independent progress filters debounce into one query and preserve other dimensions', async t=>{
  const state=setup(t)
  state.moduleRequests[0].task.resolve(moduleResult(1));await flush()
  state.pagination.page=4
  state.progressFilters.analysis_progress=['analysis_excluded']
  state.progressFilters.coverage_progress=['covered','partial']
  state.progressFilters.analysis_progress=['analysis_deferred','analysis_excluded']
  await flush()
  assert.equal(state.moduleRequests.length,1)
  await new Promise(resolve=>setTimeout(resolve,550));await flush()
  assert.equal(state.moduleRequests.length,2)
  assert.equal(state.moduleRequests[1].params.page,1)
  assert.equal(state.moduleRequests[1].params.analysis_progress,'analysis_deferred,analysis_excluded')
  assert.equal(state.moduleRequests[1].params.coverage_progress,'covered,partial')
  assert.equal(state.inventoryRequests.length,1)
  state.moduleRequests[1].task.resolve(moduleResult(2));await flush()
  state.progressFilters.analysis_progress=[]
  await flush()
  await new Promise(resolve=>setTimeout(resolve,550));await flush()
  assert.equal(state.moduleRequests[2].params.analysis_progress,undefined)
  assert.equal(state.moduleRequests[2].params.coverage_progress,'covered,partial')
})

test('inventory and modules start independently of the slow summary and release only their own loading',async t=>{
  const state=setup(t)
  assert.equal(state.inventoryRequests.length,1)
  assert.equal(state.moduleRequests.length,1)
  state.inventoryRequests[0].task.resolve(inventoryResult);await flush()
  assert.equal(state.inventory.value.inventory_rate,60)
  assert.equal(state.inventoryLoading.value,false)
  assert.equal(state.modulesLoading.value,true)
  state.moduleRequests[0].task.resolve(moduleResult(1));await flush()
  assert.equal(state.modulesLoading.value,false)
  assert.equal(state.pagination.pageCount,50)
})

test('module pagination queries only the requested page without reloading inventory or summary',async t=>{
  const state=setup(t)
  state.moduleRequests[0].task.resolve(moduleResult(1));await flush()
  state.pagination.page=2;state.pagination.pageSize=10
  const loading=state.pagination.onChange()
  assert.deepEqual(state.moduleRequests[1].params,{project_product:3,page:2,pageSize:10,keyword:''})
  assert.equal(state.inventoryRequests.length,1)
  state.moduleRequests[1].task.resolve(moduleResult(21));await loading
  assert.deepEqual(state.modules.value.map(item=>item.id),[21])
})

test('scope changes and refresh reject prior responses; failed modules do not discard inventory',async t=>{
  const state=setup(t)
  state.props.scope={project_product:4,module__in:'10,11'};await flush()
  state.inventoryRequests[0].task.resolve(inventoryResult)
  state.moduleRequests[0].task.resolve(moduleResult(99));await flush()
  assert.equal(state.inventory.value,undefined)
  assert.deepEqual(state.modules.value,[])
  state.inventoryRequests[1].task.resolve(inventoryResult)
  state.moduleRequests[1].task.reject(new Error('offline'));await flush()
  assert.equal(state.modulesLoading.value,false)
  assert.equal(state.inventory.value.inventory_rate,60)
  state.props.refreshKey++;await flush()
  assert.equal(state.inventoryRequests.length,3)
  assert.equal(state.moduleRequests[2].params.project_product,4)
  assert.equal(state.moduleRequests[2].params.module__in,'10,11')
  state.close()
  state.inventoryRequests[2].task.resolve(inventoryResult)
  state.moduleRequests[2].task.resolve(moduleResult(88));await flush()
  assert.deepEqual(state.modules.value,[])
})

test('status selection resets the server page and search keyword is submitted on explicit search',async t=>{
  const state=setup(t)
  state.pagination.page=3;state.keyword.value=' 审查 ';state.progressFilters.analysis_progress=['analysis_gap'];await flush()
  await new Promise(resolve=>setTimeout(resolve,550));await flush()
  assert.equal(state.moduleRequests[1].params.page,1)
  assert.equal(state.moduleRequests[1].params.keyword,'审查')
  assert.equal(state.moduleRequests[1].params.analysis_progress,'analysis_gap')
  assert.equal(state.inventoryRequests.length,1)
})
