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
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.task_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 150px"
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'type'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.auto_test_type"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 150px"
                  value-key="key"
                  @change="doRefresh"
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
          <a-card :bordered="false" style="float: left; width: 30%">
            <Title title="接口数&用例数" />
            <StatusChart :fail="data.failSum" :success="data.successSum" />
          </a-card>

          <a-card :bordered="false" style="float: right; width: 70%">
            <Title title="近三个季度执行用例趋势图" />
            <BarChart :fail="data.weekFailData" :success="data.weekSuccessData" />
          </a-card>
        </div>
        <a-table
          :bordered="false"
          :columns="tableColumns"
          :data="table.dataList"
          :loading="table.tableLoading.value"
          :pagination="false"
          :row-selection="{ selectedRowKeys, showCheckedAll }"
          :rowKey="rowKey"
          :scroll="{ x: 1100, y: tableScrollHeight() }"
          :scrollbar="true"
          @selection-change="onSelectionChange"
        >
          <template #columns>
            <a-table-column
              v-for="item of tableColumns"
              :key="item.key"
              :align="item.align"
              :data-index="item.key"
              :ellipsis="item.ellipsis"
              :fixed="item.fixed"
              :title="item.title"
              :tooltip="item.tooltip"
              :width="item.width"
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
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <a-space>
                  <a-button size="mini" type="text" @click="onRetry(record)">重试</a-button>
                </a-space>
                <a-space>
                  <a-button size="mini" type="text" @click="onClick(record)">查看结果</a-button>
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
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { nextTick, onMounted, reactive } from 'vue'
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
  import { Message } from '@arco-design/web-vue'

  const enumStore = useEnum()

  const pagination = usePagination(doRefresh)
  pagination.pageSize = 10
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const router = useRouter()
  const data: any = reactive({
    successSum: [],
    failSum: [],
    weekSuccessData: [],
    weekFailData: [],
  })

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getSystemTestSuite(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
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
    getSystemTestSuiteDetailsAllRetry(record.id)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getSystemTestSuiteDetailsReport()
        .then((res) => {
          data.weekFailData = res.data.fail
          data.weekSuccessData = res.data.success
          data.failSum = res.data.failSun
          data.successSum = res.data.successSun
        })
        .catch(console.log)
    })
  })
</script>
