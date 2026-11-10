import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
import { harness, flush } from './case-details-harness.mjs'

export const uiAuthBase = path.resolve('src/views/uitest/auth-config')
const latest = {}
new Function('exports',ts.transpileModule(readFileSync('src/hooks/use-latest-request.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText)(latest)
export const uiAuthRecord = (values = {}) => ({ id:0,name:'Example auth',project_product:{id:0,name:'Product'},test_env:0,auth_type:0,status:1,page_step:{id:0,name:'Login steps'},time_task:{id:0,name:'Daily'},notice_group:{id:0,name:'Notice'},refresh_mode:0,token_ttl:1440,expire_notice_minutes:30,
  manual_config:{cookies:[],local_storage:[],session_storage:[],headers:{example:'value'}},auto_auth_config:{url:'https://example.com',timeout:300},api_config:{api_info:0,token_path:'$.response.json.token'},cache_data:{extra:'omit'},update_time:'2026-11-09',...values })
export function setupUiAuthEditor(overrides = {}) {
  const previous=globalThis.document,doc=Object.assign(new EventTarget(),{visibilityState:'visible'});globalThis.document=doc
  const callbacks={mount:[],activate:[],deactivate:[],unmount:[]},reads=[],writes=[],messages=[]
  const route=vue.reactive({path:'/uitest/auth-config/index',fullPath:'/uitest/auth-config/index'})
  const user=vue.reactive({userId:1,roleId:2,token:'example-session',selected_environment:0}),permission=vue.reactive({permissionKeys:['uitest.auth-config:read']})
  const enumStore=vue.reactive({environment_type:[{key:0,title:'Test'}],ui_auth_type:[0,1,2,3,4].map(key=>({key,title:`Type ${key}`})),ui_auth_refresh_mode:[0,1,2].map(key=>({key,title:`Mode ${key}`})),getEnum:overrides.getEnum|| (async()=>{})})
  const api=Object.fromEntries(Object.entries({
    getUiSteps:overrides.getUiSteps|| (async()=>({code:200,data:[]})),
    getApiInfoOptions:overrides.getApiInfoOptions|| (async()=>[{id:0,name:'Login API',url:'/login'}]),
    getSystemTimingList:overrides.getSystemTimingList|| (async()=>({code:200,data:[]})),
    getSystemNoticeName:overrides.getSystemNoticeName|| (async()=>({code:200,data:[{value:0,label:'Current notice'}]})),
    postUiAuthConfig:overrides.postUiAuthConfig|| (async()=>({code:200})),putUiAuthConfig:overrides.putUiAuthConfig|| (async()=>({code:200})),
  }).map(([name,fn])=>[name,(...args)=>{(name.startsWith('get')?reads:writes).push([name,...args]);return fn(...args)}]))
  const h=harness('UiAuthEditorDialog','form,json,editorVisible,editingId,saving,saveError,formRef,jsonKind,jsonVisible,jsonText,locked,pages,apis,timings,notices,enumsLoading,enumsError,pageStepOptions,apiInfoOptions,timeTaskOptions,noticeOptions,enabledAuthTypeOptions,refreshModeOptions,productSelection,optionErrors,openCreate,openEdit,loadEnums,loadPageSteps,loadApiInfoList,loadTimeTaskList,loadNoticeList,onFormProjectProductChange,onAuthTypeChange,onRefreshModeChange,openJson,saveJson,onSubmit,closeEditor:close',{base:uiAuthBase,api,modules:{
    vue:{...vue,onMounted:fn=>callbacks.mount.push(fn),onActivated:fn=>callbacks.activate.push(fn),onDeactivated:fn=>callbacks.deactivate.push(fn),onBeforeUnmount:fn=>callbacks.unmount.push(fn)},
    '@/hooks/use-latest-request':latest,'vue-router':{useRoute:()=>route},'@/store/modules/user':{default:()=>user},'@/store/modules/permission':{default:()=>permission},'@/store/modules/get-enum':{useEnum:()=>enumStore},
    '@arco-design/web-vue':{Message:Object.fromEntries(['success','error'].map(key=>[key,value=>messages.push([key,value])]))},
  }})
  return {...h,reads,writes,messages,route,user,permission,enumStore,callbacks,mount(){callbacks.mount.forEach(fn=>fn())},visibility(value){doc.visibilityState=value;doc.dispatchEvent(new Event('visibilitychange'))},close(){callbacks.unmount.forEach(fn=>fn());h.close();globalThis.document=previous}}
}
export async function readyUiAuth(h, values = {}) { await h.openEdit(uiAuthRecord(values));await flush() }
