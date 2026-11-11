import { readFileSync } from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import * as vue from 'vue'
import { parse } from '@vue/compiler-sfc'
const base = path.resolve('src/views/apitest/case/details')
const compile = source => ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText
export function deferred() { let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject} }
export async function flush() { for(let i=0;i<8;i++) await Promise.resolve();await vue.nextTick() }
export function harness(name, bindings, overrides={}) {
  const componentBase = overrides.base || base
  const events=[], cleanup=[]
  const props=vue.reactive({caseId:1,projectProductId:2,editLocked:false,stepCount:0,resultId:1,...overrides.props})
  let exposed
  const api=new Proxy(overrides.api||{}, {get:(o,k)=>o[k]|| (async()=>({data:[],msg:'ok',code:200}))})
  const modules={
    vue:{...vue,onBeforeUnmount:fn=>cleanup.push(fn),onDeactivated:fn=>cleanup.push(fn),onScopeDispose:fn=>cleanup.push(fn),onMounted:()=>{},onActivated:()=>{}},
    '@arco-design/web-vue':{Message:{success(){},error(){},warning(){},info(){}},Modal:overrides.Modal||{confirm(){}}},
    '@/utils/form':{isValidInteger:v=>Number.isInteger(Number(v))&&Number(v)>=0},
    '@/setting':{fieldNames:{label:'title',value:'key'}},
    '@/store/modules/get-enum':{useEnum:()=>({})},
    '@/store/modules/user':{default:()=>({})},
    '@/hooks/useDisplayDensity':{scaleDensityPixels:v=>v},
    '@/utils/lossless-json':{cloneLosslessJson:v=>v==null?v:JSON.parse(JSON.stringify(v))},
    ...overrides.modules,
  }
  const cache=new Map()
  function load(file) {
    if(cache.has(file))return cache.get(file)
    const exports={};cache.set(file,exports)
    const source=readFileSync(file,'utf8')
    new Function('exports','require',compile(source))(exports,id=>resolve(id,path.dirname(file)))
    return exports
  }
  function resolve(id,dir=base) {
    if(id in modules) {
      if (id === '@arco-design/web-vue') return { ...modules[id], Message: { error() {}, ...modules[id].Message } }
      return modules[id]
    }
    if(id.endsWith('.vue'))return {}
    if(id.startsWith('@/api/'))return api
    if(id.startsWith('.'))return load(path.resolve(dir,id)+'.ts')
    if(id.startsWith('@/utils/') || id.startsWith('@/types/') || id.startsWith('@/hooks/') || id.startsWith('@/components/business/') || id.startsWith('@/views/'))return load(path.resolve('src',id.slice(2))+'.ts')
    throw Error('Unmocked dependency '+id)
  }
  const filename=overrides.filename ?? (name === 'index' ? path.join(componentBase,'index.vue') : path.join(componentBase,'components',name+'.vue'))
  const scriptSource=parse(readFileSync(filename,'utf8')).descriptor.scriptSetup.content
  const source=overrides.transformSource ? overrides.transformSource(scriptSource) : scriptSource
  const scope=vue.effectScope()
  const result=scope.run(()=>new Function('exports','require','defineProps','withDefaults','defineEmits','defineExpose',compile(source)+`;return {${bindings}}`)(
    {},id=>resolve(id,path.dirname(filename)),()=>props,(p,d)=>{for(const[k,v]of Object.entries(d))if(!(k in p))p[k]=typeof v==='function'?v():v;return p},
    ()=>(...event)=>events.push(event),value=>{exposed=value},
  ))
  return {...result,props,events,exposed,close:()=>{cleanup.forEach(f=>f());scope.stop()},load:relative=>load(path.join(componentBase,relative))}
}
export function method(name,dependencies,filename=path.join(base,'index.vue')) {
  const feedback = {}
  new Function('exports', 'require', compile(readFileSync('src/utils/load-error.ts', 'utf8')))(feedback, () => ({ Message: { error() {}, ...dependencies.Message } }))
  dependencies = { ...feedback, ...dependencies }
  const source=parse(readFileSync(filename,'utf8')).descriptor.scriptSetup.content
  const tree=ts.createSourceFile('index.ts',source,ts.ScriptTarget.Latest,true)
  const node=tree.statements.find(n=>(ts.isFunctionDeclaration(n)&&n.name?.text===name)||
    (ts.isVariableStatement(n)&&n.declarationList.declarations.some(d=>d.name.getText(tree)===name)))
  const injected=Object.keys(dependencies)
  return new Function(...injected,compile(node.getText(tree))+`;return ${name}`)(...injected.map(k=>dependencies[k]))
}
export const step={id:10,case:1,api_info:{id:20,name:'Example',protocol_type:'http'},execution_config:{is_recovery:false}}
export const scenario=(values={})=>({id:11,name:'Example scenario',front_sql:[],posterior_sql:[],posterior_response:[],posterior_response_text:[],ass_general:[],ass_jsonpath:[],ass_sql:[],headers:[],...values})
