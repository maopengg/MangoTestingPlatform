<template>
  <div>
    <div class="main-container">
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
                    <a-input
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      @blur="doRefresh"
                    />
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
                  <template v-else-if="item.type === 'select' && item.key === 'type'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="enumStore.auto_test_type"
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
                    {{
                      record?.project_product?.project?.name + '/' + record?.project_product?.name
                    }}
                  </template>
                  <template v-else-if="item.key === 'test_env'" #cell="{ record }">
                    {{enumStore.environment_type[record.test_env]?.title}}
                  </template>

                  <template v-else-if="item.key === 'user'" #cell="{ record }">
                    {{ record.user?.name }}
                  </template>
                  <template v-else-if="item.key === 'type'" #cell="{ record }">
                    {{enumStore.auto_test_type[record.type].title}}
                  </template>
                  <template v-else-if="item.key === 'status'" #cell="{ record }">
                    <a-tag color="green" size="small" v-if="record.status === 1">通过</a-tag>
                    <a-tag color="red" size="small" v-else-if="record.status === 0">失败</a-tag>
                    <a-tag color="red" size="small" v-else-if="record.status === 2">待开始</a-tag>
                    <a-tag color="red" size="small" v-else-if="record.status === 3">进行中</a-tag>
                  </template>
                  <template v-else-if="item.key === 'actions'" #cell="{ record }">
                    <a-space>
                      <a-button type="text" size="mini" @click="onRetry(record)">重试</a-button>
                    </a-space>
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
  import { conditionItems, tableColumns } from './config'
  import { getSystemTestSuite } from '@/api/system/test_suite'
  import { getSystemTestSuiteDetailsReport } from '@/api/system/test_sute_details'
  import { useEnum } from '@/store/modules/get-enum'

  const enumStore = useEnum()

  const pagination = usePagination(doRefresh)
  pagination.pageSize = 10
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const router = useRouter()
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

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
  }

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    if (record.type == 0) {
      router.push({
        path: '/report/ui/details',
        query: {
          id: record.id,
        },
      })
    } else if (record.type === 1) {
      router.push({
        path: '/report/api/details',
        query: {
          id: record.id,
        },
      })
    }
  }
  function onRetry(record: any) {
      console.log(record);
  }
  const barChart = ref<HTMLElement>()
  const myChart1 = ref<any>()

  function initBarEcharts() {
    myChart1.value = echarts.init(barChart.value!)
    getSystemTestSuiteDetailsReport()
      .then((res) => {
        myChart1.value.setOption({
          tooltip: {
            trigger: 'item',
          },
          xAxis: {
            type: 'category',
            data: [
              '1周',
              '2周',
              '3周',
              '4周',
              '5周',
              '6周',
              '7周',
              '8周',
              '9周',
              '10周',
              '11周',
              '12周',
            ],
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
    getSystemTestSuiteDetailsReport()
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
                    color: '#11a834', // Set the color to green for case pass count #00b42a
                  },
                },
                {
                  value: res.data.failSun,
                  name: '用例失败数',
                  itemStyle: {
                    color: '#d34141', // Set the color to red for case fail count  #f53f3f
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
