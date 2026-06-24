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
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onProjectProductChange"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <ProductModuleSelect
                  v-model="item.value"
                  :auto-clear="false"
                  :project-product-id="currentProjectProductId()"
                  :placeholder="item.placeholder"
                  @change="doRefresh"
                />
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
              <template v-else-if="item.type === 'select' && item.key === 'tasks_id'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="item.optionItems"
                  :loading="data.tasksLoading"
                  @change="doRefresh"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'user'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="item.optionItems"
                  :loading="data.userLoading"
                  @change="doRefresh"
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
          :scroll="{ x: 1280 }"
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
              <template v-else-if="item.key === 'module'" #cell="{ record }">
                {{ record.module ? formatModulePath(record.module) : '-' }}
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
                    { label: '明细', onClick: () => onClick(record) },
                    {
                      label: '通知',
                      loading: data.noticeSendingId === record.id,
                      onClick: () => onSendNotice(record),
                    },
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
  <a-modal
    v-model:visible="data.noticeModalVisible"
    title="发送通知"
    :confirm-loading="data.noticeSending"
    @cancel="onCancelNoticeModal"
    @before-ok="onConfirmNoticeModal"
  >
    <a-form :model="noticeForm">
      <a-form-item label="项目/产品">
        <ProjectProductSelect v-model="noticeForm.project_product" disabled />
      </a-form-item>
      <a-form-item label="通知组" required>
        <a-select
          v-model="noticeForm.notice_group"
          :options="data.noticeList"
          :loading="data.noticeLoading"
          placeholder="请选择通知组"
          allow-clear
          allow-search
          value-key="key"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { conditionItems, tableColumns } from './config'
  import { getSystemTestSuite, postSystemTestSuiteSendNotice } from '@/api/system/test_suite'
  import {
    getSystemTestSuiteDetailsAllRetry,
    getSystemTestSuiteDetailsReport,
  } from '@/api/system/test_sute_details'
  import { getSystemTasks } from '@/api/system/tasks'
  import { useEnum } from '@/store/modules/get-enum'
  import { Message, Modal } from '@arco-design/web-vue'
  import Title from '@/views/index/components/Title.vue'
  import StatusChart from '@/components/chart/StatusChart.vue'
  import BarChart from '@/components/chart/barChart.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { formatModulePath, formatProjectProductPath, getOptionId } from '@/utils/business-format'
  import { getUserName } from '@/api/user/user'
  import { getSystemNoticeName } from '@/api/system/notice_group'

  const enumStore = useEnum()

  const pagination = usePagination(doRefresh)
  const table = useTable()
  const rowKey = useRowKey('id')
  const router = useRouter()
  const data: any = reactive({
    successSum: 0,
    failSum: 0,
    weekSuccessData: [],
    weekFailData: [],
    chartLoading: false,
    tasksLoading: false,
    userLoading: false,
    noticeLoading: false,
    noticeSending: false,
    noticeSendingId: null,
    noticeModalVisible: false,
    noticeList: [],
    noticeRecord: null,
  })
  const noticeForm = reactive({
    project_product: '' as any,
    notice_group: '' as any,
  })
  const pollingTimer = ref<NodeJS.Timeout | null>(null)

  function getConditionItem(key: string) {
    return conditionItems.find((item) => item.key === key)
  }

  function currentProjectProductId() {
    return getOptionId(getConditionItem('project_product')?.value)
  }

  function clearEmptyFilter(value: Record<string, any>, key: string) {
    if (value[key] === null || value[key] === '' || value[key] === undefined) {
      delete value[key]
    }
  }

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function doRefresh() {
    clearPollingTimer()
    let value = getFormItems(conditionItems)
    value['project_product'] = getOptionId(value['project_product'])
    value['module'] = getOptionId(value['module'])
    clearEmptyFilter(value, 'project_product')
    clearEmptyFilter(value, 'module')
    clearEmptyFilter(value, 'tasks_id')
    clearEmptyFilter(value, 'user')
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

  function loadTaskOptions(projectProductId?: number | string | null) {
    data.tasksLoading = true
    const params: Record<string, any> = {}
    if (projectProductId !== null && projectProductId !== '' && projectProductId !== undefined) {
      params.project_product = projectProductId
    }
    return getSystemTasks(params)
      .then((res) => {
        const taskItem = getConditionItem('tasks_id')
        if (taskItem) {
          taskItem.optionItems = (Array.isArray(res.data) ? res.data : []).map((item: any) => ({
            label: item.name || String(item.id),
            value: item.id,
          }))
        }
      })
      .catch(console.log)
      .finally(() => {
        data.tasksLoading = false
      })
  }

  function loadUserOptions() {
    data.userLoading = true
    return getUserName()
      .then((res) => {
        const userItem = getConditionItem('user')
        if (userItem) {
          userItem.optionItems = (Array.isArray(res.data) ? res.data : []).map((item: any) => ({
            label: item.title || item.name || String(item.key || item.id),
            value: item.key ?? item.id,
          }))
        }
      })
      .catch(console.log)
      .finally(() => {
        data.userLoading = false
      })
  }

  function onProjectProductChange() {
    const moduleItem = getConditionItem('module')
    const taskItem = getConditionItem('tasks_id')
    if (moduleItem) {
      moduleItem.value = ''
    }
    if (taskItem) {
      taskItem.value = ''
    }
    loadTaskOptions(currentProjectProductId()).finally(() => {
      doRefresh()
    })
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
    loadTaskOptions().finally(() => {
      doRefresh()
    })
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

  function reportProjectProductId(record: any) {
    return record?.project_product?.id || record?.project_product
  }

  function buildProjectProductValue(record: any) {
    const product = record?.project_product
    if (!product) return ''
    if (product.project?.id && product.id) return [product.project.id, product.id]
    return product.id || ''
  }

  function hasTaskNotice(record: any) {
    return Boolean(record?.tasks?.name && record?.tasks?.notice_group)
  }

  async function sendNotice(record: any, noticeGroup?: number | string) {
    data.noticeSending = true
    data.noticeSendingId = record.id
    try {
      const payload: Record<string, any> = { id: record.id }
      if (noticeGroup) payload.notice_group = noticeGroup
      const res = await postSystemTestSuiteSendNotice(payload)
      Message.success(res.msg)
      data.noticeModalVisible = false
      doRefresh()
      return true
    } catch (error: any) {
      Message.error(error?.msg || '发送通知失败')
      return false
    } finally {
      data.noticeSending = false
      data.noticeSendingId = null
    }
  }

  function onSendNotice(record: any) {
    if (hasTaskNotice(record)) {
      sendNotice(record)
      return
    }
    data.noticeRecord = record
    noticeForm.project_product = buildProjectProductValue(record)
    noticeForm.notice_group = ''
    data.noticeModalVisible = true
    loadNoticeOptions(reportProjectProductId(record))
  }

  function loadNoticeOptions(projectProductId?: number | string | null) {
    if (!projectProductId) {
      data.noticeList = []
      return Promise.resolve()
    }
    data.noticeLoading = true
    return getSystemNoticeName(Number(projectProductId))
      .then((res) => {
        data.noticeList = Array.isArray(res.data) ? res.data : []
      })
      .catch(console.log)
      .finally(() => {
        data.noticeLoading = false
      })
  }

  function onCancelNoticeModal() {
    data.noticeModalVisible = false
    data.noticeRecord = null
    noticeForm.project_product = ''
    noticeForm.notice_group = ''
    data.noticeList = []
  }

  async function onConfirmNoticeModal() {
    if (!noticeForm.notice_group) {
      Message.error('请选择通知组')
      return false
    }
    if (!data.noticeRecord) return false
    return sendNotice(data.noticeRecord, noticeForm.notice_group)
  }

  onMounted(() => {
    nextTick(async () => {
      loadTaskOptions()
      loadUserOptions()
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
    display: flex;
    height: 280px;
    margin-top: 0;
    min-height: 0;
    flex-direction: column;
  }

  .report-id-cell {
    display: inline-block;
    width: 150px;
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
