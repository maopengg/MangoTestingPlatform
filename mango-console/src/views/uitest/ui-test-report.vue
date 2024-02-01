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
                    <a-input v-model="item.value" :placeholder="item.placeholder" @change="doRefresh" />
                  </template>
                  <template v-else-if="item.type === 'select'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="uiTestReportData.systemStatus"
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
                  <template v-else-if="item.key === 'project'" #cell="{ record }">
                    {{ record.project?.name }}
                  </template>
                  <template v-else-if="item.key === 'test_object'" #cell="{ record }">
                    {{ record.test_object?.name }}
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
import { get } from '@/api/http'
import { systemEnumStatus, systemTestSuiteReport, uiCaseResultWeekSum } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { onMounted, nextTick, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fieldNames } from '@/setting'
import { useProjectModule } from '@/store/modules/project_module'
import * as echarts from 'echarts'
import { getFormItems } from '@/utils/datacleaning'
import { usePageData } from '@/store/page-data'

const projectModule = useProjectModule()

const pagination = usePagination(doRefresh)
pagination.pageSize = 10
const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const router = useRouter()

const uiTestReportData = reactive({
  moduleList: projectModule.data,
  systemStatus: []
})
const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入测试套ID',
    value: '',
    reset: function () {
      this.value = ''
    }
  },
  {
    key: 'status',
    label: '测试结果',
    value: '',
    type: 'select',
    placeholder: '请选择测试结果',
    optionItems: uiTestReportData.systemStatus,
    reset: function () {}
  }
])
const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目名称',
    key: 'project',
    dataIndex: 'project',
    width: 200
  },
  {
    title: '执行环境',
    key: 'test_object',
    dataIndex: 'test_object',
    width: 200
  },
  {
    title: '执行时间',
    key: 'create_time',
    dataIndex: 'create_time',
    width: 200
  },
  {
    title: '执行状态',
    key: 'run_status',
    dataIndex: 'run_status'
  },
  {
    title: '结果',
    key: 'status',
    dataIndex: 'status'
  },
  {
    title: '失败原因',
    key: 'error_message',
    dataIndex: 'error_message',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 400
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150
  }
])

function doRefresh() {
  get({
    url: systemTestSuiteReport,
    data: () => {
      let value = getFormItems(conditionItems)
      value['page'] = pagination.page
      value['pageSize'] = pagination.pageSize
      value['type'] = 0
      return value
    }
  })
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
    path: '/uitest/report/details',
    query: {
      id: record.id
    }
  })
}

const barChart = ref<HTMLElement>()
const myChart1 = ref<any>()

function initBarEcharts() {
  myChart1.value = echarts.init(barChart.value!)
  get({
    url: uiCaseResultWeekSum,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      myChart1.value.setOption({
        tooltip: {
          trigger: 'item'
        },
        xAxis: {
          type: 'category',
          data: ['1周', '2周', '3周', '4周', '5周', '6周', '7周', '8周', '9周', '10周', '11周', '12周']
        },
        legend: {
          data: ['成功', '失败']
        },
        yAxis: {
          type: 'value'
        },
        series: [
          {
            name: '成功',
            data: res.data.success,
            type: 'line',
            itemStyle: {
              color: 'green' // Set the line color to green
            }
          },
          {
            name: '失败',
            data: res.data.fail,
            type: 'line',
            itemStyle: {
              color: 'red' // Set the line color to red
            }
          }
        ]
      })
    })
    .catch(console.log)
}

const pieChart = ref<HTMLElement>()
const myChart2 = ref<any>()

function initPieEcharts() {
  myChart2.value = echarts.init(pieChart.value!)
  get({
    url: uiCaseResultWeekSum,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      myChart2.value.setOption({
        tooltip: {
          trigger: 'item'
        },
        legend: {
          top: '5%',
          left: 'center'
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
              borderWidth: 2
            },
            label: {
              show: true,
              position: 'center'
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 40,
                fontWeight: 'bold'
              }
            },
            labelLine: {
              show: false
            },
            data: [
              {
                value: res.data.successSun,
                name: '用例通过数',
                itemStyle: {
                  color: '#11a834' // Set the color to green for case pass count #00b42a
                }
              },
              {
                value: res.data.failSun,
                name: '用例失败数',
                itemStyle: {
                  color: '#d34141' // Set the color to red for case fail count  #f53f3f
                }
              }
            ]
          }
        ]
      })
    })

    .catch(console.log)
}

function status() {
  get({
    url: systemEnumStatus,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      uiTestReportData.systemStatus = res.data
    })
    .catch(console.log)
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
    initPieEcharts()
    initBarEcharts()
    status()
  })
})
</script>
