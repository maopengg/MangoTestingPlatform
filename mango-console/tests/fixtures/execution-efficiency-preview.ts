// Local visual fixture: all requests are intercepted; no real reports, workers or credentials are used.
import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import '@arco-design/web-vue/dist/arco.css'
import '@/styles'
import { setupPinia } from '@/store/pinia'
import { setupGlobalComponent } from '@/layouts'
import { applyDisplayDensity } from '@/hooks/useDisplayDensity'
import { DisplayDensity } from '@/store/types'
import request from '@/api/axios.config'
import EfficiencyPage from '@/views/report/execution-efficiency/index.vue'
import { applyThemePreset } from '@/theme/presets'

const product = { id: 1, name: '示例产品', project: { name: '示例项目' } }
const module = { id: 1, full_path: '基础能力/资源管理' }
const reports = Array.from({ length: 24 }, (_, index) => ({
  id: index + 1, report_id: index + 1, name: `示例串行任务 ${index + 1}`, test_env: 1,
  project_product: product, module, api_concurrency_limit: 1, effective_api_limit: 1,
  pending: 287 - index, running: 1, completed: 119, longest_wait_ms: 640000 + index * 1000,
  diagnosis: '报告并发限制', current_case: { case_name: '等待异步资源清理', elapsed_ms: 262000,
    stage: '执行响应后置处理', stage_elapsed_ms: 260000 },
}))
request.defaults.adapter = async config => {
  let data: any = []
  if (String(config.url).includes('execution-efficiency/options')) {
    data = { items: [{ id: 1, name: '示例定时任务' }], has_more: false }
  } else if (String(config.url).includes('execution-efficiency')) {
    const section = config.params?.section
    if (section === 'timing') data = {
      summary: { completed: 410, sample_count: 411, covered_completed: 405, api_completed: 407,
        p50_ms: 1520, p95_ms: 262000, retry_count: 6, retry_duration_ms: 12500 },
      phases: [{ name: '前置处理', duration_ms: 18000 }, { name: '接口请求', duration_ms: 85300 },
        { name: '后置处理', duration_ms: 262000 }, { name: '结果回写', duration_ms: 3000 }],
      trend: Array.from({ length: 8 }, (_, index) => ({ time: `2026-01-01 ${10 + index}:00`, completed: 40 + index * 3, p50_ms: 1500, p95_ms: 8000 + index * 30000 })),
      basic: [{ type: 0, name: 'UI', total: 3, completed: 3, pending: 0, running: 0 },
        { type: 1, name: 'API', total: 408, completed: 407, pending: 0, running: 1 },
        { type: 2, name: 'Pytest', total: 0, completed: 0, pending: 0, running: 0 }],
      slow_cases: [{ trace_id: 'example', report_id: 1, detail_id: 1, case_name: '等待异步资源清理', duration_ms: 262000, dominant_phase: '后置处理', project_product: product, module }],
      slow_reports: [{ report_id: 1, name: '示例串行任务', observed_span_ms: 1440000, first_start_delay_ms: 1200, running: true, project_product: product, module }],
    }
    else {
      const rows = section === 'anomalies' ? [{ ...reports[0], case_name: '示例结果回写不一致', report_name: '示例串行任务',
        reason: '执行链路已结束，报告执行项仍显示执行中', stage: '结果回写', elapsed_ms: 362000 }] : reports
      const page = Number(config.params?.page || 1), size = Number(config.params?.page_size || 20)
      data = { items: rows.slice((page - 1) * size, page * size), count: rows.length,
        summary: { pending: 287, running: 1, report_count: 24, anomaly_count: 1, longest_wait_ms: 640000 },
        workers: { online: 2, capacity: 10, running: 1 }, as_of: '2026-01-01T10:12:00' }
    }
  } else if (String(config.url).includes('enum')) data = { environment_type: [{ key: 1, title: '示例环境' }] }
  return { data: { code: 200, msg: '本地模拟数据', data }, status: 200, statusText: 'OK', headers: {}, config }
}
const app = createApp(EfficiencyPage)
setupPinia(app)
setupGlobalComponent(app)
app.use(createRouter({ history: createWebHashHistory(), routes: [{ path: '/:pathMatch(.*)*', component: EfficiencyPage }] }))
applyDisplayDensity(DisplayDensity.AUTO)
applyThemePreset(new URLSearchParams(window.location.search).get('theme') || 'mango-blue')
window.addEventListener('resize', () => applyDisplayDensity(DisplayDensity.AUTO))
app.mount('#app')
