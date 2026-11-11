import { createApp, defineComponent, h, onMounted, ref } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import '@arco-design/web-vue/dist/arco.css'
import '@/styles'
import { setupPinia } from '@/store/pinia'
import { setupGlobalComponent } from '@/layouts'
import { applyDisplayDensity } from '@/hooks/useDisplayDensity'
import { DisplayDensity } from '@/store/types'
import { applyThemePreset } from '@/theme/presets'
import request from '@/api/axios.config'
import { useEnum } from '@/store/modules/get-enum'
import ApiInfoBoundCases from '@/views/apitest/info/components/ApiInfoBoundCases.vue'

// 隔离的本地预览，所有网络请求均返回模拟数据，不读取或修改真实用例。
request.defaults.adapter = async config => ({
  data: { code: 200, msg: '本地模拟数据', data: [], totalSize: 0 },
  status: 200, statusText: 'OK', headers: {}, config,
})
const query = new URLSearchParams(location.search)
const items = Array.from({ length: Number(query.get('count') || 57) }, (_, index) => ({
  case_id: 4000 + index,
  case_name: `示例用例 ${index + 1}：模板配置更新后的引用、文件和分类数据校验`,
  case_people_name: '示例负责人',
  scenario_tags: index % 3 === 0 ? [0, 1, 2, 3, 4] : index % 2 === 0 ? [0, 2] : [1],
  update_user_name: '示例更新人',
  update_time: '2026-11-11 10:20:30',
  project_product_id: 1,
}))
const app = createApp(defineComponent({
  setup() {
    const panel = ref<InstanceType<typeof ApiInfoBoundCases> | null>(null)
    onMounted(() => panel.value?.open({ id: 1, name: '示例模板：分类表单与文件引用' }))
    return () => h(ApiInfoBoundCases, {
      ref: panel,
      referenceMode: true,
      readCases: async (_id: number | string, page: number, pageSize: number) => ({
        data: items.slice((page - 1) * pageSize, page * pageSize), totalSize: items.length,
      }),
    })
  },
}))
setupPinia(app)
useEnum().api_case_scenario_tag = [
  { key: 0, title: '回归测试' }, { key: 1, title: '冒烟测试' }, { key: 2, title: '数据校验' },
  { key: 3, title: '边界校验' }, { key: 4, title: '异常校验' },
]
setupGlobalComponent(app)
app.use(createRouter({ history: createWebHashHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] }))
applyDisplayDensity(DisplayDensity.AUTO)
applyThemePreset(query.get('theme') || 'mango-blue')
window.addEventListener('resize', () => applyDisplayDensity(DisplayDensity.AUTO))
app.mount('#app')
