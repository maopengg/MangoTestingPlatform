<template>
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
                    ? Number(
                        (data.summary.api_in_progress_count / data.summary.api_count).toFixed(2)
                      )
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
                    ? Number((data.summary.ui_in_progress_count / data.summary.ui_count).toFixed(2))
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
                    ? Number(
                        (data.summary.pytest_in_progress_count / data.summary.pytest_count).toFixed(
                          2
                        )
                      )
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

    <a-card class="test-details" body-style="padding: 0 20px 20px 20px">
      <template #title>
        <icon-unordered-list />
        <span>测试套用例列表</span>
      </template>
      <a-tabs @tab-click="(key) => doRefresh(key)">
        <template #extra>
          <a-space>
            <a-button type="primary" size="small" :loading="caseRunning" @click="doCaseStatus(null)"
              >全部</a-button
            >
            <a-button status="danger" size="small" :loading="caseRunning" @click="doCaseStatus(0)"
              >只看失败</a-button
            >
            <a-button status="success" size="small" :loading="caseRunning" @click="doCaseStatus(1)"
              >只看成功</a-button
            >
            <a-button status="warning" size="small" :loading="caseRunning" @click="doCaseStatus(2)"
              >只看进行中</a-button
            >
            <a-button status="normal" size="small" :loading="caseRunning" @click="doCaseStatus(3)"
              >只看待开始</a-button
            >
          </a-space>
        </template>
        <a-tab-pane
          key="0"
          :title="'UI测试（' + data.summary.ui_count + '）'"
          v-if="data.summary.ui_count > 0"
        >
          <a-collapse
            :default-active-key="[1]"
            :bordered="false"
            v-for="item of data.dataList"
            :key="item.id"
            accordion
            destroy-on-hide
          >
            <a-collapse-item key="1">
              <template #header>
                <div class="custom-header">
                  <span>{{ item.case_name }}</span>
                  <span style="width: 20px"></span>
                  <a-tag :color="enumStore.status_colors[item.status]"
                    >{{ enumStore.task_status[item.status].title }}
                  </a-tag>
                </div>
              </template>
              <template #extra>
                       <a-button
                          type="text"
                          size="mini"
                          @click="onRetry(item.id)"
                          >重试
                        </a-button>
      </template>

                ><template #columns>
                  <a-table-column title="步骤ID" data-index="id">
                    <template #cell="{ record }">
                      {{ record.id }}
                    </template>
                  </a-table-column>
                  <a-table-column title="产品名称" data-index="project_product_name">
                    <template #cell="{ record }">
                      {{ record.project_product_name }}
                    </template>
                  </a-table-column>
                  <a-table-column title="步骤名称" data-index="name">
                    <template #cell="{ record }">
                      {{ record.name }}
                    </template>
                  </a-table-column>
                  <a-table-column title="开始时间" data-index="test_time">
                    <template #cell="{ record }">
                      {{ record?.test_time }}
                    </template>
                  </a-table-column>
                  <a-table-column title="结束时间" data-index="stop_time">
                    <template #cell="{ record }">
                      {{ record?.stop_time }}
                    </template>
                  </a-table-column>
                  <a-table-column title="测试环境" data-index="test_object">
                    <template #cell="{ record }">
                      {{ record?.test_object }}
                    </template>
                  </a-table-column>
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
                  <a-table-column title="失败提示" data-index="error_message">
                    <template #cell="{ record }">
                      {{ record.error_message }}
                    </template>
                  </a-table-column>
                  <a-table-column title="操作" data-index="actions" :width="130" fixed="right">
                    <template #cell="{ record }">
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
                </template></a-table
              >
            </a-collapse-item>
          </a-collapse>
        </a-tab-pane>
        <a-tab-pane
          key="1"
          :title="'API测试（' + data.summary.api_count + '）'"
          v-if="data.summary.api_count > 0"
        >
          <a-collapse
            :default-active-key="[1]"
            :bordered="false"
            v-for="item of data.dataList"
            :key="item.id"
            accordion
            destroy-on-hide
            style="padding: 0 0 0 0"
          >
            <a-collapse-item :header="item.case_name" key="1">
              <template #header>
                <div class="custom-header">
                  <span>{{ item.case_name }}</span>
                  <span style="width: 20px"></span>
                  <a-tag :color="enumStore.status_colors[item.status]"
                    >{{ enumStore.task_status[item.status].title }}
                  </a-tag>
                </div>
              </template>
                            <template #extra>
                       <a-button
                          type="text"
                          size="mini"
                          @click="onRetry(item.id)"
                          >重试
                        </a-button>
      </template>
              <a-table :columns="apiColumns" :data="item.children" :pagination="false"
                ><template #columns>
                  <a-table-column title="接口ID" data-index="id">
                    <template #cell="{ record }">
                      {{ record.id }}
                    </template>
                  </a-table-column>
                  <a-table-column title="产品名称" data-index="project_product_name">
                    <template #cell="{ record }">
                      {{ record.project_product_name }}
                    </template>
                  </a-table-column>
                  <a-table-column title="接口名称" data-index="name">
                    <template #cell="{ record }">
                      {{ record.name }}
                    </template>
                  </a-table-column>
                  <a-table-column title="测试环境" data-index="request_url">
                    <template #cell="{ record }">
                      {{ record?.request?.url }}
                    </template>
                  </a-table-column>
                  <a-table-column title="耗时" data-index="response_time">
                    <template #cell="{ record }">
                      {{ record?.response?.time }}
                    </template>
                  </a-table-column>
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
                  <a-table-column title="失败提示" data-index="error_message">
                    <template #cell="{ record }">
                      {{ record.error_message }}
                    </template>
                  </a-table-column>
                  <a-table-column title="操作" data-index="actions" :width="130" fixed="right">
                    <template #cell="{ record }">
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
                </template></a-table
              >
            </a-collapse-item>
          </a-collapse>
        </a-tab-pane>
        <a-tab-pane
          key="2"
          :title="'Pytest测试（' + data.summary.pytest_count + '）'"
          v-if="data.summary.pytest_count > 0"
        >
          <a-collapse
            :default-active-key="[1]"
            :bordered="false"
            v-for="item of data.dataList"
            :key="item.id"
            accordion
            destroy-on-hide
            style="padding: 0 0 0 0"
          >
            <a-collapse-item :header="item.case_name" key="1">
              <template #header>
                <div class="custom-header">
                  <span>{{ item.case_name }}</span>
                  <span style="width: 20px"></span>
                  <a-tag :color="enumStore.status_colors[item.status]"
                    >{{ enumStore.task_status[item.status].title }}
                  </a-tag>
                </div>
              </template>
                            <template #extra>
                       <a-button
                          type="text"
                          size="mini"
                          @click="onRetry(item.id)"
                          >重试
                        </a-button>
      </template>
              <a-table :columns="pytestColumns" :data="item.children" :pagination="false"
                ><template #columns>
                  <a-table-column title="产品名称" data-index="project_product_name">
                    <template #cell="{ record }">
                      {{ item.project_product.name }}
                    </template>
                  </a-table-column>
                  <a-table-column title="用例名称" data-index="name">
                    <template #cell="{ record }">
                      {{ record.name }}
                    </template>
                  </a-table-column>
                  <a-table-column title="开始时间" data-index="start">
                    <template #cell="{ record }">
                      {{ formatDateTime(record.start) }}
                    </template>
                  </a-table-column>
                  <a-table-column title="结束时间" data-index="stop">
                    <template #cell="{ record }">
                      {{ formatDateTime(record.stop) }}
                    </template>
                  </a-table-column>
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
                          v-if="!record.children"
                          type="text"
                          size="mini"
                          @click="showDetails(record)"
                          >查看详细报告
                        </a-button>
                      </a-space>
                    </template>
                  </a-table-column>
                </template></a-table
              >
            </a-collapse-item>
          </a-collapse>
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <!-- 测试详情抽屉 -->
    <a-drawer
      v-model:visible="drawerVisible"
      :width="1000"
      title="测试用例详情"
      class="custom-drawer"
    >
      <template v-if="data.selectedCase">
        <div>
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
  import { Message, Modal } from '@arco-design/web-vue'
  import { apiColumns, pytestColumns, uiColumns } from '@/views/report/details/config'

  const pageData: any = usePageData()
  const drawerVisible = ref(false)
  const enumStore = useEnum()

  const data: any = reactive({
    dataList: [],
    summary: {},
    selectedCase: {},
    caseStatus: null,
  })
  const caseRunning = ref(false)

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
  function formatDateTime(timestamp) {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  }
  const showDetails = (record: any) => {
    data.selectedCase = record
    drawerVisible.value = true
  }
  // 修改doCaseStatus函数
  const doCaseStatus = async (key) => {
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      data.caseStatus = key
      await doRefresh(data.caseType) // 添加await等待异步操作完成
    } catch (e) {
      Message.error(e?.msg || e?.message || '用例执行失败')
    } finally {
      caseRunning.value = false
    }
  }

  // 修改doRefresh函数，让它返回Promise
  function doRefresh(type = null) {
    data.caseType = type
    let value = { test_suite_id: pageData.record.id }
    if (data.caseStatus !== null) {
      value['status'] = data.caseStatus
    }
    if (data.caseType !== null) {
      value['type'] = data.caseType
    } else if (data.summary?.ui_count > 0) {
      value['type'] = 0
    } else if (data.summary.api_count > 0) {
      value['type'] = 1
    } else if (data.summary.pytest_count > 0) {
      value['type'] = 2
    }
    value['page'] = 1
    value['pageSize'] = 10000

    // 返回Promise
    return new Promise((resolve, reject) => {
      getSystemTestSuiteDetails(value)
        .then((res) => {
          data.dataList = res.data
          resolve(res)
        })
        .catch((error) => {
          console.log(error)
          reject(error)
        })
    })
  }

  function doRefreshSummary() {
    getSystemTestSuiteDetailsSummary(pageData.record.id)
      .then((res) => {
        data.summary = res.data
        doRefresh(null)
      })
      .catch(console.log)
  }

  function onRetry(case_id: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要重试这个测试？',
      cancelText: '取消',
      okText: '重试',
      onOk: () => {
        getSystemTestSuiteDetailsRetry(case_id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
      },
    })
  }

  onMounted(() => {
    doRefreshSummary()
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
    margin-bottom: 8px;
  }

  .summary-card {
    height: 100%;

    .arco-card-header {
      background: rgba(0, 0, 0, 0.02);
    }
  }

  .card-content {
    text-align: center;
    padding: 6px 0;
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
    margin-bottom: 8px;
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
  .custom-header {
    display: flex;
    align-items: center;
    gap: 12px; /* 控制标签间距 */
    font-size: 14px;
  }
</style>
