<template>
  <div class="main-container">
    <div class="left">
      <div class="item">
        <Title title="用例占比" />
        <PieChart :chartData="data.caseSum" :loading="data.caseSumLoading" />
      </div>
      <div class="item">
        <Title title="执行占比" />
        <PieChart :chartData="data.reportSum" :loading="data.reportSumLoading" />
      </div>
      <div class="item">
        <Title title="自动化测试统计" />
        <!-- 组件自己获取所需数据 -->
        <AutomationStats />
      </div>
    </div>
    <div class="center-workspace">
      <div class="trend-panel panel">
        <Title title="近3个月执行趋势图" />
        <FullYearSalesChart ref="fullYearSalesChart" />
      </div>
      <div class="center-bottom">
        <div class="pending-panel panel compact-panel">
          <Title title="待执行自动化任务" />
          <div class="pending-card-body">
            <PendingTasks />
          </div>
        </div>
        <div class="activity-panel panel compact-panel">
          <Title title="活跃度" />
          <HotProductChart ref="hotProductChart" />
        </div>
      </div>
    </div>
    <div class="right-rail">
      <div class="resource-panel panel compact-panel">
        <Title title="资源中心" />
        <ResourceCenter
          @download-executor="downloadExecutor"
          @download-plugin="downloadPlugin"
          @view-help="viewHelp"
          @contact-author="contactAuthor"
        />
      </div>
      <div class="mcp-panel panel feature-panel">
        <Title title="MCP智能接入" />
        <McpWorkbench />
      </div>
    </div>
  </div>

  <!-- 联系作者弹窗 -->
  <ContactAuthor v-model:visible="contactVisible" />
</template>

<script lang="ts" setup>
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import FullYearSalesChart from './components/chart/FullYearSalesChart.vue'
  import HotProductChart from './components/chart/HotProductChart.vue'
  import Title from '@/views/index/components/Title.vue'
  import PieChart from '@/components/chart/PieChart.vue'
  import { getSystemCaseRunSum, getSystemCaseSum } from '@/api/system'
  import ContactAuthor from './components/ContactAuthor.vue'
  import AutomationStats from './components/AutomationStats.vue'
  import PendingTasks from './components/PendingTasks.vue'
  import ResourceCenter from './components/ResourceCenter.vue'
  import McpWorkbench from './components/McpWorkbench.vue'

  const contactVisible = ref(false)

  const data: any = reactive({
    caseSum: [],
    reportSum: [],
    caseSumLoading: false,
    reportSumLoading: false,
    onlineUsers: 0,
  })

  function caseSum() {
    data.caseSumLoading = true
    getSystemCaseSum()
      .then((res) => {
        data.caseSum = res.data
      })
      .catch(console.log)
      .finally(() => {
        data.caseSumLoading = false
      })
  }

  function getAllReportSum() {
    data.reportSumLoading = true
    getSystemCaseRunSum()
      .then((res) => {
        data.reportSum = res.data
      })
      .catch(console.log)
      .finally(() => {
        data.reportSumLoading = false
      })
  }

  onMounted(() => {
    nextTick(async () => {
      caseSum()
      getAllReportSum()
    })
  })

  // 资源中心相关方法
  function downloadExecutor() {
    // 跳转到执行器下载链接
    window.open('https://www.alipan.com/s/8CmZdabwt4R', '_blank')
  }

  function downloadPlugin() {
    // 跳转到插件下载链接
    window.open('https://www.alipan.com/s/dEaiFz5Zvfq', '_blank')
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
    border-radius: 8px;
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
      padding: 20px;
    }
  }

  .main-container {
    display: grid;
    height: 100%;
    min-height: 0;
    grid-template-columns: minmax(360px, 420px) minmax(0, 1fr) minmax(340px, 400px);
    gap: 15px;
    overflow: hidden;
    padding: 15px;

    .panel {
      display: flex;
      min-height: 0;
      flex-direction: column;
      position: relative;
      border-radius: 8px;
      border: 1px solid var(--m-border);
      background: var(--m-surface);
      box-shadow: var(--m-shadow);
      padding: 10px 12px 12px;
      transition: box-shadow 0.2s cubic-bezier(0, 0, 1, 1);
    }

    .compact-panel {
      padding: 8px 10px 10px;
    }

    .feature-panel {
      padding: 10px 12px;
    }

    .left {
      display: flex;
      min-width: 0;
      min-height: 0;
      flex-direction: column;
      gap: 15px;

      .item {
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        min-height: 0;
        position: relative;
        border: 1px solid var(--m-border);
        background: var(--m-surface);
        transition: box-shadow 0.2s cubic-bezier(0, 0, 1, 1);
        box-shadow: var(--m-shadow);
        padding: 12px;

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
      min-width: 0;
      min-height: 0;
      grid-template-rows: 360px minmax(0, 1fr);
      gap: 15px;
    }

    .trend-panel {
      overflow: hidden;
    }

    .center-bottom {
      display: grid;
      min-height: 0;
      grid-template-columns: minmax(0, 1fr) 280px;
      gap: 15px;
    }

    .pending-panel {
      overflow: hidden;
    }

    .pending-card-body {
      flex: 1;
      min-height: 0;
      padding-top: 8px;
    }

    .right-rail {
      display: grid;
      min-width: 0;
      min-height: 0;
      grid-template-rows: 190px minmax(0, 1fr);
      gap: 15px;
    }

    .resource-panel,
    .mcp-panel {
      overflow: hidden;
    }

    .activity-panel {
      overflow: hidden;
    }

    .activity-panel :deep(.chart-item-container) {
      flex: 1;
      min-height: 0;
    }
  }

  @media (max-width: 1440px) {
    .main-container {
      grid-template-columns: minmax(300px, 0.9fr) minmax(360px, 1.22fr) minmax(280px, 0.82fr);
      gap: 10px;
      padding: 10px;

      .panel {
        padding: 8px 10px 10px;
      }

      .compact-panel,
      .feature-panel {
        padding: 8px;
      }

      .left {
        gap: 10px;

        .item {
          padding: 9px;
        }
      }

      .center-workspace {
        grid-template-rows: 320px minmax(0, 1fr);
        gap: 10px;
      }

      .center-bottom {
        grid-template-columns: minmax(0, 1fr) minmax(210px, 240px);
        gap: 10px;
      }

      .right-rail {
        grid-template-rows: 168px minmax(0, 1fr);
        gap: 10px;
      }
    }
  }

  @media (max-width: 1280px) {
    .main-container {
      grid-template-columns: minmax(270px, 0.85fr) minmax(320px, 1.2fr) minmax(240px, 0.75fr);
      gap: 8px;
      padding: 8px;

      .left {
        gap: 8px;

        .item {
          padding: 8px;
        }
      }

      .center-workspace {
        grid-template-rows: 300px minmax(0, 1fr);
        gap: 8px;
      }

      .center-bottom {
        grid-template-columns: minmax(0, 1fr) minmax(180px, 210px);
        gap: 8px;
      }

      .right-rail {
        grid-template-rows: 150px minmax(0, 1fr);
        gap: 8px;
      }
    }
  }

  @media (max-height: 820px) {
    .main-container {
      gap: 10px;
      padding: 10px;

      .left {
        gap: 10px;

        .item {
          padding: 8px;
        }
      }

      .center-workspace {
        grid-template-rows: 300px minmax(0, 1fr);
        gap: 10px;
      }

      .right-rail {
        grid-template-rows: 158px minmax(0, 1fr);
        gap: 10px;
      }
    }
  }

  @media (max-height: 760px) {
    .main-container {
      gap: 8px;
      padding: 8px;

      .center-workspace {
        grid-template-rows: 270px minmax(0, 1fr);
        gap: 8px;
      }

      .right-rail {
        grid-template-rows: 138px minmax(0, 1fr);
        gap: 8px;
      }
    }
  }

  // 按钮样式优化
  :deep(.arco-btn) {
    border-radius: 6px;
    transition: all 0.3s ease;
  }

  :deep(.arco-btn:hover) {
    transform: translateY(-2px);
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

  // 首页作为后台工作台页面，低于全局最小工作区宽度后不再降级为移动布局。
  @media (max-width: 1px) {
    .main-container {
      height: auto;
      min-height: 100%;
      grid-template-columns: 1fr;
      grid-template-rows: auto;
      overflow: auto;

      .left,
      .center-workspace,
      .trend-panel,
      .pending-panel,
      .mcp-panel,
      .right-rail {
        grid-column: 1;
        grid-row: auto;
      }

      .left {
        flex-direction: row;

        .item {
          flex: 1;
          min-height: 260px;
        }
      }

      .trend-panel {
        min-height: 420px;
      }

      .pending-panel,
      .mcp-panel {
        min-height: 260px;
      }

      .center-workspace,
      .right-rail {
        grid-template-rows: auto;
      }
    }
  }

  @media (max-width: 1px) {
    .main-container {
      padding: 10px;
      gap: 10px;

      .left {
        flex-direction: column;

        .item {
          flex: 1;
        }
      }

      .center-bottom {
        grid-template-columns: 1fr;
      }
    }
  }
</style>
