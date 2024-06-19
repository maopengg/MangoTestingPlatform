<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="测试报告" @search="doRefresh" @reset-search="onResetSearch">
            <template #search-content>
              <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.type === 'input'">
                    <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
                  </template>
                  <template v-else-if="item.type === 'select'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="status.data"
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
                <div ref="pieChart" :style="{ width: '100%', height: '250px' }"></div>
              </a-card>

              <a-card style="float: right; width: 70%" :bordered="false">
                <Title title="近三个季度执行用例趋势图" />
                <div ref="barChart" :style="{ width: '100%', height: '250px' }"></div>
              </a-card>
            </div>
            <a-table
              :bordered="false"
              :row-selection="{ selectedRowKeys, showCheckedAll }"
              :loading="table.tableLoading.value"
              :data="table.dataList"
              :columns="tableColumns"
              :pagination="false"
              :rowKey="rowKey"
              @selection-change="onSelectionChange"
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
                    <span style="width: 110px; display: inline-block">{{ record.id }}</span>
                  </template>
                  <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                    {{ record.project_product?.project?.name + '/' + record.project_product?.name }}
                  </template>
                  <template v-else-if="item.key === 'test_object'" #cell="{ record }">
                    {{ uEnvironment.data[record.test_object?.environment].title }}
                  </template>
                  <template v-else-if="item.key === 'user'" #cell="{ record }">
                    {{ record.user?.nickname }}
                  </template>
                  <template v-else-if="item.key === 'run_status'" #cell="{ record }">
                    <a-tag color="red" size="small" v-if="record.run_status === 0">进行中</a-tag>
                    <a-tag color="green" size="small" v-else-if="record.run_status === 1">已完成</a-tag>
                  </template>
                  <template v-else-if="item.key === 'status'" #cell="{ record }">
                    <a-tag color="red" size="small" v-if="record.status === 0">失败</a-tag>
                    <a-tag color="green" size="small" v-else-if="record.status === 1">通过</a-tag>
                    <a-tag color="green" size="small" v-else-if="record.status === null">待测试完成</a-tag>
                  </template>
                  <template v-else-if="item.key === 'actions'" #cell="{ record }">
                    <a-space>
                      <a-button type="text" size="mini" @click="onClick(record)">查看结果</a-button>
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
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { onMounted, nextTick, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { fieldNames } from '@/setting'
  import * as echarts from 'echarts'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { tableColumns, conditionItems } from './config'
  import { getApiResultWeek } from '@/api/apitest'
  import { getSystemTestSuiteReport } from '@/api/system'
  import { useEnvironment } from '@/store/modules/get-environment'
  import { useStatus } from '@/store/modules/status'

  const uEnvironment = useEnvironment()
  const status = useStatus()

  const pagination = usePagination(doRefresh)
  pagination.pageSize = 10
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const router = useRouter()

  function doRefresh() {
    if (uEnvironment.data.length === 0) {
      uEnvironment.getEnvironment()
    }
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    value['type'] = 1
    getSystemTestSuiteReport(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
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
      path: '/apitest/report/details',
      query: {},
    })
  }

  const barChart = ref<HTMLElement>()
  const myChart1 = ref<any>()

  function initBarEcharts() {
    myChart1.value = echarts.init(barChart.value!)
    getApiResultWeek()
      .then((res) => {
        myChart1.value.setOption({
          tooltip: {
            trigger: 'item',
          },
          xAxis: {
            type: 'category',
            data: ['1周', '2周', '3周', '4周', '5周', '6周', '7周', '8周', '9周', '10周', '11周', '12周'],
          },
          legend: {
            data: ['成功', '失败'],
          },
          yAxis: {
            type: 'value',
          },
          series: [
            {
              name: '成功',
              data: res.data.success,
              type: 'line',
              itemStyle: {
                color: 'green', // Set the line color to green
              },
            },
            {
              name: '失败',
              data: res.data.fail,
              type: 'line',
              itemStyle: {
                color: 'red', // Set the line color to red
              },
            },
          ],
        })
      })
      .catch(console.log)
  }

  const pieChart = ref<HTMLElement>()
  const myChart2 = ref<any>()

  function initPieEcharts() {
    myChart2.value = echarts.init(pieChart.value!)
    getApiResultWeek()
      .then((res) => {
        myChart2.value.setOption({
          tooltip: {
            trigger: 'item',
          },
          legend: {
            top: '5%',
            left: 'center',
          },
          series: [
            {
              name: 'Access From',
              type: 'pie',
              radius: ['40%', '70%'],
              avoidLabelOverlap: false,
              itemStyle: {
                borderRadius: 10,
                borderColor: '#fff',
                borderWidth: 2,
              },
              label: {
                show: true,
                position: 'center',
              },
              emphasis: {
                label: {
                  show: true,
                  fontSize: 40,
                  fontWeight: 'bold',
                },
              },
              labelLine: {
                show: false,
              },
              data: [
                {
                  value: res.data.successSun,
                  name: '用例通过数',
                  itemStyle: {
                    color: '#11a834', // Set the color to green for case pass count
                  },
                },
                {
                  value: res.data.failSun,
                  name: '用例失败数',
                  itemStyle: {
                    color: '#d34141', // Set the color to red for case fail count
                  },
                },
              ],
            },
          ],
        })
      })

      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      initPieEcharts()
      initBarEcharts()
    })
  })
</script>
