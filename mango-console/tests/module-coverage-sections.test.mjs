import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { reactive } from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

function setup(t) {
  const previousWindow = globalThis.window
  globalThis.window = { removeEventListener() {} }
  const inventoryRequests=[],moduleRequests=[]
  const state=harness('CoverageOverview',
    'inventory,inventoryLoading,modules,modulesLoading,pagination,keyword,gapFilter,searchModules', {
      base:path.resolve('src/views/apitest/module-coverage'),
      props:{loading:true,error:false,scope:{project_product:3},refreshKey:1},
      api:{
        getCoverageInventory:params=>{const task=deferred();inventoryRequests.push({params,task});return task.promise},
        getCoverageModuleProgress:params=>{const task=deferred();moduleRequests.push({params,task});return task.promise},
      },
      modules:{
        'echarts/core':{use(){},dispose(){}},'echarts/components':{TitleComponent:{}},
        '@/hooks/useEcharts':{default(){}},
        '@/hooks/table':{usePagination:callback=>reactive({page:1,pageSize:20,pageCount:0,
          onChange:callback,setTotalSize(value){this.pageCount=value}})},
      },
    })
  t.after(()=>{state.close();globalThis.window=previousWindow})
  return {...state,inventoryRequests,moduleRequests}
}
const inventoryResult={data:{project_inventory_summary:{leaf_count:50,inventoried_count:30,uninventoried_count:20,inventory_rate:60}}}
const moduleResult=(id,count=50)=>({data:{items:[{id}],count,page:1,page_size:20}})

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
  assert.deepEqual(state.moduleRequests[1].params,{project_product:3,page:2,pageSize:10,keyword:'',progress:'all'})
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
  state.pagination.page=3;state.keyword.value=' 审查 ';state.gapFilter.value='analysis_gap';await flush()
  assert.equal(state.moduleRequests[1].params.page,1)
  assert.equal(state.moduleRequests[1].params.keyword,'审查')
  assert.equal(state.moduleRequests[1].params.progress,'analysis_gap')
  assert.equal(state.inventoryRequests.length,1)
})
