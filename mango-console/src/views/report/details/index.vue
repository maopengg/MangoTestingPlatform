<template>
  <TableBody ref="tableBody">
    <template #default>
      <div class="test-report-container">
        <a-row :gutter="16" class="summary-cards">
          <a-col v-for="(item, index) in summaryCards" :key="index" class="summary-col">
            <a-card :class="['summary-card', item.class]">
              <template #title>
                <a-space>
                  <component :is="item.icon" />
                  <span>{{ item.title }}</span>
                </a-space>
              </template>
              <div class="card-content">
                <span class="number">{{ item.value }}</span>
                <span class="label">个</span>
              </div>
            </a-card>
          </a-col>
        </a-row>
        <a-row :gutter="16" class="chart-section">
          <a-col :span="8">
            <a-card title="测试套基础信息" class="info-card">
              <div class="chart-container">
                <a-space direction="vertical" style="width: 100%">
                  <div class="info-item">
                    <span class="info-label">测试套ID：</span>
                    <span class="info-value">{{ pageData.record.id }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">任务名称：</span>
                    <span class="info-value">{{ pageData.record.tasks?.name }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">执行时间：</span>
                    <span class="info-value">{{ pageData.record.create_time }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">测试环境：</span>
                    <span class="info-value">{{
                      enumStore.environment_type[pageData.record.test_env].title
                    }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">执行人：</span>
                    <span class="info-value">{{ pageData.record.user?.name }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">是否通知：</span>
                    <span class="info-value">{{
                      enumStore.status[pageData.record.is_notice].title
                    }}</span>
                  </div>
                </a-space>
              </div>
            </a-card>
          </a-col>

          <a-col :span="8">
            <a-card title="用例执行进度" class="progress-card">
              <div class="chart-container">
                <div class="progress-item">
                  <div class="progress-label">API测试 ({{ data.summary.api_count }})</div>
                  <a-progress
                    :percent="
                      data.summary.api_count > 0
                        ? (data.summary.api_in_progress_count / data.summary.api_count).toFixed(2)
                        : 0
                    "
                    :style="{ width: '80%' }"
                    :color="{
                      '0%': 'rgb(var(--primary-6))',
                      '100%': 'rgb(var(--success-6))',
                    }"
                    :stroke-width="8"
                  />
                </div>
                <div class="progress-item">
                  <div class="progress-label">UI测试 ({{ data.summary.ui_count }})</div>
                  <a-progress
                    :percent="
                      data.summary.ui_count > 0
                        ? (data.summary.ui_in_progress_count / data.summary.ui_count).toFixed(2)
                        : 0
                    "
                    :style="{ width: '80%' }"
                    :color="{
                      '0%': 'rgb(var(--primary-6))',
                      '100%': 'rgb(var(--success-6))',
                    }"
                    :stroke-width="8"
                  />
                </div>
                <div class="progress-item">
                  <div class="progress-label">Pytest测试 ({{ data.summary.pytest_count }})</div>
                  <a-progress
                    :percent="
                      data.summary.pytest_count > 0
                        ? (
                            data.summary.pytest_in_progress_count / data.summary.pytest_count
                          ).toFixed(2)
                        : 0
                    "
                    :style="{ width: '80%' }"
                    :color="{
                      '0%': 'rgb(var(--primary-6))',
                      '100%': 'rgb(var(--success-6))',
                    }"
                    :stroke-width="8"
                  />
                </div>
              </div>
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card title="测试结果分布图" class="result-card">
              <div class="chart-container">
                <StatusChart
                  :success="data.summary.success_count"
                  :fail="data.summary.fail_count"
                  :pending="data.summary.proceed_count"
                  :todo="data.summary.stay_begin_count"
                />
              </div>
            </a-card>
          </a-col>
        </a-row>

        <a-card class="test-details">
          <template #title>
            <a-space>
              <icon-unordered-list />
              <span>测试套用例列表</span>
              <span style="font-size: 12px; opacity: 0.7; margin-left: 4px"
                >请在左侧展开查看步骤结果</span
              >
            </a-space>
          </template>
          <template #extra>
            <a-space>
              <!--              <span  style="font-size: 16px; opacity: 0.6;  color: black ">只看某个状态</span>-->
              <a-button type="primary" size="small" @click="doRefresh(null)">全部</a-button>
              <a-button status="danger" size="small" @click="doRefresh(0)">失败</a-button>
              <a-button status="success" size="small" @click="doRefresh(1)">成功</a-button>
              <a-button status="warning" size="small" @click="doRefresh(2)">进行中</a-button>
              <a-button status="normal" size="small" @click="doRefresh(3)">待开始</a-button>
            </a-space>
          </template>
          <a-table
            :bordered="false"
            :loading="table.tableLoading.value"
            :data="table.dataList"
            :columns="tableColumns"
            :pagination="false"
            :row-key="rowKey"
            :expand-row-keys="expandedKeys"
          >
            <template #columns>
              <a-table-column title="ID" data-index="id">
                <template #cell="{ record }">
                  {{ record.id }}
                </template>
              </a-table-column>
              <a-table-column title="用例名称" data-index="case_name">
                <template #cell="{ record }">
                  {{ record.case_name }}
                </template>
              </a-table-column>
              <a-table-column title="测试类型" data-index="type">
                <template #cell="{ record }">
                  <a-tag :color="enumStore.colors[record?.type]" size="small" class="custom-tag"
                    >{{
                      record?.type || record.type === 0
                        ? enumStore.test_case_type[record?.type].title
                        : ''
                    }}
                  </a-tag>
                </template>
              </a-table-column>
              <a-table-column title="步骤名称" data-index="name" />
              <a-table-column title="测试结果" data-index="status">
                <template #cell="{ record }">
                  <a-tag
                    :color="enumStore.status_colors[record?.status]"
                    size="small"
                    class="custom-tag"
                  >
                    {{ enumStore.task_status[record?.status].title }}
                  </a-tag>
                </template>
              </a-table-column>
              <a-table-column title="操作" data-index="actions" :width="130" fixed="right">
                <template #cell="{ record }">
                  <a-space>
                    <a-button
                      v-if="record.children"
                      type="text"
                      size="mini"
                      @click="onRetry(record)"
                      >重试</a-button
                    >
                  </a-space>

                  <a-space>
                    <a-button
                      v-if="!record.children"
                      type="text"
                      size="mini"
                      @click="showDetails(record)"
                      >查看详细报告
                    </a-button>
                  </a-space>
                </template>
              </a-table-column>
            </template>
          </a-table>
          <TableFooter :pagination="pagination" />
        </a-card>

        <!-- 测试详情抽屉 -->
        <a-drawer
          v-model:visible="drawerVisible"
          :width="1000"
          title="测试用例详情"
          class="custom-drawer"
        >
          <template v-if="data.selectedCase">
            <a-descriptions :column="1" bordered class="custom-descriptions">
              <a-descriptions-item label="用例ID">{{ data.selectedCase?.id }}</a-descriptions-item>
              <a-descriptions-item label="用例名称"
                >{{ data.selectedCase?.name }}
              </a-descriptions-item>
              <a-descriptions-item label="项目名称"
                >{{ data.selectedCase?.project_product_name }}
              </a-descriptions-item>
              <a-descriptions-item label="执行状态">
                <a-tag
                  :color="enumStore.status_colors[data?.selectedCase?.status]"
                  size="small"
                  class="custom-tag"
                >
                  {{ enumStore?.task_status[data?.selectedCase?.status]?.title }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item v-if="data?.selectedCase?.status === 0" label="失败提示"
                >{{ data.selectedCase?.error_message }}
              </a-descriptions-item>
            </a-descriptions>
            <div class="report-cards">
              <div v-if="data.selectedCase.case_type === 0">
                <a-card :title="data?.selectedCase?.name" :bordered="false" class="report-card">
                  <ElementTestReport :resultData="data?.selectedCase" />
                </a-card>
              </div>
              <div v-else-if="data.selectedCase.case_type === 1">
                <a-card :title="data?.selectedCase?.name" :bordered="false" class="report-card">
                  <ApiTestReport :resultData="data?.selectedCase" />
                </a-card>
              </div>
              <div v-else-if="data.selectedCase.case_type === 2">
                <a-card :title="data?.selectedCase?.name" :bordered="false" class="report-card">
                  <PytestTestReport :resultData="data?.selectedCase">pytest</PytestTestReport>
                </a-card>
              </div>
            </div>
          </template>
        </a-drawer>
      </div>
    </template>
  </TableBody>
</template>
<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue'
  import { usePageData } from '@/store/page-data'
  import {
    getSystemTestSuiteDetails,
    getSystemTestSuiteDetailsRetry,
    getSystemTestSuiteDetailsSummary,
  } from '@/api/system/test_sute_details'
  import ElementTestReport from '@/components/ElementTestReport.vue'
  import ApiTestReport from '@/components/ApiTestReport.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import PytestTestReport from '@/components/PytestTestReport.vue'
  import {
    IconApps,
    IconCheckCircle,
    IconCloseCircle,
    IconHistory,
    IconSync,
    IconUnorderedList,
  } from '@arco-design/web-vue/es/icon'
  import { usePagination, useRowKey, useTable, useTableColumn } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'

  const pageData: any = usePageData()
  const pagination = usePagination(doRefresh)
  const drawerVisible = ref(false)
  const enumStore = useEnum()

  const table = useTable()
  const rowKey = useRowKey('id')
  const tableColumns = useTableColumn([
    table.indexColumn,
    {
      title: '用例名称',
      key: 'case_name',
      dataIndex: 'case_name',
    },
    {
      title: '测试类型',
      key: 'type',
      dataIndex: 'type',
    },
    {
      title: '步骤名称',
      key: 'name',
      dataIndex: 'name',
    },
    {
      title: '测试结果',
      key: 'status',
      dataIndex: 'status',
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      fixed: 'right',
      width: 130,
    },
  ])
  const data: any = reactive({
    dataList: [],
    summary: {},
    selectedCase: {},
  })

  const summaryCards = computed(() => [
    {
      title: '总用例数',
      value: data.summary.count,
      icon: IconApps,
      class: '',
    },
    {
      title: '待开始',
      value: data.summary.stay_begin_count,
      icon: IconHistory,
      class: 'wait',
    },
    {
      title: '进行中',
      value: data.summary.proceed_count,
      icon: IconSync,
      class: 'running',
    },
    {
      title: '成功用例',
      value: data.summary.success_count,
      icon: IconCheckCircle,
      class: 'success',
    },
    {
      title: '失败用例',
      value: data.summary.fail_count,
      icon: IconCloseCircle,
      class: 'error',
    },
  ])
  const expandedKeys = ref([])

  const showDetails = (record: any) => {
    data.selectedCase = record
    drawerVisible.value = true
  }

  function doRefresh(status = null) {
    let value = { test_suite_id: pageData.record.id }
    if (status !== null) {
      value['status'] = status
    }
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getSystemTestSuiteDetails(value)
      .then((res) => {
        data.datsList = res.data
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function doRefreshSummary() {
    getSystemTestSuiteDetailsSummary(pageData.record.id)
      .then((res) => {
        data.summary = res.data
      })
      .catch(console.log)
  }
  function onRetry(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要重试这个测试？',
      cancelText: '取消',
      okText: '重试',
      onOk: () => {
        getSystemTestSuiteDetailsRetry(record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
      },
    })
  }
  onMounted(() => {
    doRefresh(null)
    doRefreshSummary()

    // 添加测试数据以验证合并功能
    setTimeout(() => {
      console.log('表格数据:', table.dataList)
    }, 2000)
  })
</script>
<style lang="less" scoped>
  .summary-cards {
    display: flex;
    justify-content: space-between;
  }

  .summary-col {
    flex: 1;
    margin: 0 8px; /* 调整间距 */
  }

  .summary-col:first-child {
    margin-left: 0;
  }

  .summary-col:last-child {
    margin-right: 0;
  }

  .test-report-container {
    padding: 5px;
    min-height: 102vh;
  }

  // 卡片通用样式
  :deep(.arco-card) {
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    transition: all 0.3s ease;
    overflow: hidden;
    border: none;

    &:hover {
      transform: translateY(-5px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
    }

    .arco-card-header {
      border-bottom: 1px solid rgba(0, 0, 0, 0.05);
      padding: 16px 20px;
      font-weight: 600;
      font-size: 16px;
    }

    .arco-card-body {
      padding: 20px;
    }
  }

  // 摘要卡片
  .summary-cards {
    margin-bottom: 16px;
  }

  .summary-card {
    height: 100%;

    .arco-card-header {
      background: rgba(0, 0, 0, 0.02);
    }
  }

  .card-content {
    text-align: center;
    padding: 24px 0;
  }

  .number {
    font-size: 42px;
    font-weight: bold;
    margin-right: 8px;
    background: linear-gradient(45deg, #1890ff, #52c41a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .label {
    font-size: 16px;
    color: #86909c;
  }

  .success {
    :deep(.arco-card-header) {
      color: #52c41a;
      background: rgba(82, 196, 26, 0.1);
    }

    .number {
      background: linear-gradient(45deg, #52c41a, #95de64);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
  }

  .running {
    :deep(.arco-card-header) {
      color: #d46b08;
      background: rgba(255, 247, 232, 3);
    }

    .number {
      background: linear-gradient(45deg, #d46b08, #ffa940);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
  }

  .error {
    :deep(.arco-card-header) {
      color: #f5222d;
      background: rgba(245, 34, 45, 0.1);
    }

    .number {
      background: linear-gradient(45deg, #f5222d, #ff7875);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
  }

  .wait {
    :deep(.arco-card-header) {
      color: #1890ff;
      background: rgba(24, 144, 255, 0.05);
    }

    .number {
      background: linear-gradient(45deg, #1890ff, #69c0ff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
  }

  .chart-section {
    margin-bottom: 16px;
  }

  .chart-container {
    min-height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 1px;
  }

  .info-card {
    .chart-container {
      align-items: flex-start;
    }
  }

  .info-item {
    margin-bottom: 5px;
    display: flex;
    align-items: center;
    padding: 4px 8px;
    border-radius: 4px;
    background: rgba(0, 0, 0, 0.02);
    transition: all 0.3s ease;

    &:hover {
      background: rgba(0, 0, 0, 0.04);
      transform: translateX(5px);
    }
  }

  .info-value {
    color: #4e5969;
  }

  // 进度条卡片
  .progress-card {
    .progress-item {
      margin-bottom: 36px;
      width: 100%;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .progress-label {
      margin-bottom: 16px;
      font-size: 14px;
      font-weight: 600;
      color: #1d2129;
    }

    :deep(.arco-progress) {
      border-radius: 8px;
      overflow: hidden;

      .arco-progress-line-path {
        transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
      }

      .arco-progress-line-text {
        font-weight: 600;
      }
    }
  }

  .result-card {
    :deep(.arco-progress-circle) {
      .arco-progress-circle-path {
        stroke-linecap: round;
        transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
      }
    }
  }

  .circle-progress-text {
    text-align: center;

    .progress-title {
      font-size: 16px;
      color: #86909c;
      margin-bottom: 4px;
    }

    .progress-value {
      font-size: 24px;
      font-weight: bold;
      color: #52c41a;
    }
  }

  // 抽屉样式
  .custom-drawer {
    :deep(.arco-drawer-header) {
      border-bottom: 1px solid rgba(0, 0, 0, 0.05);
      padding: 16px 24px;
    }

    :deep(.arco-drawer-body) {
      padding: 24px;
    }
  }

  .custom-descriptions {
    margin-bottom: 24px;

    :deep(.arco-descriptions-item-label) {
      background-color: rgba(var(--primary-1), 0.3);
      font-weight: 600;
    }

    :deep(.arco-descriptions-item-value) {
      padding: 8px 12px;
    }
  }

  .report-cards {
    margin-top: 8px;
  }

  .report-card {
    margin-bottom: 12px;
  }

  // 表格样式
  :deep(.arco-table) {
    .expand-icon {
      cursor: pointer;
      margin-right: 8px;
      color: rgb(var(--primary-6));

      &:hover {
        opacity: 0.8;
      }
    }

    .arco-table-tr-expand {
      background-color: rgba(var(--primary-1), 0.1);
    }

    .arco-table-cell {
      vertical-align: middle;
    }

    .arco-table-th {
      background-color: rgba(var(--primary-1), 0.2);
      font-weight: 600;
    }

    .arco-table-tr {
      &:hover {
        .arco-table-td {
          background-color: rgba(var(--primary-1), 0.1);
        }
      }
    }

    .arco-table-td {
      transition: background-color 0.3s;

      &[rowspan] {
        background-color: rgba(var(--primary-1), 0.05);
        border-left: 2px solid rgb(var(--primary-6));
      }
    }
  }
</style>
