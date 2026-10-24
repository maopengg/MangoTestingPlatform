<template>
  <div class="mango-home-workbench-scroll">
    <div class="main-container mango-home-dashboard">
      <div class="left">
        <div class="item mango-section-card">
          <Title title="项目自动化质量" />
          <a-button
            class="mango-home-card-shortcut"
            type="text"
            size="small"
            @click="navigateTo('/report/effectiveness/index')"
          >
            直达质量效能
            <template #icon><IconArrowRight /></template>
          </a-button>
          <p class="mango-home-panel-description"
            >按项目汇总定时任务执行报告，比较执行量与最终结果</p
          >
          <ProjectQualityChart :data="data.projectQuality" :loading="data.projectQualityLoading" />
        </div>
        <div class="item mango-section-card">
          <Title title="近 7 天执行结果" />
          <a-button
            class="mango-home-card-shortcut"
            type="text"
            size="small"
            @click="navigateTo('/report/index')"
          >
            直达执行报告
            <template #icon><IconArrowRight /></template>
          </a-button>
          <p class="mango-home-panel-description">按真实用例与场景数汇总最终执行质量</p>
          <StatusChart
            :success="data.reportStatus.success"
            :fail="data.reportStatus.fail"
            :warning="data.reportStatus.warning"
            :other="reportOtherCount"
            :loading="data.reportSumLoading"
            center-label="最终通过率"
            :center-value="formatPercent(data.reportPassRate)"
          />
        </div>
        <div class="item mango-section-card">
          <Title title="自动化能力建设" />
          <p class="mango-home-panel-description">前端、服务、脚本、数据工厂、测试配置与定时任务</p>
          <AutomationStats />
        </div>
      </div>
      <div class="center-workspace">
        <div class="trend-panel panel mango-section-card">
          <Title title="近 12 周自动化执行趋势" />
          <p class="mango-home-panel-description">UI、API、Pytest 的真实用例与场景执行规模</p>
          <FullYearSalesChart ref="fullYearSalesChart" />
        </div>
        <div class="center-bottom">
          <div class="pending-panel panel mango-section-card">
            <Title title="即将执行的定时任务" />
            <p class="mango-home-panel-description">按下一次触发时间排序，仅展示已启用任务</p>
            <div class="pending-card-body">
              <PendingTasks />
            </div>
          </div>
          <div class="activity-panel panel mango-section-card">
            <Title title="近 7 天用户活跃度" />
            <p class="mango-home-panel-description">衡量用户对测试平台的实际使用情况</p>
            <HotProductChart ref="hotProductChart" />
          </div>
        </div>
      </div>
      <div class="right-rail">
        <div class="todo-panel panel mango-section-card">
          <Title title="风险待办" :class="{ 'mango-risk-title--danger': hasPendingRisk }" />
          <p class="mango-home-panel-description">授权到期、刷新失败与数据模型异常</p>
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
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
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
  const router = useRouter()

  const data: any = reactive({
    projectQuality: [],
    reportStatus: {
      success: 0,
      fail: 0,
      warning: 0,
      proceed: 0,
      stay_begin: 0,
      stopped: 0,
    },
    reportPassRate: null,
    projectQualityLoading: false,
    reportSumLoading: false,
    onlineUsers: 0,
  })

  const reportOtherCount = computed(
    () =>
      Number(data.reportStatus.proceed || 0) +
      Number(data.reportStatus.stay_begin || 0) +
      Number(data.reportStatus.stopped || 0)
  )

  function projectQuality() {
    data.projectQualityLoading = true
    getSystemProjectQuality()
      .then((res) => {
        data.projectQuality = Array.isArray(res.data) ? res.data : []
      })
      .catch(console.log)
      .finally(() => {
        data.projectQualityLoading = false
      })
  }

  function getAllReportSum() {
    data.reportSumLoading = true
    getSystemCaseRunSum()
      .then((res) => {
        const payload = res.data || {}
        if (Array.isArray(payload)) {
          const legacy = Object.fromEntries(
            payload.map((item: any) => [String(item.name || ''), Number(item.value || 0)])
          )
          data.reportStatus = {
            success: legacy['通过'] || 0,
            fail: legacy['失败'] || 0,
            warning: legacy['警告'] || 0,
            proceed: legacy['进行中'] || 0,
            stay_begin: legacy['待开始'] || 0,
            stopped: legacy['已停止'] || 0,
          }
          const completed =
            data.reportStatus.success + data.reportStatus.fail + data.reportStatus.warning
          data.reportPassRate = completed
            ? Number(((data.reportStatus.success / completed) * 100).toFixed(2))
            : null
          return
        }
        data.reportStatus = {
          ...data.reportStatus,
          ...(payload.status_counts || {}),
        }
        data.reportPassRate = payload.final_pass_rate ?? null
      })
      .catch(console.log)
      .finally(() => {
        data.reportSumLoading = false
      })
  }

  function formatPercent(value: number | string | null | undefined) {
    if (value === null || value === undefined || value === '') return '-'
    const numberValue = Number(value)
    return Number.isFinite(numberValue) ? `${numberValue.toFixed(2)}%` : '-'
  }

  function navigateTo(path: string) {
    router.push(path)
  }

  onMounted(() => {
    nextTick(async () => {
      projectQuality()
      getAllReportSum()
    })
  })

  // 资源中心相关方法
  function downloadExecutor() {
    // 跳转到执行器下载链接
    window.open('https://www.alipan.com/s/8CmZdabwt4R', '_blank')
  }

  function viewSkill() {
    skillVisible.value = true
  }

  function viewHelp() {
    // 跳转到帮助文档链接
    window.open('http://43.142.161.61:8002/', '_blank')
  }

  function contactAuthor() {
    // 打开联系作者弹窗
    contactVisible.value = true
  }
</script>

<style lang="less" scoped>
  :deep(.title-container) {
    z-index: 1;
  }

  :deep(.arco-card) {
    border-radius: var(--m-radius-lg);
    border: 1px solid var(--m-border);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
    transition: box-shadow 0.3s ease;
  }

  :deep(.arco-card:hover) {
    box-shadow: var(--m-shadow);
  }

  :deep(.arco-card-body) {
    padding: 0;
    height: 100%;
  }

  :deep(.arco-modal) {
    .arco-modal-body {
      padding: 18px;
    }
  }

  .mango-home-workbench-scroll {
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
    min-width: 1064px;
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

  // 按钮样式优化
  :deep(.arco-btn) {
    border-radius: 5px;
    transition: all 0.3s ease;
  }

  :deep(.arco-btn:hover) {
    transform: translateY(-1px);
    box-shadow: var(--m-shadow);
  }

  // 描述列表样式优化
  :deep(.arco-descriptions) {
    .arco-descriptions-item-label {
      font-weight: 500;
      color: var(--m-muted);
    }

    .arco-descriptions-item-value {
      color: var(--m-text-2);
    }
  }

</style>
