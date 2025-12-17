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
                  style="width: 150px"
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
        <div style="margin-bottom: 10px">
          <a-card style="float: left; width: 30%" :bordered="false">
            <Title title="接口数&用例数" />
            <StatusChart :success="data.successSum" :fail="data.failSum" />
          </a-card>

          <a-card style="float: right; width: 70%" :bordered="false">
            <Title title="近三个月执行用例趋势图" />
            <BarChart :success="data.weekSuccessData" :fail="data.weekFailData" />
          </a-card>
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
                <span style="width: 110px; display: inline-block">{{ record.id }}</span>
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ record?.project_product?.project?.name + '/' + record?.project_product?.name }}
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
                  >{{ enumStore.task_status[record.status].title }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'is_notice'" #cell="{ record }">
                {{ record.is_notice === 1 ? '已发送' : '未发送' }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <a-space>
                  <a-button type="text" size="mini" class="custom-mini-btn" @click="onRetry(record)"
                    >重试
                  </a-button>
                </a-space>
                <a-space>
                  <a-button type="text" size="mini" class="custom-mini-btn" @click="onClick(record)"
                    >查看结果
                  </a-button>
                </a-space>
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
      path: '/report/details',
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
      onOk: () => {
        getSystemTestSuiteDetailsAllRetry(record.id)
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
      getSystemTestSuiteDetailsReport()
        .then((res) => {
          data.weekFailData = res.data.fail
          data.weekSuccessData = res.data.success
          data.failSum = res.data.failSun || 0
          data.successSum = res.data.successSun || 0
        })
        .catch(console.log)
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>
