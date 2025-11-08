<template>
  <div class="main-container">
    <div class="left">
      <div class="item">
        <Title title="用例占比" />
        <PieChart :chartData="data.caseSum" />
      </div>
      <div class="item">
        <Title title="执行占比" />
        <PieChart :chartData="data.reportSum" />
      </div>
      <div class="item">
        <Title title="自动化测试统计" />
        <AutomationStats
          :ui-stats="data.uiStats"
          :api-stats="data.apiStats"
          :pytest-stats="data.pytestStats"
        />
      </div>
    </div>
    <div class="center">
      <div style="display: flex; flex-direction: column; height: 100%">
        <a-space direction="vertical" style="height: 100%; display: flex; flex-direction: column">
          <a-card style="flex: 1; overflow: hidden">
            <div style="display: flex; flex-direction: column; height: 100%">
              <Title title="近3个月执行趋势图" />
              <FullYearSalesChart ref="fullYearSalesChart" />
            </div>
          </a-card>
          <a-card style="flex: 1; overflow: hidden; display: flex; flex-direction: column">
            <div style="flex: 0 0 auto">
              <Title title="正在准备执行的自动化任务" />
            </div>
            <PendingTasks
              :data-list="table.dataList"
              :loading="table.tableLoading.value"
              :table-columns="tableColumns"
              @selection-change="onSelectionChange"
              @view-result="handleViewResult"
            />
          </a-card>
        </a-space>
      </div>
    </div>
    <div class="right">
      <div class="item">
        <Title title="资源中心" />
        <ResourceCenter
          @download-executor="downloadExecutor"
          @download-plugin="downloadPlugin"
          @view-help="viewHelp"
          @contact-author="contactAuthor"
        />
      </div>
      <div class="item">
        <Title title="活跃度" />
        <HotProductChart ref="hotProductChart" />
      </div>
    </div>
  </div>

  <!-- 联系作者弹窗 -->
  <ContactAuthor v-model:visible="contactVisible" />
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive, ref, unref, watch } from 'vue'
  import useAppConfigStore from '@/store/modules/app-config'
  import FullYearSalesChart from './components/chart/FullYearSalesChart.vue'
  import HotProductChart from './components/chart/HotProductChart.vue'
  import Title from '@/views/index/components/Title.vue'
  import { useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
  import { useRouter } from 'vue-router'
  import { getSystemTasks } from '@/api/system/tasks'
  import { useEnum } from '@/store/modules/get-enum'
  import PieChart from '@/components/chart/PieChart.vue'
  import { getSystemCaseRunSum, getSystemCaseSum } from '@/api/system'
  import { Message } from '@arco-design/web-vue'

  // 导入新创建的组件
  import ContactAuthor from './components/ContactAuthor.vue'
  import AutomationStats from './components/AutomationStats.vue'
  import PendingTasks from './components/PendingTasks.vue'
  import ResourceCenter from './components/ResourceCenter.vue'

  const appStore = useAppConfigStore()

  // 联系作者弹窗相关状态
  const contactVisible = ref(false)

  const enumStore = useEnum()
  const hotProductChart = ref()
  const fullYearSalesChart = ref()
  const onResize = () => {
    setTimeout(() => {
      unref(hotProductChart).updateChart()
      unref(fullYearSalesChart).updateChart()
    }, 500)
  }
  const collapse = computed(() => {
    return appStore.isCollapse
  })
  watch(collapse, () => {
    onResize()
  })

  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const data: any = reactive({
    caseSum: [],
    reportSum: [],
    onlineUsers: 0,
    // UI自动化统计
    uiStats: {
      elementCount: 0,
      pageCount: 0,
      stepCount: 0,
      caseCount: 0,
    },
    // API自动化统计
    apiStats: {
      interfaceCount: 0,
      caseCount: 0,
      headersCount: 0,
    },
    // Pytest自动化统计
    pytestStats: {
      processObjects: 0,
      caseCount: 0,
      toolFiles: 0,
      testFiles: 0,
    },
  })
  const tableColumns = useTableColumn([
    table.indexColumn,
    {
      title: '任务名称',
      key: 'name',
      dataIndex: 'name',
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '定时策略',
      key: 'timing_strategy',
      dataIndex: 'timing_strategy',
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '测试对象',
      key: 'test_env',
      dataIndex: 'test_env',
      width: 100,
    },
    {
      title: '负责人',
      key: 'case_people',
      dataIndex: 'case_people',
      width: 120,
    },
  ])
  const router = useRouter()

  function handleViewResult(record: any) {
    router.push({
      path: '/index/report-details',
      query: {
        id: record.id,
        name: record.name,
        type: record.type,
      },
    })
  }

  function goToCreateCase() {
    router.push('/apitest/case/create')
  }

  function goToTaskManagement() {
    router.push('/system/tasks')
  }

  function goToReportCenter() {
    router.push('/index/report')
  }

  function doRefresh() {
    getSystemTasks({
      pageSize: 100,
      page: 1,
    })
      .then((res) => {
        table.handleSuccess(res)
        caseSum()
        getAllReportSum()
        getSystemStatistics()
      })
      .catch(console.log)
  }

  function caseSum() {
    getSystemCaseSum()
      .then((res) => {
        data.caseSum = res.data
      })
      .catch(console.log)
  }

  function getAllReportSum() {
    getSystemCaseRunSum()
      .then((res) => {
        data.reportSum = res.data
      })
      .catch(console.log)
  }

  // 获取系统统计数据
  function getSystemStatistics() {
    // 这里可以添加实际的API调用来获取统计数据
    // 暂时使用模拟数据

    // UI自动化统计
    data.uiStats.elementCount = 128
    data.uiStats.pageCount = 24
    data.uiStats.stepCount = 86
    data.uiStats.caseCount = 86

    // API自动化统计
    data.apiStats.interfaceCount = 42
    data.apiStats.caseCount = 38
    data.apiStats.headersCount = 15

    // Pytest自动化统计
    data.pytestStats.processObjects = 12
    data.pytestStats.caseCount = 56
    data.pytestStats.toolFiles = 8
    data.pytestStats.testFiles = 22
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
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
    border: none;
    box-shadow: 0px 8px 16px 0px rgba(162, 173, 200, 0.2);
    transition: box-shadow 0.3s ease;
  }

  :deep(.arco-card:hover) {
    box-shadow: 0px 12px 20px 0px rgba(162, 173, 200, 0.3);
  }

  :deep(.arco-card-body) {
    padding: 0;
    height: 100%;
  }

  :deep(.arco-modal) {
    .arco-modal-body {
      padding: 20px;
    }

    .arco-modal-footer {
      text-align: center;
    }
  }

  .main-container {
    display: flex;
    height: 100%;
    overflow: hidden;
    gap: 15px;
    padding: 15px;

    .left {
      width: 25%;
      display: flex;
      flex-direction: column;
      gap: 15px;

      .item {
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        height: 100%;
        position: relative;
        background: var(--color-bg-2);
        transition: box-shadow 0.2s cubic-bezier(0, 0, 1, 1);
        box-shadow: 0px 8px 8px 0px rgba(162, 173, 200, 0.15);
        padding: 12px;

        div:nth-last-child(1) {
          flex: 1;
        }
      }

      .item + .item {
        margin-top: 0;
      }
    }

    .center {
      flex: 1;
      overflow: hidden;

      :deep(.arco-space) {
        height: 100%;
        display: flex;
        flex-direction: column;
      }

      :deep(.arco-card) {
        border-radius: 8px;
        flex: 1;
      }

      :deep(.arco-card:first-child) {
        margin-bottom: 20px;
      }

      // 移除额外的margin-bottom
      :deep(.arco-card:last-child) {
        margin-bottom: 6px;
      }
    }

    .right {
      width: 25%;
      display: flex;
      height: 100%;
      overflow: hidden;
      flex-direction: column;
      gap: 15px;

      & > div:nth-child(1) {
        flex: 0.5;
      }

      & > div:nth-child(2) {
        flex: 2.5;
        overflow: hidden;
      }

      .item {
        display: flex;
        flex-direction: column;
        height: 100%;
        position: relative;
        background: var(--color-bg-2);
        border-radius: 8px;
        transition: box-shadow 0.2s cubic-bezier(0, 0, 1, 1);
        box-shadow: 0px 8px 8px 0px rgba(162, 173, 200, 0.15);
        padding: 10px;

        & > div:nth-child(2) {
          flex: 1;
        }
      }

      .item + .item {
        margin-top: 0;
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
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }

  // 描述列表样式优化
  :deep(.arco-descriptions) {
    .arco-descriptions-item-label {
      font-weight: 500;
      color: #666;
    }

    .arco-descriptions-item-value {
      color: #333;
    }
  }

  // 响应式设计
  @media (max-width: 1200px) {
    .main-container {
      flex-direction: column;

      .left,
      .center,
      .right {
        width: 100%;
      }

      .left,
      .right {
        flex-direction: row;

        .item {
          flex: 1;
        }
      }
    }
  }

  @media (max-width: 768px) {
    .main-container {
      padding: 10px;
      gap: 10px;

      .left,
      .right {
        flex-direction: column;

        .item {
          flex: 1;
        }
      }

      .center {
        :deep(.arco-card:first-child) {
          margin-bottom: 10px;
        }
      }
    }
  }
</style>
