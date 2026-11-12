import { createApp, h, ref } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import '@arco-design/web-vue/dist/arco.css'
import '@/styles'
import { setupPinia } from '@/store/pinia'
import { setupGlobalComponent } from '@/layouts'
import { applyDisplayDensity } from '@/hooks/useDisplayDensity'
import { DisplayDensity } from '@/store/types'
import request from '@/api/axios.config'
import StatusChart from '@/components/chart/StatusChart.vue'
import PieChart from '@/components/chart/PieChart.vue'
import ReportTrendChart from '@/views/report/components/ReportTrendChart.vue'
import ProjectQualityChart from '@/views/index/components/chart/ProjectQualityChart.vue'
import Orchestration from '@/views/apitest/case/details/components/ApiCaseOrchestrationPanel.vue'
import StepTable from '@/views/apitest/case/details/components/ApiCaseStepTable.vue'
import McpWorkbench from '@/views/index/components/McpWorkbench.vue'
import Footer from '@/layouts/footer/index.vue'

// This fixture never reads or mutates real platform data.
request.defaults.adapter = async config => ({
  data: { code: 200, data: config.url?.includes('api-key') ? { api_key: 'example-fixture-key' } : [], totalSize: 0 },
  status: 200, statusText: 'OK', headers: {}, config,
})
const trend = Array.from({ length: 12 }, (_, index) => ({ label: `10/${index + 1}–10/${index + 7}`,
  batch_count: 10 + index, scheduled_count: 200 + index * 10, other_count: 0,
  success_count: 200, fail_count: 5, warning_count: 0, pass_rate: 97.56 }))
const rows = Array.from({ length: 40 }, (_, index) => ({ id: index + 1, api_info: { id: index + 1, name: `步骤 ${index + 1}` }, status: 1 }))
const columns = [{ title: '接口名称', dataIndex: 'api_name', width: 330 },
  { title: '结果', dataIndex: 'status', width: 100 }, { title: '失败提示', dataIndex: 'error', width: 190 },
  { title: '操作', dataIndex: 'actions', fixed: 'right' as const, width: 140 }]
const Root = { setup() {
  const tab = ref('2')
  const card = (title: string, child: unknown, style = '') => h('section', { class: 'mango-section-card', style }, [h('h2', title), child])
  return () => h('main', { class: 'mango-recovery-fixture' }, [
    h('div', { class: 'mango-recovery-charts' }, [
      card('单一状态', h(StatusChart, { success: 0, fail: 0, warning: 0, pending: 10, todo: 0, stopped: 0, totalLabel: '报告总数', unit: '份' })),
      card('近 7 天执行结果', h(StatusChart, { success: 334562, fail: 2123, warning: 991, other: 4798, centerLabel: '最终通过率', centerValue: '99.07%' })),
      card('自动化类型', h(PieChart, { chartData: [{ name: 'API', value: 100 }, { name: 'UI', value: 40 }] })),
      card('项目自动化质量', h(ProjectQualityChart, { data: [{ project_id: 1, project_name: '示例项目', report_count: 6700, success_count: 6500, fail_count: 150, warning_count: 50, other_count: 0, pass_rate: 97 }] })),
    ]),
    h('div', { class: 'mango-recovery-workbench' }, [
      h(Orchestration, { activeKey: tab.value, stepCount: 40, editLocked: false, showAdd: true, loading: false, onChange: (value: string) => { tab.value = value } }, {
        steps: () => h(StepTable, { columns, data: rows, loading: false, editLocked: false, executionActive: false, statusText: () => '通过', statusColor: () => 'green', getApiInfoId: (row: { id: number }) => row.id }),
        preparation: () => h('div', '前置准备'), cleanup: () => h('div', '后置清理'),
      }),
      card('近 12 周执行报告趋势', h(ReportTrendChart, { items: trend })),
      card('MCP 智能接入', h(McpWorkbench, { compact: true })),
    ]), h(Footer),
  ])
} }
const app = createApp(Root)
setupPinia(app)
const router = createRouter({ history: createWebHashHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
app.use(router)
setupGlobalComponent(app)
applyDisplayDensity(DisplayDensity.AUTO)
void router.isReady().then(() => app.mount('#app'))
const style = document.createElement('style')
style.textContent = `body { margin: 0; } .mango-recovery-fixture { padding: 12px; height: 100vh; display: flex; flex-direction: column; gap: 12px; box-sizing: border-box; }
 .mango-recovery-charts { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 12px; height: 32vh; }
 .mango-recovery-fixture .mango-section-card { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
 .mango-recovery-fixture h2 { flex: none; font-size: 16px; margin: 0 0 10px; }
 .mango-recovery-fixture .mango-section-card > div { flex: 1; min-height: 0; }
 .mango-recovery-workbench { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(0, 1.1fr) minmax(260px, .7fr); gap: 12px; }`
document.head.appendChild(style)
