// Isolated visual fixture; every request is intercepted, with no real identities or writes.
import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import '@arco-design/web-vue/dist/arco.css'
import '@/styles'
import { setupPinia } from '@/store/pinia'
import { setupGlobalComponent } from '@/layouts'
import { applyDisplayDensity } from '@/hooks/useDisplayDensity'
import { DisplayDensity } from '@/store/types'
import { applyThemePreset } from '@/theme/presets'
import request from '@/api/axios.config'
import RolePage from '@/views/system/role/index.vue'
const endpoint = (index: number, protocol = 'http', fixed = false) => ({
  id: `${protocol}.${index.toString(16).padStart(64, '0')}`, protocol,
  method: protocol === 'http' ? 'GET' : 'MCP', name: protocol === 'http' ? 'get_case_details' : 'get_api_case_detail_full',
  description: '查看用例配置与步骤明细；仅返回当前用户有权限访问的项目数据。',
  urls: protocol === 'http' ? [`/api/api/case/details/${index}`] : [],
  fixed, fixed_enabled: fixed, fixed_reason: fixed ? '基础或共用选项，沿用固定授权规则' : '',
})
request.defaults.adapter = async config => {
  let data: unknown = []
  if (config.url?.endsWith('/user/role/all')) data = [
    { key: 1, title: '业务只读角色', description: '分别配置菜单及 HTTP、MCP 接口授权' },
    { key: 2, title: '自动化维护者', description: '负责用例和任务维护' },
    { key: 3, title: '游客', description: '系统默认，只读' },
  ]
  else if (config.url?.endsWith('/user/role/permission') && config.method === 'put') {
    const body = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
    data = { menu_keys: body.menu_keys, endpoint_permissions: body.endpoint_permissions }
  } else if (config.url?.endsWith('/user/role/permission')) data = {
    tree: [
      { permissionKey: 'index.home', menuName: '首页', children: [] },
      { permissionKey: 'api.case', menuName: '测试用例', children: [] },
      { permissionKey: 'help', menuName: '帮助与规范', children: [
        { permissionKey: 'help.variable', menuName: '公共方法', children: [] },
      ] },
      { permissionKey: '__fixed__', menuName: '其他', displayOnly: true, children: [
        { permissionKey: '__fixed__.public', menuName: '公开登录与下载', displayOnly: true, children: [] },
        { permissionKey: '__fixed__.mcp_base', menuName: 'MCP 基础能力', displayOnly: true, children: [] },
      ] },
    ],
    menu_keys: ['index.home', 'api.case', 'help', 'help.variable'], endpoint_permissions: Number(config.params?.role_id) === 3
      ? Object.fromEntries(Array.from({ length: 24 }, (_, index) => [endpoint(index + 1, index % 2 ? 'mcp' : 'http').id, 'endpoint_allow'])) : {},
    endpoint_groups: [
      { menu_key: 'api.case', endpoints: Array.from({ length: 24 }, (_, index) => endpoint(index + 1, index % 2 ? 'mcp' : 'http')) },
      { menu_key: 'index.home', endpoints: [endpoint(102, 'http', true)] },
      { menu_key: 'help.variable', endpoints: [endpoint(103, 'http', true)] },
      { menu_key: '__fixed__', endpoints: [endpoint(100, 'http', true), endpoint(101, 'mcp', true)] },
      { menu_key: '__fixed__.public', endpoints: [endpoint(100, 'http', true)] },
      { menu_key: '__fixed__.mcp_base', endpoints: [endpoint(101, 'mcp', true)] },
    ],
  }
  return { data: { code: 200, msg: '本地模拟数据', data }, status: 200, statusText: 'OK', headers: {}, config }
}
const app = createApp(RolePage)
setupPinia(app)
setupGlobalComponent(app)
const router = createRouter({ history: createWebHashHistory(), routes: [{ path: '/:pathMatch(.*)*', component: RolePage }] })
app.use(router)
applyDisplayDensity(DisplayDensity.AUTO)
applyThemePreset(new URLSearchParams(window.location.search).get('theme') || 'mango-blue')
window.addEventListener('resize', () => applyDisplayDensity(DisplayDensity.AUTO))
router.isReady().then(() => app.mount('#app'))
