<template>
  <div class="main-container">
    <div class="left">
      <div class="item">
        <Title title="用例占比" />
        <PieChart :chartData="data.caseSum" />
      </div>
      <div class="item">
        <Title title="执行占比" />
        <PieChart :chartData="data.reportSum" />
      </div>
      <div class="item">
        <Title title="活跃度" />
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
              <Title title="近3个月执行趋势图" />
              <FullYearSalesChart ref="fullYearSalesChart" />
            </div>
          </a-card>
          <a-card>
            <div style="flex: 1; overflow: auto">
              <a-space direction="vertical" fill>
                <Title style="height: 65px" title="正在准备执行的自动化任务" />
                <a-table
                  :bordered="true"
                  :columns="tableColumns"
                  :data="table.dataList"
                  :loading="table.tableLoading.value"
                  :pagination="false"
                  :rowKey="rowKey"
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
                      <template v-else-if="item.key === 'timing_strategy'" #cell="{ record }">
                        {{ record.timing_strategy?.name }}
                      </template>

                      <template v-else-if="item.key === 'test_env'" #cell="{ record }">
                        <a-tag :color="enumStore.colors[record.test_env]" size="small">
                          {{
                            record.test_env !== null
                              ? enumStore.environment_type[record.test_env].title
                              : ''
                          }}
                        </a-tag>
                      </template>
                      <template v-else-if="item.key === 'actions'" #cell="{ record }">
                        <a-space>
                          <a-button size="mini" type="text" @click="onClick(record)"
                            >查看结果
                          </a-button>
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

<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive, ref, unref, watch } from 'vue'
  import Title from '@/views/index/components/Title'
  import useAppConfigStore from '@/store/modules/app-config'
  import CenterTitle from '@/views/index/components/CenterTitle.vue'
  import FullYearSalesChart from './components/chart/FullYearSalesChart.vue'
  import HotProductChart from './components/chart/HotProductChart.vue'
  import {
    usePagination,
    useRowKey,
    useRowSelection,
    useTable,
    useTableColumn,
  } from '@/hooks/table'
  import { useRouter } from 'vue-router'
  import { getSystemTasks } from '@/api/system/tasks'
  import { useEnum } from '@/store/modules/get-enum'
  import PieChart from '@/components/chart/PieChart.vue'
  import { getSystemCaseRunSum, getSystemCaseSum } from '@/api/system'

  const appStore = useAppConfigStore()
  const mainHeight = computed(() => {
    return appStore.mainHeight + 'px'
  })

  const enumStore = useEnum()
  const hotProductChart = ref()
  const fullYearSalesChart = ref()
  const onResize = () => {
    setTimeout(() => {
      unref(hotProductChart).updateChart()
      unref(fullYearSalesChart).updateChart()
    }, 500)
  }
  const collapse = computed(() => {
    return appStore.isCollapse
  })
  watch(collapse, () => {
    onResize()
  })

  const pagination = usePagination(doRefresh)
  pagination.pageSize = 7

  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const data: any = reactive({
    caseSum: [],
    reportSum: [],
  })
  const tableColumns = useTableColumn([
    table.indexColumn,

    {
      title: '任务名称',
      key: 'name',
      dataIndex: 'name',
      align: 'left',
    },
    {
      title: '测试对象',
      key: 'test_env',
      dataIndex: 'test_env',
      align: 'left',
    },
    {
      title: '定时策略',
      key: 'timing_strategy',
      dataIndex: 'timing_strategy',
      align: 'left',
    },
  ])
  const router = useRouter()

  function onClick(record: any) {
    router.push({
      path: '/index/report-details',
      query: {
        id: record.id,
        name: record.name,
        type: record.type,
      },
    })
  }

  function doRefresh() {
    getSystemTasks({
      pageSize: pagination.pageSize,
      page: pagination.page,
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        caseSum()
        getAllReportSum()
      })
      .catch(console.log)
  }

  function caseSum() {
    getSystemCaseSum()
      .then((res) => {
        data.caseSum = res.data
      })
      .catch(console.log)
  }

  function getAllReportSum() {
    getSystemCaseRunSum()
      .then((res) => {
        data.reportSum = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
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
