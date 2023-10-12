<template>
  <div class="main-container">
    <div class="center">
      <div style="display: flex; flex-direction: column; height: 100%">
        <div class="center-data-item-wrapper">
          <DataItem class="item" title="界面执行数" :data-model="{ num: 1000, prefix: '', suffix: '', bg: Bg1 }" />
          <DataItem class="item" title="接口执行数" :data-model="{ num: 56100, prefix: '', suffix: '', bg: Bg2 }" />
          <DataItem class="item" title="性能执行数" :data-model="{ num: 3216, prefix: '', suffix: '', bg: Bg3 }" />
        </div>
        <a-card style="flex: 1; overflow: hidden">
          <div style="display: flex; flex-direction: column; height: 100%">
            <Title title="月维度趋势图" />
            <FullYearSalesChart ref="fullYearSalesChart" />
            <div style="flex: 1; overflow: auto">
              <div>
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
                        {{ record.id }}
                      </template>
                      <template v-else-if="item.key === 'project'" #cell="{ record }">
                        {{ record.project.name }}
                      </template>
                      <template v-else-if="item.key === 'run_state'" #cell="{ record }">
                        <a-tag color="green" size="small" v-if="record.state === 1">进行中</a-tag>
                        <a-tag color="red" size="small" v-else-if="record.state === 2">已完成</a-tag>
                      </template>
                      <template v-else-if="item.key === 'state'" #cell="{ record }">
                        <a-tag color="green" size="small" v-if="record.state === 1">进行中</a-tag>
                        <a-tag color="red" size="small" v-else-if="record.state === 2">已完成</a-tag>
                      </template>
                      <template v-else-if="item.key === 'actions'" #cell="{ record }">
                        <a-space>
                          <a-button type="text" size="mini" @click="onViewResults(record)">查看结果</a-button>
                        </a-space>
                      </template>
                    </a-table-column>
                  </template>
                </a-table>
              </div>
            </div>
          </div>
        </a-card>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, ref, unref, watch, onMounted, nextTick } from 'vue'
import useAppConfigStore from '@/store/modules/app-config'
import DataItem from './components/DataItem.vue'
import FullYearSalesChart from './components/chart/FullYearSalesChart.vue'
import Bg1 from '@/assets/bg_item_1.png'
import Bg2 from '@/assets/bg_item_2.png'
import Bg3 from '@/assets/bg_item_3.png'
import { useProject } from '@/store/modules/get-project'
import { useTestObj } from '@/store/modules/get-test-obj'
import Title from './components/Title'
import { Message } from '@arco-design/web-vue'

import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { get } from '@/api/http'
import { uiPage } from '@/api/url'

const pagination = usePagination(doRefresh)
pagination.pageSize = 10
const appStore = useAppConfigStore()
const mainHeight = computed(() => {
  return appStore.mainHeight + 'px'
})
const { onSelectionChange } = useRowSelection()

const enrollmentChannelsChart = ref()
const weekSalesChart = ref()
const hotProductChart = ref()
const fullYearSalesChart = ref()
const orderChart = ref()
const onResize = () => {
  setTimeout(() => {
    unref(enrollmentChannelsChart).updateChart()
    unref(weekSalesChart).updateChart()
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
onMounted(() => {
  nextTick(async () => {
    Project.getItems()
    testObj.getEnvironment()
  })
})
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
  {
    title: '用例名称',
    key: 'name',
    dataIndex: 'name'
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

function onViewResults(record: any) {
  console.log(record)
  Message.success('点击了查询结果')
}
const pageType: any = ref('0')

function switchType(key: any) {
  pageType.value = key
  doRefresh()
}
function doRefresh() {
  get({
    url: uiPage,
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
