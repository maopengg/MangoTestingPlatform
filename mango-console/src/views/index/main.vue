<template>
  <div class="main-container">
    <div class="left">
      <div class="item">
        <Title title="测试用例" />
        <EnrollmentChannelsChart ref="enrollmentChannelsChart" :propData="mainData.reportSum" />
      </div>
      <div class="item">
        <Title title="测试结果" />
        <EnrollmentChannelsChart ref="enrollmentChannelsChart" :propData="mainData.caseSum" />
      </div>
      <div class="item">
        <Title title="-" />
        <HotProductChart ref="hotProductChart" />
      </div>
    </div>
    <div class="center">
      <div style="display: flex; flex-direction: column; height: 100%">
        <a-space direction="vertical">
          <a-card>
            <CenterTitle />
          </a-card>
          <a-card style="flex: 1; overflow: hidden">
            <div style="display: flex; flex-direction: column; height: 100%">
              <Title title="近3个月执行用例趋势图" />
              <FullYearSalesChart ref="fullYearSalesChart" />
            </div>
          </a-card>
          <a-card>
            <div style="flex: 1; overflow: auto">
              <a-space direction="vertical" fill>
                <a-tabs @tab-click="(key) => switchType(key)">
                  <a-tab-pane key="0" title="界面自动化" />
                  <a-tab-pane key="1" title="接口自动化" />
                  <a-tab-pane key="2" title="性能自动化" />
                </a-tabs>
                <a-table
                  :bordered="true"
                  :loading="table.tableLoading"
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
                    >
                      <template v-if="item.key === 'index'" #cell="{ record }">
                        <span style="width: 110px; display: inline-block">{{ record.id }}</span>
                      </template>
                      <template v-else-if="item.key === 'project'" #cell="{ record }">
                        {{ record.project.name }}
                      </template>
                      <template v-else-if="item.key === 'run_state'" #cell="{ record }">
                        <a-tag color="red" size="small" v-if="record.run_state === 0">进行中</a-tag>
                        <a-tag color="green" size="small" v-else-if="record.run_state === 1">已完成</a-tag>
                      </template>
                      <template v-else-if="item.key === 'state'" #cell="{ record }">
                        <a-tag color="red" size="small" v-if="record.state === 0">失败</a-tag>
                        <a-tag color="green" size="small" v-else-if="record.state === 1">成功</a-tag>
                        <a-tag color="green" size="small" v-else-if="record.state === null">待测试完成</a-tag>
                      </template>
                      <template v-else-if="item.key === 'actions'" #cell="{ record }">
                        <a-space>
                          <a-button type="text" size="mini" @click="onClick(record)">查看结果</a-button>
                        </a-space>
                      </template>
                    </a-table-column>
                  </template>
                </a-table>
                <TableFooter :pagination="pagination" />
              </a-space>
            </div>
          </a-card>
        </a-space>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, unref, watch, onMounted, nextTick, reactive } from 'vue'
import Title from './components/Title'
import EnrollmentChannelsChart from './components/chart/EnrollmentChannelsChart.vue'
import useAppConfigStore from '@/store/modules/app-config'
import CenterTitle from './components/CenterTitle.vue'
import FullYearSalesChart from './components/chart/FullYearSalesChart.vue'
import HotProductChart from './components/chart/HotProductChart.vue'
import { useProject } from '@/store/modules/get-project'
import { useTestObj } from '@/store/modules/get-test-obj'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { useRouter } from 'vue-router'
import { get } from '@/api/http'
import { testSuiteAllReportSum, testSuiteReport, testSuiteAllCaseSum, SocketAllUserSum } from '@/api/url'

const appStore = useAppConfigStore()
const mainHeight = computed(() => {
  return appStore.mainHeight + 'px'
})

const enrollmentChannelsChart = ref()
const hotProductChart = ref()
const fullYearSalesChart = ref()
const orderChart = ref()
const onResize = () => {
  setTimeout(() => {
    unref(enrollmentChannelsChart).updateChart()
    // unref(weekSalesChart).updateChart()
    unref(hotProductChart).updateChart()
    unref(fullYearSalesChart).updateChart()
    unref(orderChart).updateChart()
  }, 500)
}
const collapse = computed(() => {
  return appStore.isCollapse
})
watch(collapse, () => {
  onResize()
})
const Project = useProject()
const testObj = useTestObj()

const pagination = usePagination(doRefresh)
pagination.pageSize = 9

const { onSelectionChange } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目名称',
    key: 'project',
    dataIndex: 'project',
    width: 150
  },
  // {
  // title: '测试套名称',
  // key: 'name',
  // dataIndex: 'name'
  // },
  {
    title: '执行时间',
    key: 'create_time',
    dataIndex: 'create_time'
  },
  {
    title: '执行状态',
    key: 'run_state',
    dataIndex: 'run_state'
  },
  {
    title: '测试结果',
    key: 'state',
    dataIndex: 'state'
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150
  }
])
const router = useRouter()

function onClick(record: any) {
  router.push({
    path: '/index/report-details',
    query: {
      id: record.id,
      name: record.name
    }
  })
}
const pageType: any = ref('0')

function switchType(key: any) {
  pageType.value = key
  doRefresh()
}
function doRefresh() {
  get({
    url: testSuiteReport,
    data: () => {
      return {
        page: pagination.page,
        pageSize: pagination.pageSize,
        type: pageType.value
      }
    }
  })
    .then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
    .catch(console.log)
}
let mainData = reactive({
  reportSum: [],
  caseSum: [],
  userSum: 0
})
function getAllReportSum() {
  get({
    url: testSuiteAllReportSum,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      mainData.reportSum = res.data
    })
    .catch(console.log)
}
function getAllCaseSum() {
  get({
    url: testSuiteAllCaseSum,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      mainData.caseSum = res.data
    })
    .catch(console.log)
}
function getAllUserSum() {
  get({
    url: SocketAllUserSum,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      mainData.userSum = res.data['sum']
    })
    .catch(console.log)
}
onMounted(() => {
  nextTick(async () => {
    Project.getItems()
    testObj.getEnvironment()
    getAllReportSum()
    getAllCaseSum()
    doRefresh()
    getAllUserSum()
  })
})
</script>

<style lang="less" scoped>
:deep(.arco-card) {
  border-radius: 5px;
  border: none;
  box-shadow: 0px 8px 8px 0px rgba(162, 173, 200, 0.15);
}

:deep(.arco-card-body) {
  padding: 0;
  height: 100%;
}

.main-container {
  display: flex;
  height: v-bind(mainHeight);
  overflow: hidden;

  .left {
    width: 25%;
    display: flex;
    flex-direction: column;
    justify-content: space-evenly;

    .item {
      border-radius: 5px;
      display: flex;
      flex-direction: column;
      height: 100%;
      position: relative;
      background: var(--color-bg-2);
      transition: box-shadow 0.2s cubic-bezier(0, 0, 1, 1);
      box-shadow: 0px 8px 8px 0px rgba(162, 173, 200, 0.15);

      div:nth-last-child(1) {
        flex: 1;
      }
    }

    .item + .item {
      margin-top: 10px;
    }
  }

  .center {
    margin: 0 10px;
    flex: 1;
    overflow: hidden;

    .center-data-item-wrapper {
      display: flex;
      margin: 10px 0;

      .item {
        flex: 1;
      }

      .item + .item {
        margin-left: 10px;
      }
    }
  }

  .right {
    width: 25%;
    display: flex;
    height: 100%;
    overflow: hidden;
    flex-direction: column;

    & > div:nth-child(1) {
      flex: 1;
    }

    & > div:nth-child(2) {
      flex: 2;
      overflow: hidden;
    }

    .item {
      display: flex;
      flex-direction: column;
      height: 100%;
      position: relative;
      background: var(--color-bg-2);
      border-radius: 5px;
      transition: box-shadow 0.2s cubic-bezier(0, 0, 1, 1);
      box-shadow: 0px 8px 8px 0px rgba(162, 173, 200, 0.15);

      & > div:nth-child(2) {
        flex: 1;
      }
    }

    .item + .item {
      margin-top: 10px;
    }
  }
}
</style>
