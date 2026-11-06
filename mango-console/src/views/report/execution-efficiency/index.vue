<template>
  <TableBody plain :sticky-horizontal-scroll="false" class="mango-detail-workbench-page mango-efficiency-page">
    <template #header>
      <TableHeader title="执行效能">
        <template #header-extra>
          <a-space size="small">
            <a-popover title="统计口径" position="bottom" trigger="click">
              <a-button size="small" type="text"><template #icon><IconInfoCircle /></template>统计口径</a-button>
              <template #content>
                <div class="mango-efficiency-help">
                  <p>执行效能衡量平台速度与排队情况，不代表业务通过率。</p>
                  <p>当前排队不受统计时段限制；首次等待从创建时间计算，待重试项缺少准确起点时显示“—”。</p>
                  <p>耗时分析按时段内创建的报告统计。P50/P95包含已结束的API重试尝试，阶段耗时不重复累加嵌套步骤。</p>
                  <p>缺失计时不按0计算；排除统计项仍计入执行成本。异常线索不等于已确认的平台故障。</p>
                </div>
              </template>
            </a-popover>
          </a-space>
        </template>
      </TableHeader>
    </template>
    <ProjectProductNavigationWorkbench
      contained-body show-modules :show-toolbar="false" :reset-key="resetKey"
      :model-value="navigation.projectProduct" :module-value="navigation.module"
      @filter-change="onNavigation" @search="search" @reset-search="reset"
    >
      <template #search>
        <a-form layout="inline" :model="{}" @submit.prevent="search">
          <a-form-item v-for="item in conditions" :key="item.key" :label="item.label">
            <a-select v-if="item.type === 'select'" v-model="item.value" :multiple="item.multiple"
              :max-tag-count="1" :options="options(item.key)" allow-search allow-clear
              :loading="optionState[item.key]?.loading || false"
              :filter-option="isTaskOption(item.key) ? false : undefined"
              :placeholder="`请选择${item.label}`"
              @popup-visible-change="(visible: boolean) => visible && openOptions(item.key)"
              @search="(keyword: string) => searchOptions(item.key, keyword)"
              @dropdown-reach-bottom="moreOptions(item.key)" />
            <a-input v-else v-model="item.value" :placeholder="item.placeholder" @press-enter="search" />
          </a-form-item>
          <a-form-item v-if="section === 'timing'" label="统计时间">
            <a-range-picker v-model="dateRange" show-time format="MM-DD HH:mm" value-format="YYYY-MM-DD HH:mm:ss"
              :allow-clear="false" />
          </a-form-item>
        </a-form>
      </template>
      <template #tabs>
        <a-tabs v-model:active-key="section" class="mango-tabs-nav-only" @change="changeSection">
          <a-tab-pane v-for="item in sectionOptions" :key="item.value" :title="item.label" />
        </a-tabs>
      </template>

      <div class="mango-efficiency-content">
        <a-alert v-if="error" type="error" role="alert">
          {{ error }} <a-button size="small" :loading="loading" @click="refresh">重新查询</a-button>
        </a-alert>
        <mango-panel-spin :loading="initialLoading" class="mango-efficiency-panel">
          <template v-if="snapshot && !error">
            <dl class="mango-efficiency-metrics" aria-label="执行效能概览">
              <div v-for="metric in metrics" :key="metric.label" :class="`mango-efficiency-metric--${metric.tone || 'neutral'}`">
                <dt>{{ metric.label }}</dt><dd>{{ metric.value }}</dd>
              </div>
            </dl>
            <template v-if="section === 'timing'">
              <p class="mango-efficiency-muted mango-efficiency-coverage">
                计时覆盖 <strong>{{ snapshot.summary.covered_completed }} / {{ snapshot.summary.api_completed }}</strong> 个API执行项
                <span class="mango-efficiency-separator">·</span>{{ snapshot.summary.sample_count }} 条完成尝试
                <span v-if="snapshot.summary.reports_without_details">另有 {{ snapshot.summary.reports_without_details }} 份报告已无执行明细。</span>
              </p>
              <div class="mango-efficiency-charts">
                <section class="mango-efficiency-section"><div class="mango-efficiency-section-heading"><h3>完成量与耗时趋势</h3></div>
                  <div class="mango-efficiency-chart"><EffectivenessChart :height="chartHeight" :option="trendOption" :empty="!snapshot.trend?.length" :loading="!initialLoading && loading" /></div>
                </section>
                <section class="mango-efficiency-section"><div class="mango-efficiency-section-heading"><h3>API 阶段耗时</h3></div>
                  <div class="mango-efficiency-chart"><EffectivenessChart :height="chartHeight" :option="phaseOption" :empty="!snapshot.phases?.length" :loading="!initialLoading && loading" /></div>
                </section>
              </div>
              <div class="mango-efficiency-basics" aria-label="各自动化类型基础执行量">
                <div v-for="item in snapshot.basic" :key="item.type" class="mango-efficiency-basic">
                  <strong>{{ item.name }}</strong>
                  <dl><div><dt>执行项</dt><dd>{{ item.total }}</dd></div><div><dt>已结束</dt><dd>{{ item.completed }}</dd></div>
                    <div><dt>待开始</dt><dd>{{ item.pending }}</dd></div><div><dt>执行中</dt><dd>{{ item.running }}</dd></div></dl>
                </div>
              </div>
              <section class="mango-efficiency-section mango-efficiency-ranking">
                <div class="mango-efficiency-section-heading">
                  <a-radio-group v-model="ranking" type="button" size="small" aria-label="慢执行排行类型">
                    <a-radio v-for="item in rankingOptions" :key="item.value" :value="item.value">{{ item.label }}</a-radio>
                  </a-radio-group>
                  <span>{{ ranking === 'cases' ? '按单次尝试耗时排序 · 前100' : '已采集API链路跨度 · 前100' }}</span>
                </div>
                <template v-if="ranking === 'cases'">
              <a-table :columns="slowCaseColumns" :data="slowCases" row-key="trace_id" size="small"
                :loading="!initialLoading && loading" :pagination="false" :scroll="{ x: efficiencyScrollWidths.cases, y: compactTableHeight(slowCases.length) }" class="mango-native-scroll-table">
                <template #duration="{ record }"><span class="mango-efficiency-number">{{ duration(record.duration_ms) }}</span></template>
                <template #started_at="{ record }">{{ record.started_at ? dayjs(record.started_at).format('YYYY-MM-DD HH:mm:ss') : '—' }}</template>
                <template #project_product="{ record }">{{ formatProjectProductPath(record.project_product) }}</template>
                <template #module="{ record }">{{ formatModulePath(record.module) || '—' }}</template>
                <template #actions="{ record }"><MangoTableActions :actions="caseActions(record)" /></template>
              </a-table>
              <div class="mango-efficiency-pagination"><a-pagination v-model:current="slowPage" :total="snapshot.slow_cases?.length || 0" :page-size="10" size="small" show-total /></div>
                </template>
                <template v-else>
              <a-table :columns="slowReportColumns" :data="slowReports" row-key="report_id" size="small"
                :loading="!initialLoading && loading" :pagination="false" :scroll="{ x: efficiencyScrollWidths.reports, y: compactTableHeight(slowReports.length) }" class="mango-native-scroll-table">
                <template #span="{ record }">{{ duration(record.observed_span_ms) }}</template>
                <template #delay="{ record }">{{ duration(record.first_start_delay_ms) }}</template>
                <template #timing_status="{ record }">{{ record.running ? '运行中（持续增长）' : record.timing_complete === false ? '计时不完整' : '已采集链路跨度' }}</template>
                <template #project_product="{ record }">{{ formatProjectProductPath(record.project_product) }}</template>
                <template #module="{ record }">{{ formatModulePath(record.module) || '—' }}</template>
                <template #actions="{ record }"><MangoTableActions :actions="reportActions(record)" /></template>
              </a-table>
              <div class="mango-efficiency-pagination"><a-pagination v-model:current="reportPage" :total="snapshot.slow_reports?.length || 0" :page-size="10" size="small" show-total /></div>
                </template>
              </section>
            </template>
            <template v-else>
              <section class="mango-efficiency-section mango-efficiency-live">
              <div class="mango-efficiency-section-heading">
                <h3>{{ section === 'queue' ? '排队报告' : '异常执行项' }}</h3>
                <span>{{ pagination.pageCount }} 条</span>
              </div>
              <div class="mango-efficiency-capacity">
                <span><IconDesktop /> API Worker <strong>{{ snapshot.workers?.online }}</strong> 个在线</span>
                <span>忙碌槽位 <strong>{{ snapshot.workers?.running }} / {{ snapshot.workers?.capacity }}</strong></span>
              </div>
              <a-table :columns="section === 'queue' ? queueColumns : anomalyColumns" :data="snapshot.items || []"
                :row-key="section === 'queue' ? 'report_id' : 'id'" size="small" :loading="!initialLoading && loading"
                :pagination="false" :scroll="{ x: section === 'queue' ? efficiencyScrollWidths.queue : efficiencyScrollWidths.anomalies, y: '100%' }"
                class="mango-native-scroll-table mango-efficiency-current-table">
                <template #test_env="{ record }">{{ environment(record.test_env) }}</template>
                <template #limit="{ record }"><span class="mango-efficiency-number">{{ record.api_concurrency_limit ?? '—' }} <span class="mango-efficiency-muted">/</span> {{ record.effective_api_limit }}</span></template>
                <template #pending="{ record }"><span :class="{ 'mango-efficiency-warning': record.pending > 0 }" class="mango-efficiency-number">{{ record.pending }}</span></template>
                <template #running="{ record }"><span :class="{ 'mango-efficiency-primary': record.running > 0 }" class="mango-efficiency-number">{{ record.running }}</span></template>
                <template #wait="{ record }"><span class="mango-efficiency-number">{{ duration(record.longest_wait_ms) }}</span></template>
                <template #diagnosis="{ record }"><span class="mango-efficiency-diagnosis" :class="`mango-efficiency-diagnosis--${diagnosisTone(record.diagnosis)}`">{{ record.diagnosis }}</span></template>
                <template #elapsed="{ record }">{{ duration(record.elapsed_ms) }}</template>
                <template #current="{ record }">
                  <div v-if="record.current_case" class="mango-efficiency-case" :title="`${record.current_case.case_name} · ${record.current_case.stage} · ${duration(record.current_case.elapsed_ms)}`">
                    <span class="mango-efficiency-case-name">{{ record.current_case.case_name }}</span>
                    <span class="mango-efficiency-case-context"><span>{{ record.current_case.stage }}</span><strong>{{ duration(record.current_case.elapsed_ms) }}</strong></span>
                  </div><span v-else class="mango-efficiency-muted">—</span>
                </template>
                <template #project_product="{ record }">{{ formatProjectProductPath(record.project_product) }}</template>
                <template #module="{ record }">{{ formatModulePath(record.module) || '—' }}</template>
                <template #actions="{ record }"><MangoTableActions :actions="reportActions(record)" /></template>
              </a-table>
              </section>
            </template>
          </template>
          <div v-else-if="!loading && !error" class="mango-empty-state">请选择范围并查询执行效能</div>
        </mango-panel-spin>
      </div>
      <template v-if="section !== 'timing'" #footer>
        <TableFooter :pagination="pagination" :show-refresh="false" />
      </template>
    </ProjectProductNavigationWorkbench>
    <ExecutionResultHistoryDrawer v-model:visible="history.visible" :title="history.title"
      :query="history.query" />
  </TableBody>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { getExecutionEfficiency, getExecutionEfficiencyOptions, type EfficiencyResponse, type EfficiencySection } from '@/api/system/execution_efficiency'
import type { ExecutionResultQuery } from '@/api/system/execution_result'
import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
import MangoTableActions from '@/components/table/MangoTableActions.vue'
import EffectivenessChart from '../effectiveness/components/EffectivenessChart.vue'
import { useEnum } from '@/store/modules/get-enum'
import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { createConditions, sectionOptions, rankingOptions, queueColumns, anomalyColumns, slowCaseColumns, slowReportColumns, efficiencyScrollWidths, duration, compactTableHeight, diagnosisTone } from './config'

const router = useRouter(), enumStore = useEnum(), userStore = useUserStore(), permissionStore = usePermissionStore()
const section = ref<EfficiencySection>('queue'), loading = ref(false), error = ref('')
const ranking = ref('cases')
const snapshot = ref<EfficiencyResponse | null>(null), conditions = reactive(createConditions()), resetKey = ref(0)
const initialLoading = computed(() => loading.value && !snapshot.value)
const chartHeight = computed(() => `${scaleDensityPixels(240)}px`)
const navigation = reactive<{ projectProduct: string | number | null; module: string | number | null; moduleIds: Array<string | number> }>({ projectProduct: null, module: null, moduleIds: [] })
const initialDates = () => [dayjs().subtract(24, 'hour').format('YYYY-MM-DD HH:mm:ss'), dayjs().format('YYYY-MM-DD HH:mm:ss')]
const dateRange = ref(initialDates()), slowPage = ref(1), reportPage = ref(1)
const history = reactive<{ visible: boolean; title: string; query?: ExecutionResultQuery }>({ visible: false, title: '' })
let requestVersion = 0, active = true
const optionState = reactive<Record<string, { loading: boolean; page: number; keyword: string; more: boolean; version: number }>>({
  task_ids: { loading: false, page: 0, keyword: '', more: true, version: 0 },
  task_group_ids: { loading: false, page: 0, keyword: '', more: true, version: 0 },
})
const optionTimers: Record<string, ReturnType<typeof setTimeout>> = {}
function isTaskOption(key: string) { return key === 'task_ids' || key === 'task_group_ids' }
async function loadOptions(key: string, nextPage = 1) {
  const state = optionState[key]
  if (!state || !active) return
  const version = ++state.version
  state.loading = true
  try {
    const response = await getExecutionEfficiencyOptions({ kind: key === 'task_ids' ? 'tasks' : 'groups',
      ...(navigation.projectProduct ? { product_id: navigation.projectProduct } : {}),
      keyword: state.keyword, page: nextPage, page_size: 50 })
    if (version !== state.version || !active) return
    const item = conditions.find(item => item.key === key)!
    const incoming = response.data.items.map(row => ({ value: row.id, label: row.name }))
    item.optionItems = nextPage === 1 ? incoming : [...(item.optionItems || []), ...incoming]
    state.page = nextPage; state.more = response.data.has_more
  } finally { if (version === state.version) state.loading = false }
}
function openOptions(key: string) { if (optionState[key]?.page === 0) loadOptions(key).catch(() => {}) }
function searchOptions(key: string, keyword: string) {
  if (!optionState[key]) return
  optionState[key].keyword = keyword
  optionState[key].version++
  optionState[key].loading = true
  optionState[key].more = false
  clearTimeout(optionTimers[key])
  optionTimers[key] = setTimeout(() => loadOptions(key).catch(() => {}), 250)
}
function moreOptions(key: string) {
  const state = optionState[key]
  if (state && !state.loading && state.more) loadOptions(key, state.page + 1).catch(() => {})
}
function clearOptions() {
  for (const key of Object.keys(optionState)) {
    clearTimeout(optionTimers[key]); optionState[key].version++
    Object.assign(optionState[key], { page: 0, keyword: '', more: true, loading: false })
    const item = conditions.find(item => item.key === key)!
    item.value = []; item.optionItems = []
  }
}
const pagination = reactive({ page: 1, pageSize: 20, pageCount: 0, pageSizes: [20, 50, 100], showSizePicker: true, onChange: () => refresh() })
const slowCases = computed(() => snapshot.value?.slow_cases?.slice((slowPage.value - 1) * 10, slowPage.value * 10) || [])
const slowReports = computed(() => snapshot.value?.slow_reports?.slice((reportPage.value - 1) * 10, reportPage.value * 10) || [])
const metrics = computed(() => {
  const summary = snapshot.value?.summary || {}
  return section.value === 'timing' ? [
    { label: '已结束执行项', value: summary.completed ?? '—', tone: 'neutral' },
    { label: 'API P50耗时', value: duration(summary.p50_ms), tone: 'primary' }, { label: 'API P95耗时', value: duration(summary.p95_ms), tone: 'primary' },
    { label: '额外重试次数', value: summary.retry_count ?? '—', tone: 'neutral' }, { label: '已记录重试耗时', value: duration(summary.retry_duration_ms), tone: 'neutral' },
  ] : [
    { label: '待开始', value: summary.pending ?? '—', tone: summary.pending ? 'warning' : 'neutral' }, { label: '执行中', value: summary.running ?? '—', tone: 'primary' },
    { label: '排队报告', value: summary.report_count ?? '—', tone: 'neutral' }, { label: '最长首次等待', value: duration(summary.longest_wait_ms), tone: 'neutral' },
    { label: '异常线索', value: summary.anomaly_count ?? '—', tone: summary.anomaly_count ? 'danger' : 'neutral' },
  ]
})
function options(key: string) {
  if (key === 'test_env') return (enumStore.environment_type || []).map((item: any) => ({ value: item.key, label: item.title }))
  return conditions.find(item => item.key === key)?.optionItems || []
}
function environment(value: unknown) {
  return (enumStore.environment_type || []).find((item: any) => String(item.key) === String(value))?.title || String(value)
}
function reportActions(record: Record<string, any>) {
  return [{ label: '查看报告', onClick: () => router.push({ path: '/report/system/details', query: { id: record.report_id } }) }]
}
function caseActions(record: Record<string, any>) {
  return [{ label: '执行历史', onClick: () => {
    history.title = `用例执行历史：${record.case_name}`
    history.query = { target_type: 'api_case', test_suite_detail_id: record.detail_id, test_suite_id: record.report_id }
    history.visible = true
  } }]
}
function buildQuery() {
  const query: Record<string, any> = { section: section.value, page: pagination.page, page_size: pagination.pageSize }
  if (navigation.projectProduct) query.project_product_id = navigation.projectProduct
  if (navigation.moduleIds.length) query.module_ids__in = navigation.moduleIds.join(',')
  else if (navigation.module) query.module_ids__in = navigation.module
  for (const item of conditions) {
    if (Array.isArray(item.value)) { if (item.value.length) query[`${item.key}__in`] = item.value.join(',') }
    else if (String(item.value ?? '').trim()) query[item.key] = String(item.value).trim()
  }
  if (section.value === 'timing') { query.start_at = dateRange.value[0]; query.end_at = dateRange.value[1] }
  return query
}
async function refresh() {
  const version = ++requestVersion
  loading.value = true; error.value = ''
  try {
    const response = await getExecutionEfficiency(buildQuery())
    if (version !== requestVersion || !active) return
    snapshot.value = response.data
    pagination.pageCount = response.data.count || 0
  } catch (failure: any) {
    if (version !== requestVersion || !active) return
    snapshot.value = null
    error.value = failure?.msg || failure?.message || '查询失败，请缩小范围后重试'
  } finally { if (version === requestVersion) loading.value = false }
}
function search() { pagination.page = 1; slowPage.value = 1; reportPage.value = 1; snapshot.value = null; refresh() }
function changeSection() { search() }
function onNavigation(value: typeof navigation) {
  if (String(value.projectProduct) !== String(navigation.projectProduct)) clearOptions()
  Object.assign(navigation, value, { moduleIds: value.moduleIds || [] }); search()
}
function reset() {
  conditions.forEach(item => { item.value = item.multiple ? [] : '' })
  Object.assign(navigation, { projectProduct: null, module: null, moduleIds: [] })
  dateRange.value = initialDates(); resetKey.value += 1; search()
  clearOptions()
}
const trendOption = computed(() => ({
  color: ['var(--m-chart-1)', 'var(--m-chart-2)', 'var(--m-chart-3)'], tooltip: { trigger: 'axis' },
  legend: { data: ['API完成执行项', 'P50（秒）', 'P95（秒）'], textStyle: { color: 'var(--m-text-2)' } },
  grid: { left: '12%', right: '12%', bottom: '18%', top: '20%' },
  xAxis: { type: 'category', data: snapshot.value?.trend?.map(row => row.time), axisLabel: { color: 'var(--m-muted)' } },
  yAxis: [{ type: 'value', minInterval: 1, name: '执行项', axisLabel: { color: 'var(--m-muted)' } }, { type: 'value', name: '秒', axisLabel: { color: 'var(--m-muted)' }, splitLine: { show: false } }],
  series: [
    { name: 'API完成执行项', type: 'bar', data: snapshot.value?.trend?.map(row => row.completed) },
    ...(['p50_ms', 'p95_ms'] as const).map((key, index) => ({ name: index ? 'P95（秒）' : 'P50（秒）', type: 'line', yAxisIndex: 1,
      data: snapshot.value?.trend?.map(row => row[key] === null ? null : Number(row[key]) / 1000) })),
  ],
}))
const phaseOption = computed(() => ({
  color: ['var(--m-chart-1)'], tooltip: { trigger: 'axis' }, grid: { left: '25%', right: '8%', top: '8%', bottom: '15%' },
  xAxis: { type: 'value', name: '秒', axisLabel: { color: 'var(--m-muted)' } },
  yAxis: { type: 'category', data: snapshot.value?.phases?.map(row => row.name), axisLabel: { color: 'var(--m-text-2)' } },
  series: [{ type: 'bar', data: snapshot.value?.phases?.map(row => Number((row.duration_ms / 1000).toFixed(3))) }],
}))
watch(() => [userStore.userId, userStore.roleId, permissionStore.permissionKeys.join('|')], () => {
  requestVersion++; snapshot.value = null; history.visible = false; loading.value = false
  clearOptions()
  if (active) search()
})
onMounted(() => { enumStore.getEnum(); refresh() })
onActivated(() => { if (!active) { active = true; refresh() } })
onDeactivated(() => { active = false; requestVersion++; loading.value = false })
onBeforeUnmount(() => { active = false; requestVersion++; clearOptions() })
</script>

<style scoped>
.mango-efficiency-page { height: 100%; }
.mango-efficiency-content { display: flex; flex-direction: column; gap: var(--m-page-gap); min-height: 0; height: 100%; container: mango-efficiency / inline-size; }
.mango-efficiency-muted { color: var(--m-muted); font-size: 12px; margin: 0; }
.mango-efficiency-panel { min-height: 0; flex: 1; }
.mango-efficiency-panel :deep(> .mango-panel-spin__content) { display: flex; flex-direction: column; gap: var(--m-page-gap); height: 100%; min-height: 0; overflow-y: auto; padding: var(--m-page-gap); box-sizing: border-box; background: var(--m-bg); }
.mango-efficiency-metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0; padding: var(--m-space-lg) 0; margin: 0; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); font-variant-numeric: tabular-nums; flex-shrink: 0; }
.mango-efficiency-metrics > div { display: flex; flex-direction: column; gap: var(--m-space-sm); min-width: 0; padding: 0 var(--m-space-lg); }
.mango-efficiency-metrics > div + div { border-left: 1px solid var(--m-border); }
.mango-efficiency-metrics dt { color: var(--m-text-2); font-size: 12px; }
.mango-efficiency-metrics dd { margin: 0; color: var(--m-text); font-size: 20px; line-height: 1.4; font-weight: 600; overflow-wrap: anywhere; }
.mango-efficiency-metric--primary dd, .mango-efficiency-primary { color: var(--m-primary); }
.mango-efficiency-metric--warning dd, .mango-efficiency-warning { color: var(--m-warning); }
.mango-efficiency-metric--danger dd { color: var(--m-danger); }
.mango-efficiency-charts { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: var(--m-page-gap); }
.mango-efficiency-chart { height: 240px; }
.mango-efficiency-content h3 { margin: 0; color: var(--m-text); font-size: var(--m-font-body); font-weight: 600; }
.mango-efficiency-charts > section { min-width: 0; }
.mango-efficiency-section { border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); min-width: 0; flex-shrink: 0; overflow: hidden; }
.mango-efficiency-section-heading { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: var(--m-page-gap); min-height: 40px; padding: var(--m-space-sm) var(--m-card-padding); border-bottom: 1px solid var(--m-border); flex-shrink: 0; }
.mango-efficiency-section-heading > span { color: var(--m-muted); font-size: 12px; }
.mango-efficiency-basics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); font-variant-numeric: tabular-nums; flex-shrink: 0; }
.mango-efficiency-basic { padding: var(--m-card-padding); min-width: 0; }
.mango-efficiency-basic + .mango-efficiency-basic { border-left: 1px solid var(--m-border); }
.mango-efficiency-basic > strong { color: var(--m-text); font-size: var(--m-font-body); }
.mango-efficiency-basic dl { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin: 8px 0 0; }
.mango-efficiency-basic dt { color: var(--m-muted); font-size: 12px; white-space: nowrap; }
.mango-efficiency-basic dd { margin: 3px 0 0; color: var(--m-text); font-weight: 600; }
.mango-efficiency-pagination { display: flex; justify-content: flex-end; padding: var(--m-space-sm) var(--m-card-padding); border-top: 1px solid var(--m-border); }
.mango-efficiency-live { display: flex; flex-direction: column; flex: 1; min-height: 280px; }
.mango-efficiency-capacity { display: flex; flex-wrap: wrap; align-items: center; gap: var(--m-space-lg); padding: var(--m-space-sm) var(--m-card-padding); color: var(--m-text-2); font-size: var(--m-font-caption); background: var(--m-surface-soft); border-bottom: 1px solid var(--m-border); flex-shrink: 0; }
.mango-efficiency-capacity > span { display: inline-flex; align-items: center; gap: 6px; }
.mango-efficiency-capacity strong { color: var(--m-text); font-variant-numeric: tabular-nums; }
.mango-efficiency-number { font-variant-numeric: tabular-nums; font-weight: 500; }
.mango-efficiency-case { display: flex; min-width: 0; flex-direction: column; gap: 3px; padding: 2px 0; }
.mango-efficiency-case-name { color: var(--m-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mango-efficiency-case-context { display: flex; align-items: baseline; gap: 8px; color: var(--m-muted); font-size: 12px; }
.mango-efficiency-case-context > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mango-efficiency-case-context > strong { color: var(--m-text-2); flex-shrink: 0; font-weight: 500; font-variant-numeric: tabular-nums; }
.mango-efficiency-diagnosis { display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--m-text-2); }
.mango-efficiency-diagnosis--warning { color: var(--m-warning); }
.mango-efficiency-diagnosis--danger { color: var(--m-danger); }
.mango-efficiency-help { width: 360px; max-width: calc(100vw - 48px); color: var(--m-text-2); font-size: 12px; line-height: 1.7; }
.mango-efficiency-help p { margin: 0 0 8px; }
.mango-efficiency-help p:last-child { margin-bottom: 0; }
.mango-efficiency-coverage strong { font-weight: 600; color: var(--m-text-2); font-variant-numeric: tabular-nums; }
.mango-efficiency-separator { margin: 0 6px; }
.mango-efficiency-current-table { flex: 1; min-height: 160px; }
@container mango-efficiency (max-width: 64rem) {
  .mango-efficiency-charts { grid-template-columns: minmax(0, 1fr); }
  .mango-efficiency-metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); row-gap: var(--m-space-lg); }
  .mango-efficiency-metrics > div:nth-child(4) { border-left: 0; }
  .mango-efficiency-basics { grid-template-columns: minmax(0, 1fr); }
  .mango-efficiency-basic + .mango-efficiency-basic { border-left: 0; border-top: 1px solid var(--m-border); }
}
@container mango-efficiency (max-width: 40rem) {
  .mango-efficiency-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .mango-efficiency-metrics > div:nth-child(odd) { border-left: 0; }
  .mango-efficiency-metrics > div:nth-child(even) { border-left: 1px solid var(--m-border); }
}
</style>
