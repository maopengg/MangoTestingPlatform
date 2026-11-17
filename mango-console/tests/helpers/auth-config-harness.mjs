import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { parse } from '@vue/compiler-sfc'
import * as vue from 'vue'

const base = 'src/views/apitest/auth-config/'
const compile = text => ts.transpileModule(text, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
export function loadModule(file, mocks = {}) {
  const exports = {}
  new Function('exports', 'require', compile(readFileSync(file, 'utf8')))(exports, id => {
    if (id in mocks) return mocks[id]
    if (id === '@/utils/api-response') return loadModule('src/utils/api-response.ts')
    if (id === '@/utils/load-error') return loadModule('src/utils/load-error.ts', {
      '@arco-design/web-vue': { Message: { error() {}, ...mocks['@arco-design/web-vue']?.Message } },
    })
    if (id === 'vue') return vue
    throw new Error(`Unmocked import: ${id}`)
  })
  return exports
}
const utils = loadModule('src/utils/search-condition.ts')
export const { getFormItems } = loadModule('src/utils/datacleaning.ts')
export const form = loadModule(base + 'auth-form.ts')
export const messages = []
export const config = loadModule(base + 'config.ts', {
  '@/utils/search-condition': utils,
  '@/utils/id-search': { createIdSearchValue: () => '' },
  '@arco-design/web-vue': { Message: { error: message => messages.push(message) } },
  '@/hooks/table': { useTableIndexColumn: () => ({ width: 100, key: 'index' }), useTableColumn: columns => columns },
  '@/utils/update-user': { createUpdateUserCondition: () => ({ key: 'update_user', type: 'select', value: [] }), updateUserColumn: () => ({ width: 110 }) },
})
export const record = (overrides = {}) => ({
  id: 1, name: 'Example auth', project_product: { id: 2, name: 'Example product' }, test_env: 0,
  auth_type: 0, api_info: { id: 3, name: 'Login' }, custom_code: null,
  target_address: '', public_variable_ids: [7], refresh_mode: 0, token_ttl: 1440,
  refresh_margin: 10, expire_notice_minutes: 30, time_task: null, notice_group: null,
  status: 1, last_refresh_status: 1, ...overrides,
})
export function deferred() { let resolve, reject; const promise = new Promise((a,b) => {resolve=a;reject=b}); return {promise,resolve,reject} }
export async function flush() { for (let i=0;i<5;i++) await Promise.resolve() }

export function component(name, bindings, mocks = {}) {
  const events = [], cleanup = []
  let handle
  const source = parse(readFileSync(base + (name === 'index' ? 'index.vue' : 'components/' + name + '.vue'), 'utf8')).descriptor.scriptSetup.content
  const api = new Proxy(mocks.api || {}, { get: (target, key) => target[key] || (async () => ({ data: [], msg: 'ok', code: 200 })) })
  const modules = {
    vue: { ...vue, onMounted: () => {}, onActivated: () => {}, onBeforeUnmount: fn => cleanup.push(fn), onDeactivated: fn => cleanup.push(fn) },
    '@arco-design/web-vue': { Message: { error: message => messages.push(message), success: () => {} }, Modal: mocks.Modal },
    'vue-router': { useRoute: () => ({path:'/apitest/auth-config/index',query:{}}) },
    '@/hooks/table': {
      useTable: () => ({dataList:vue.shallowReactive([]),tableLoading:vue.ref(false),handleSuccess(response){this.dataList.splice(0,this.dataList.length,...response.data)}}),
      usePagination: () => ({page:1,pageSize:20,setTotalSize(){}}),
      useRowKey: key => key,
      useRowSelection: () => ({selectedRowKeys:vue.ref([]),showCheckedAll:vue.ref(true),onSelectionChange(){}}),
    },
    '@/hooks/use-latest-request': loadModule('src/hooks/use-latest-request.ts'),
    '@/utils/datacleaning': {getFormItems},
    '@/utils/status-color': {AUTH_REFRESH_STATUS_COLORS:{},getStatusTagColor:()=>''},
    '@/store/modules/get-enum': { useEnum: () => ({}) },
    '@/store/modules/user': { default: () => ({ selected_environment: 0 }) },
    '@/setting': { fieldNames: { label: 'title', value: 'key' } },
    '@/utils/business-format': { getOptionId: value => Array.isArray(value) ? value.at(-1) : value },
    '@/api/apitest/info': { getApiInfoOptions: mocks.getApiInfoOptions || (async () => []) },
    '@/api/system/time': { getSystemTimingList: mocks.getSystemTimingList || (async () => ({ data: [] })) },
    '@/api/system/notice_group': { getSystemNoticeName: mocks.getSystemNoticeName || (async () => ({ data: [] })) },
    '@/api/apitest/auth-config': api,
    '@/api/user/user': {getUserName:async()=>({data:[]})},
    '../config': config,
    './config': config,
    '../auth-form': form,
    '@/utils/load-error': loadModule('src/utils/load-error.ts', {
      '@arco-design/web-vue': { Message: { error: message => messages.push(message) } },
    }),
  }
  const exports = {}
  const result = new Function('exports','require','defineEmits','defineExpose',compile(source) + `;return {${bindings}}`)(
    exports, id => id.endsWith('.vue') ? {} : modules[id] ?? (() => { throw new Error(`Unmocked import ${id}`) })(),
    () => (...args) => events.push(args), value => {handle=value},
  )
  return { ...result, handle, events, cleanup: () => cleanup.forEach(fn=>fn()) }
}
