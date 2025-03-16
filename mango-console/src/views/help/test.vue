<template>
  <div class="test-report-container">
    <a-row :gutter="2" class="summary-cards">
      <a-col :span="6" v-for="(item, index) in summaryCards" :key="index">
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

    <a-row :gutter="2" class="chart-section">
      <a-col :span="8">
        <a-card title="基础信息">
          <div class="chart-container">
            <div class="progress-item">
              <div class="progress-label">API测试 ({{ data.summary.api_count }})：</div>
              <a-progress
                :percent="data.summary.api_in_progress_count / data.summary.api_count"
                :style="{ width: '50%' }"
                :color="{
                  '0%': 'rgb(var(--primary-6))',
                  '100%': 'rgb(var(--success-6))',
                }"
              />
            </div>
            <div class="progress-item">
              <div class="progress-label">UI测试 ({{ data.summary.ui_count }})</div>
              <a-progress
                :percent="data.summary.ui_in_progress_count / data.summary.ui_count"
                :style="{ width: '50%' }"
                :color="{
                  '0%': 'rgb(var(--primary-6))',
                  '100%': 'rgb(var(--success-6))',
                }"
              />
            </div>
            <div class="progress-item">
              <div class="progress-label">Pytest测试 ({{ data.summary.pytest_count }})</div>
              <a-progress
                :percent="data.summary.pytest_in_progress_count / data.summary.pytest_count"
                :style="{ width: '50%' }"
                :color="{
                  '0%': 'rgb(var(--primary-6))',
                  '100%': 'rgb(var(--success-6))',
                }"
              />
            </div>
          </div>
        </a-card>
      </a-col>

      <a-col :span="8">
        <a-card title="测试进度">
          <div class="chart-container">
            <div class="progress-item">
              <div class="progress-label">API测试 ({{ data.summary.api_count }})：</div>
              <a-progress
                :percent="data.summary.api_in_progress_count / data.summary.api_count"
                :style="{ width: '50%' }"
                :color="{
                  '0%': 'rgb(var(--primary-6))',
                  '100%': 'rgb(var(--success-6))',
                }"
              />
            </div>
            <div class="progress-item">
              <div class="progress-label">UI测试 ({{ data.summary.ui_count }})</div>
              <a-progress
                :percent="data.summary.ui_in_progress_count / data.summary.ui_count"
                :style="{ width: '50%' }"
                :color="{
                  '0%': 'rgb(var(--primary-6))',
                  '100%': 'rgb(var(--success-6))',
                }"
              />
            </div>
            <div class="progress-item">
              <div class="progress-label">Pytest测试 ({{ data.summary.pytest_count }})</div>
              <a-progress
                :percent="data.summary.pytest_in_progress_count / data.summary.pytest_count"
                :style="{ width: '50%' }"
                :color="{
                  '0%': 'rgb(var(--primary-6))',
                  '100%': 'rgb(var(--success-6))',
                }"
              />
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="测试结果统计">
          <div class="chart-container">
            <a-progress
              type="circle"
              :percent="(data.summary.success_count / data.summary.count) * 100"
              :color="'#52C41A'"
              style="margin-right: 32px"
            >
              <template #text>
                <div class="circle-progress-text">
                  <div>成功率</div>
                  <div
                    >{{ ((data.summary.success_count / data.summary.count) * 100).toFixed(1) }}%
                  </div>
                </div>
              </template>
            </a-progress>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-card class="test-details">
      <template #title>
        <a-space>
          <icon-unordered-list />
          <span>测试用例详情</span>
        </a-space>
      </template>
      <a-table
        :draggable="{ type: 'handle', width: 40 }"
        :bordered="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :loading="table.tableLoading.value"
        :data="table.dataList"
        :columns="tableColumns"
        :pagination="false"
        :rowKey="rowKey"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :title="item.title"
            :width="item.width"
            :data-index="item.key"
            :fixed="item.fixed"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.type]" size="small"
                >{{ enumStore.test_case_type[record.type].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'case_id'" #cell="{ record }">
              {{ record.ui_case?.name || record.api_case?.name || record.pytest_case?.name }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record?.status]" size="small">
                {{ enumStore.task_status[record?.status].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-button type="text" @click="showDetails(record)"> 查看详情</a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <!-- 测试详情抽屉 -->
    <a-drawer v-model:visible="drawerVisible" :width="800" title="测试用例详情">
      <template v-if="data.selectedCase">
        <a-descriptions :column="1" bordered>
          <a-descriptions-item label="用例ID">{{ data.selectedCase?.id }}</a-descriptions-item>
          <a-descriptions-item label="用例名称"
            >{{ data.selectedCase?.case_name }}
          </a-descriptions-item>
          <a-descriptions-item label="项目名称"
            >{{ data.selectedCase?.project_product?.name }}
          </a-descriptions-item>
          <a-descriptions-item label="创建时间"
            >{{ data.selectedCase?.create_time }}
          </a-descriptions-item>
          <a-descriptions-item label="更新时间"
            >{{ data.selectedCase?.update_time }}
          </a-descriptions-item>
          <a-descriptions-item label="执行状态">
            <a-tag :color="enumStore.colors[data?.selectedCase?.status]" size="small">
              {{ enumStore?.task_status[data?.selectedCase?.status]?.title }}
            </a-tag>
          </a-descriptions-item>
        </a-descriptions>
        <div>
          <div v-if="data.caseType === 0">
            <a-card :title="data?.selectedCase.resultData?.name" :bordered="false">
              <ElementTestReport :resultData="data?.selectedCase.resultData" />
            </a-card>
          </div>
          <div v-else-if="data.caseType === 1">
            <a-card :title="data?.selectedCase.resultData?.name" :bordered="false">
              <ApiTestReport :resultData="data?.selectedCase.resultData" />
            </a-card>
          </div>
          <div v-else-if="data.caseType === 2">
            <a-card :title="data?.selectedCase.resultData?.name" :bordered="false">
              <PytestTestReport :resultData="data?.selectedCase.resultData"
                >pytest
              </PytestTestReport>
            </a-card>
          </div>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
  import { ref, computed, reactive, onMounted } from 'vue'
  import {
    IconApps,
    IconCheckCircle,
    IconCloseCircle,
    IconSync,
    IconUnorderedList,
  } from '@arco-design/web-vue/es/icon'
  import PytestTestReport from '@/components/PytestTestReport.vue'
  import ApiTestReport from '@/components/ApiTestReport.vue'
  import ElementTestReport from '@/components/ElementTestReport.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    usePagination,
    useRowKey,
    useRowSelection,
    useTable,
    useTableColumn,
  } from '@/hooks/table'
  import {
    getSystemTestSuiteDetails,
    getSystemTestSuiteDetailsSummary,
  } from '@/api/system/test_sute_details'

  const pagination = usePagination(doRefresh)
  const drawerVisible = ref(false)
  const enumStore = useEnum()

  const table = useTable()
  const rowKey = useRowKey('id')
  const { selectedRowKeys, showCheckedAll } = useRowSelection()
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
    stepName: '',
    treeData: [],
    resultData: {},
    summary: {},
    caseType: null,
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
    {
      title: '进行中',
      value: data.summary.proceed_count,
      icon: IconSync,
      class: 'running',
    },
  ])

  const showDetails = (record: any) => {
    data.selectedCase = record
    drawerVisible.value = true
  }

  function doRefresh() {
    getSystemTestSuiteDetails(232853768174)
      .then((res) => {
        data.datsList = res.data
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function doRefreshSummary() {
    getSystemTestSuiteDetailsSummary(232853768174)
      .then((res) => {
        data.summary = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    doRefresh()
    doRefreshSummary()
  })
</script>

<style scoped></style>
