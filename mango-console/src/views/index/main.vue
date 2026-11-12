<template>
  <div class="mango-home-workbench-scroll mango-workbench-scroll-x">
    <div class="main-container mango-home-dashboard">
      <div class="left">
        <div class="item mango-section-card">
          <Title title="项目自动化质量" />
          <a-button
            class="mango-home-card-shortcut"
            type="text"
            size="small"
            :loading="navigatingTo === homeLinks.quality"
            :disabled="!!navigatingTo"
            @click="navigateTo(homeLinks.quality)"
          >
            直达质量效能
            <template #icon><IconArrowRight /></template>
          </a-button>
          
          <ProjectQualityChart :data="projectQualityRows" :loading="projectQualityLoading" />
        </div>
        <div class="item mango-section-card">
          <Title title="近 7 天执行结果" />
          <a-button
            class="mango-home-card-shortcut"
            type="text"
            size="small"
            :loading="navigatingTo === homeLinks.reports"
            :disabled="!!navigatingTo"
            @click="navigateTo(homeLinks.reports)"
          >
            直达执行报告
            <template #icon><IconArrowRight /></template>
          </a-button>
          
          <StatusChart
            :success="reportCounts.success"
            :fail="reportCounts.fail"
            :warning="reportCounts.warning"
            :other="reportOtherCount"
            :loading="reportSumLoading"
            center-label="最终通过率"
            :center-value="formatPercent(reportPassRate)"
          />
        </div>
        <div class="item mango-section-card">
          <Title title="自动化能力建设" />
          <AutomationStats />
        </div>
      </div>
      <div class="center-workspace">
        <div class="trend-panel panel mango-section-card">
          <Title title="近 12 周自动化执行趋势" />
          <FullYearSalesChart />
        </div>
        <div class="center-bottom">
          <div class="pending-panel panel mango-section-card">
            <Title title="即将执行的定时任务" />
            <a-button class="mango-home-card-shortcut" type="text" size="small"
              :loading="navigatingTo === homeLinks.tasks" :disabled="!!navigatingTo" @click="navigateTo(homeLinks.tasks)">
              直达定时任务<template #icon><IconArrowRight /></template>
            </a-button>
            <div class="pending-card-body">
              <PendingTasks />
            </div>
          </div>
          <div class="activity-panel panel mango-section-card">
            <Title title="近 7 天用户活跃度" />
            <HotProductChart />
          </div>
        </div>
      </div>
      <div class="right-rail">
        <div class="todo-panel panel mango-section-card">
          <Title title="风险待办" :class="{ 'mango-risk-title--danger': hasPendingRisk }" />
          <div class="todo-card-body">
            <RiskTodos @pending-change="hasPendingRisk = $event" />
          </div>
        </div>
        <div class="resource-panel panel mango-section-card">
          <div class="resource-panel__content">
            <Title title="资源中心" />
            <ResourceCenter
              @download-executor="downloadExecutor"
              @view-skill="viewSkill"
              @view-help="viewHelp"
              @contact-author="contactAuthor"
            />
          </div>
        </div>
        <div class="mcp-panel panel mango-section-card">
          <Title title="MCP智能接入" />
          <McpWorkbench compact />
        </div>
      </div>
    </div>
  </div>

  <!-- 联系作者弹窗 -->
  <ContactAuthor v-model:visible="contactVisible" />
  <SkillCenterDrawer v-model:visible="skillVisible" />
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import { homeLinks } from './config'
  import { emptyReportCounts, formatPercent, readProjectQuality, readReportSummary } from './records'
  import type { HomeReportCounts, ProjectQualityItem } from './types'
  import { useRoute, useRouter } from 'vue-router'
  import { IconArrowRight } from '@arco-design/web-vue/es/icon'
  import FullYearSalesChart from './components/chart/FullYearSalesChart.vue'
  import HotProductChart from './components/chart/HotProductChart.vue'
  import Title from '@/views/index/components/Title.vue'
  import StatusChart from '@/components/chart/StatusChart.vue'
  import { getSystemCaseRunSum, getSystemProjectQuality } from '@/api/system'
  import ContactAuthor from './components/ContactAuthor.vue'
  import AutomationStats from './components/AutomationStats.vue'
  import PendingTasks from './components/PendingTasks.vue'
  import ResourceCenter from './components/ResourceCenter.vue'
  import McpWorkbench from './components/McpWorkbench.vue'
  import SkillCenterDrawer from './components/SkillCenterDrawer.vue'
  import RiskTodos from './components/RiskTodos.vue'
  import ProjectQualityChart from './components/chart/ProjectQualityChart.vue'

  const contactVisible = ref(false)
  const skillVisible = ref(false)
  const hasPendingRisk = ref(false)
  const router = useRouter(), route = useRoute(), user = useUserStore()
  const entryPath = route.path
  const contextKey = computed(() => JSON.stringify([
    route.fullPath, user.userId, user.roleId, user.token, user.selected_environment,
  ]))
  const projectQualityRows = ref<ProjectQualityItem[]>([])
  const projectQualityLoading = ref(false)
  const projectQualityError = ref('')
  const reportCounts = ref<HomeReportCounts>(emptyReportCounts())
  const reportPassRate = ref<number | null>(null)
  const reportSumLoading = ref(false)
  const reportSumError = ref('')
  const navigatingTo = ref<string | null>(null)
  let active = true, mounted = false, projectSequence = 0, reportSequence = 0, contextGeneration = 0
  const available = () => active && route.path === entryPath
  const reportOtherCount = computed(() => reportCounts.value.proceed + reportCounts.value.stay_begin + reportCounts.value.stopped)

  async function loadProjectQuality() {
    if (!available()) return
    const sequence = ++projectSequence, context = contextKey.value, generation = contextGeneration
    const current = () => available() && sequence === projectSequence && context === contextKey.value && generation === contextGeneration
    projectQualityLoading.value = true
    projectQualityError.value = ''
    try {
      const rows = readProjectQuality(await getSystemProjectQuality())
      if (current()) projectQualityRows.value = rows
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "项目自动化质量加载失败，请重试", false), projectQualityError.value = '项目自动化质量加载失败，请重试')
    } finally {
      if (current()) projectQualityLoading.value = false
    }
  }

  async function loadReportSummary() {
    if (!available()) return
    const sequence = ++reportSequence, context = contextKey.value, generation = contextGeneration
    const current = () => available() && sequence === reportSequence && context === contextKey.value && generation === contextGeneration
    reportSumLoading.value = true
    reportSumError.value = ''
    try {
      const summary = readReportSummary(await getSystemCaseRunSum())
      if (current()) { reportCounts.value = summary.counts; reportPassRate.value = summary.passRate }
    } catch (loadFailure1) {
      if (current()) (reportLoadError(loadFailure1, "近七天执行结果加载失败，请重试", false), reportSumError.value = '近七天执行结果加载失败，请重试')
    } finally {
      if (current()) reportSumLoading.value = false
    }
  }

  function reloadAggregates() { void loadProjectQuality(); void loadReportSummary() }
  function invalidateAggregates() {
    contextGeneration++; projectSequence++; reportSequence++
    projectQualityLoading.value = false; reportSumLoading.value = false
    contactVisible.value = false; skillVisible.value = false
  }
  watch(contextKey, () => {
    invalidateAggregates()
    projectQualityRows.value = []; reportCounts.value = emptyReportCounts(); reportPassRate.value = null
    projectQualityError.value = ''; reportSumError.value = ''; hasPendingRisk.value = false
    if (mounted && available()) reloadAggregates()
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; reloadAggregates() })
  onDeactivated(() => { active = false; invalidateAggregates() })
  onActivated(() => { if (mounted && !active) { active = true; reloadAggregates() } })
  onBeforeUnmount(() => { active = false; mounted = false; invalidateAggregates() })

  async function navigateTo(path: string) {
    if (!available() || navigatingTo.value) return
    const generation = contextGeneration
    navigatingTo.value = path
    try { await router.push(path) }
    catch { if (available() && generation === contextGeneration) Message.error('页面打开失败，请重试') }
    finally { navigatingTo.value = null }
  }
  function downloadExecutor() { if (available()) window.open(homeLinks.executor, '_blank', 'noopener,noreferrer') }
  function viewHelp() { if (available()) window.open(homeLinks.help, '_blank', 'noopener,noreferrer') }
  function viewSkill() { if (available()) skillVisible.value = true }
  function contactAuthor() { if (available()) contactVisible.value = true }
</script>

<style lang="less" scoped>
  :deep(.title-container) {
    z-index: 1;
  }

  .mango-home-workbench-scroll {
    --mango-workbench-min-width: calc(1050px + 2 * var(--m-page-gap));
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: auto;
    container-name: mango-home;
    container-type: inline-size;
    overscroll-behavior: contain;
    scrollbar-color: var(--m-scrollbar-thumb) transparent;
    scrollbar-width: thin;
  }

  .main-container {
    display: grid;
    width: 100%;
    height: 100%;
    /* 首页是固定阅读顺序的数据看板；宽度不足时滚动，不能把右栏重排到不可见区域。 */
    min-width: var(--mango-workbench-min-width);
    min-height: 648px;
    margin: 0 auto;
    grid-template-areas: 'left center right';
    grid-template-columns:
      minmax(260px, 22fr)
      minmax(520px, 56fr)
      minmax(270px, 22fr);
    gap: var(--m-page-gap);
    overflow: hidden;

    .mango-section-card + .mango-section-card {
      margin-top: 0;
    }

    .panel {
      display: flex;
      min-height: 0;
      flex-direction: column;
      position: relative;
      transition: box-shadow 0.2s cubic-bezier(0, 0, 1, 1);
    }

    .mango-home-panel-description {
      margin: -4px 8px 1px 18px;
      color: var(--m-muted);
      font-size: var(--m-home-font-micro);
      line-height: 13px;
    }

    .mango-home-card-shortcut {
      position: absolute;
      z-index: 2;
      top: 8px;
      right: 8px;
      height: 21px;
      padding: 0 4px;
      font-size: var(--m-home-font-micro);
    }

    :deep(.title-container) {
      padding: 8px;

      .title {
        font-size: var(--m-home-font-title);
      }

      .line {
        width: 2px;
        height: 13px;
        margin-right: 7px;
      }
    }

    :deep(.mango-upcoming-task) {
      min-height: 50px;
      grid-template-columns: 77px minmax(0, 1fr) auto;
      gap: 9px;
      padding: 6px 9px;
    }

    :deep(.mango-upcoming-task__relative) {
      font-size: var(--m-home-font-body);
    }

    :deep(.mango-upcoming-task__absolute),
    :deep(.mango-upcoming-task__meta) {
      font-size: var(--m-home-font-micro);
    }

    :deep(.mango-upcoming-task__name) {
      font-size: var(--m-home-font-small);
    }

    :deep(.mango-upcoming-task__meta) {
      margin-top: 2px;
    }

    :deep(.mango-risk-todo) {
      min-height: 61px;
      padding: 6px 8px;
    }

    :deep(.mango-risk-todo__title-row strong) {
      font-size: var(--m-home-font-small);
    }

    :deep(.mango-risk-todo__summary) {
      margin: 1px 0;
      font-size: var(--m-home-font-micro);
      line-height: 13px;
    }

    :deep(.mango-capability-overview) {
      padding: 4px 8px 8px;
    }

    :deep(.mango-capability-grid) {
      grid-auto-rows: minmax(142px, 1fr);
      gap: 6px;
    }

    :deep(.mango-capability-card) {
      gap: 6px;
      padding: 8px 8px 6px;
    }

    :deep(.mango-capability-card__header) {
      grid-template-columns: 23px minmax(0, 1fr) minmax(54px, auto);
      gap: 4px;

      strong {
        font-size: var(--m-home-font-body);
        line-height: 16px;
      }
    }

    :deep(.mango-capability-card__icon) {
      width: 23px;
      height: 23px;
      flex-basis: 23px;
      font-size: var(--m-font-subtitle);
    }

    :deep(.mango-capability-card__total strong) {
      font-size: var(--m-font-subtitle);
      line-height: 17px;
      white-space: nowrap;
    }

    :deep(.mango-capability-card__total) {
      min-width: 54px;
    }

    :deep(.mango-capability-card__metrics) {
      grid-auto-rows: minmax(22px, 1fr);
      padding-top: 6px;
    }

    :deep(.mango-capability-metric) {
      gap: 3px;
      padding: 2px 4px;

      dd {
        font-size: var(--m-home-font-body);
        line-height: 14px;
      }
    }

    :deep(.mango-activity-rank__list) {
      gap: 6px;
      padding-top: 4px;
    }

    :deep(.mango-activity-rank__metrics) {
      padding: 4px 1px;

      div {
        padding: 4px;
      }

      strong {
        font-size: var(--m-home-font-body);
        line-height: 15px;
      }
    }

    :deep(.mango-activity-rank__trend) {
      height: 54px;
    }

    :deep(.mango-mcp-workbench.is-compact) {
      .mango-mcp-scroll-area {
        gap: 3px;
      }

      .mango-mcp-endpoint-box,
      .mango-mcp-api-key-box {
        min-height: 45px;
        padding: 6px 8px;
      }

      .mango-mcp-capability-item {
        padding: 5px;
      }

      .arco-btn-size-small {
        height: 21px;
        font-size: var(--m-home-font-micro);
      }
    }

    .left {
      display: flex;
      grid-area: left;
      min-width: 0;
      min-height: 0;
      flex-direction: column;
      gap: var(--m-page-gap);

      .item {
        display: flex;
        flex-direction: column;
        min-height: 0;
        position: relative;
        transition: box-shadow 0.2s cubic-bezier(0, 0, 1, 1);

        div:nth-last-child(1) {
          flex: 1;
        }
      }

      .item:nth-child(1),
      .item:nth-child(2) {
        flex: 0.86;
      }

      .item:nth-child(3) {
        flex: 1.28;
      }

      .item + .item {
        margin-top: 0;
      }
    }

    .center-workspace {
      display: grid;
      grid-area: center;
      min-width: 0;
      min-height: 0;
      grid-template-rows: minmax(270px, 36fr) minmax(0, 64fr);
      gap: var(--m-page-gap);
    }

    .trend-panel {
      overflow: hidden;
    }

    .center-bottom {
      display: grid;
      min-width: 0;
      min-height: 0;
      grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
      gap: var(--m-page-gap);
    }

    .pending-panel {
      overflow: hidden;
    }

    .pending-card-body {
      flex: 1;
      min-height: 0;
      padding-top: var(--m-page-gap);
    }

    .right-rail {
      display: grid;
      grid-area: right;
      min-width: 0;
      min-height: 0;
      grid-template-rows: minmax(252px, 34fr) minmax(76px, 8fr) minmax(234px, 58fr);
      gap: var(--m-page-gap);
    }

    .resource-panel,
    .todo-panel,
    .mcp-panel {
      overflow: hidden;
    }

    .resource-panel {
      border: 1px solid var(--m-border-strong);
    }

    .resource-panel__content {
      display: flex;
      width: 100%;
      min-height: 0;
      flex: 1;
      flex-direction: column;
      justify-content: center;
    }

    .todo-card-body {
      min-height: 0;
      padding-top: 3px;
      flex: 1;
    }

    .resource-panel :deep(.title-container) {
      padding: 3px 9px;
    }

    :deep(.mango-risk-title--danger .title) {
      color: var(--m-danger);
    }

    .activity-panel {
      overflow: hidden;
    }

    .activity-panel :deep(.chart-item-container) {
      flex: 1;
      min-height: 0;
    }
  }

  @media (max-height: 820px) and (min-width: 1440px) {
    .main-container {
      .center-workspace {
        grid-template-rows: 270px minmax(0, 1fr);
      }
    }
  }

  @media (max-height: 760px) and (min-width: 1440px) {
    .main-container {
      .center-workspace {
        grid-template-rows: 243px minmax(0, 1fr);
      }
    }
  }

</style>
