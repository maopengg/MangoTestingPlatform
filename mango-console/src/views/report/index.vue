<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="测试报告"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="enumStore.task_status"
                  @change="doRefresh"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-space direction="vertical" fill>
        <div class="report-chart-grid">
          <section class="report-chart-card status-card mango-section-card">
            <Title title="测试用例占比" />
            <StatusChart :success="data.successSum" :fail="data.failSum" :loading="data.chartLoading" />
          </section>

          <section class="report-chart-card trend-card mango-section-card">
            <Title title="近三个月执行用例趋势图" />
            <BarChart
              :success="data.weekSuccessData"
              :fail="data.weekFailData"
              :loading="data.chartLoading"
            />
          </section>
        </div>
        <a-table
          :scrollbar="true"
          :bordered="false"
          :loading="table.tableLoading.value"
          :data="table.dataList"
          :columns="tableColumns"
          :pagination="false"
          :rowKey="rowKey"
          :scroll="{ x: 1100, y: tableScrollHeight() }"
        >
          <template #columns>
            <a-table-column
              v-for="item of tableColumns"
              :key="item.key"
              :align="item.align"
              :title="item.title"
              :width="item.width + 50"
              :data-index="item.key"
              :fixed="item.fixed"
              :ellipsis="item.ellipsis"
              :tooltip="item.tooltip"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                <span class="report-id-cell">{{ record.id }}</span>
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record?.project_product) }}
              </template>
              <template v-else-if="item.key === 'test_env'" #cell="{ record }">
                <a-tag :color="enumStore.status_colors[record.test_env]" size="small"
                  >{{ enumStore.environment_type[record.test_env]?.title }}
                </a-tag>
              </template>

              <template v-else-if="item.key === 'user'" #cell="{ record }">
                {{ record.user?.name }}
              </template>
              <template v-else-if="item.key === 'tasks'" #cell="{ record }">
                {{ record.tasks?.name }}
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-tag :color="enumStore.status_colors[record.status]" size="small"
                  >{{ enumStore.task_status[record.status]?.title || '-' }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'is_notice'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.is_notice]" size="small"
                  >{{ enumStore.test_suite_notice[record.is_notice]?.title || '-' }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    { label: '重试', onClick: () => onRetry(record) },
                    { label: '查看结果', onClick: () => onClick(record) },
                  ]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-space>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { conditionItems, tableColumns } from './config'
  import { getSystemTestSuite } from '@/api/system/test_suite'
  import {
    getSystemTestSuiteDetailsAllRetry,
    getSystemTestSuiteDetailsReport,
  } from '@/api/system/test_sute_details'
  import { useEnum } from '@/store/modules/get-enum'
  import { Message, Modal } from '@arco-design/web-vue'
  import Title from '@/views/index/components/Title.vue'
  import StatusChart from '@/components/chart/StatusChart.vue'
  import BarChart from '@/components/chart/barChart.vue'
  import { formatProjectProductPath } from '@/utils/business-format'

  const enumStore = useEnum()

  const pagination = usePagination(doRefresh)
  pagination.pageSize = 10
  const table = useTable()
  const rowKey = useRowKey('id')
  const router = useRouter()
  const data: any = reactive({
    successSum: 0,
    failSum: 0,
    weekSuccessData: [],
    weekFailData: [],
    chartLoading: false,
  })
  const pollingTimer = ref<NodeJS.Timeout | null>(null)

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function doRefresh() {
    clearPollingTimer()
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getSystemTestSuite(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        const hasRunningItem =
          res.data &&
          Array.isArray(res.data) &&
          res.data.some((item: any) => item.status === 3 || item.status === 2)

        if (hasRunningItem) {
          // 5秒后再次刷新
          pollingTimer.value = setInterval(() => {
            doRefresh()
          }, 5000)
        }
      })
      .catch(console.log)
  }

  function tableScrollHeight() {
    const headerHeight = 460
    const footerHeight = 45
    return `calc(94vh - ${headerHeight}px - ${footerHeight}px)`
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh()
  }

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/report/system/details',
      query: {
        id: record.id,
      },
    })
  }

  function onRetry(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要重试这个测试套的全部用例？',
      cancelText: '取消',
      okText: '重试',
      onBeforeOk: () => {
        return getSystemTestSuiteDetailsAllRetry(record.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      data.chartLoading = true
      getSystemTestSuiteDetailsReport()
        .then((res) => {
          data.weekFailData = res.data.fail
          data.weekSuccessData = res.data.success
          data.failSum = res.data.failSun || 0
          data.successSum = res.data.successSun || 0
        })
        .catch(console.log)
        .finally(() => {
          data.chartLoading = false
        })
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>

<style lang="less" scoped>
  .report-chart-grid {
    display: grid;
    height: 280px;
    margin-bottom: 12px;
    grid-template-columns: minmax(360px, 0.8fr) minmax(520px, 1.2fr);
    gap: 12px;
  }

  .report-chart-card {
    height: 280px;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .report-id-cell {
    display: inline-block;
    width: 110px;
  }

  .status-card :deep(.mango-status-chart),
  .trend-card :deep(.mango-report-trend-chart) {
    flex: 1;
    min-height: 0;
  }

  @media (max-width: 1px) {
    .report-chart-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
