<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="预警监控报告"
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
                  :options="statusOptions"
                  @change="doRefresh"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <a-cascader
                  style="width: 200px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="projectInfo.projectProduct"
                  value-key="key"
                  allow-clear
                  allow-search
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
        <!-- 统计卡片 -->
        <div style="margin-bottom: 10px">
          <a-row :gutter="16">
            <a-col :span="6">
              <a-card :bordered="false">
                <a-statistic
                  title="总报告数"
                  :value="statistics.total"
                  :value-style="{ color: '#1890ff' }"
                />
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card :bordered="false">
                <a-statistic
                  title="成功"
                  :value="statistics.success"
                  :value-style="{ color: '#52c41a' }"
                />
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card :bordered="false">
                <a-statistic
                  title="失败"
                  :value="statistics.fail"
                  :value-style="{ color: '#ff4d4f' }"
                />
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card :bordered="false">
                <a-statistic
                  title="信息"
                  :value="statistics.info"
                  :value-style="{ color: '#faad14' }"
                />
              </a-card>
            </a-col>
          </a-row>
        </div>

        <!-- 报告表格 -->
        <a-table
          :scrollbar="true"
          :bordered="false"
          :loading="table.tableLoading.value"
          :data="table.dataList"
          :columns="tableColumns"
          :pagination="false"
          :rowKey="rowKey"
          :scroll="{ x: 1200, y: tableScrollHeight() }"
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
                <span style="width: 80px; display: inline-block">{{ record.id }}</span>
              </template>
              <template v-else-if="item.key === 'task_name'" #cell="{ record }">
                <a-tag color="blue" size="small">{{ record.task_name }}</a-tag>
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-tag :color="getStatusColor(record.status)" size="small">
                  {{ record.status_display }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'msg'" #cell="{ record }">
                <span :title="record.msg">{{ record.msg }}</span>
              </template>
              <template v-else-if="item.key === 'is_notice'" #cell="{ record }">
                <a-tag :color="record.is_notice === 1 ? 'green' : 'gray'" size="small">
                  {{ record.is_notice === 1 ? '是' : '否' }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'notice_group'" #cell="{ record }">
                {{ record.task_notice_group?.name || '-' }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <a-button type="text" size="mini" class="custom-mini-btn" @click="onViewDetail(record)">
                  查看详情
                </a-button>
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

  <!-- 详情抽屉 -->
  <a-drawer
    v-model:visible="detailDrawer.visible"
    :width="600"
    title="报告详情"
    :footer="false"
  >
    <a-descriptions :column="1" bordered v-if="detailDrawer.data">
      <a-descriptions-item label="报告ID">{{ detailDrawer.data.id }}</a-descriptions-item>
      <a-descriptions-item label="关联任务">
        <a-tag color="blue">{{ detailDrawer.data.task_name }}</a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="状态">
        <a-tag :color="getStatusColor(detailDrawer.data.status)">
          {{ detailDrawer.data.status_display }}
        </a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="创建时间">{{ detailDrawer.data.create_time }}</a-descriptions-item>
      <a-descriptions-item label="是否通知">
        <a-tag :color="detailDrawer.data.is_notice === 1 ? 'green' : 'gray'" size="small">
          {{ detailDrawer.data.is_notice === 1 ? '是' : '否' }}
        </a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="通知组" v-if="detailDrawer.data.task_notice_group">
        <a-tag color="blue">{{ detailDrawer.data.task_notice_group.name }}</a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="消息内容">
        <div style="max-height: 200px; overflow-y: auto; white-space: pre-wrap">
          {{ detailDrawer.data.msg }}
        </div>
      </a-descriptions-item>
      <a-descriptions-item label="详细信息" v-if="detailDrawer.data.send_text">
        <div style="max-height: 300px; overflow-y: auto; white-space: pre-wrap">
          {{ detailDrawer.data.send_text }}
        </div>
      </a-descriptions-item>
    </a-descriptions>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { conditionItems, tableColumns } from './report-config'
  import { getMonitoringReportList } from '@/api/monitoring/report'
  import { useProject } from '@/store/modules/get-project'
  import { MonitoringReport } from '@/api/monitoring/report'

  const projectInfo = useProject()
  const pagination = usePagination(doRefresh)
  pagination.pageSize = 10
  const table = useTable()
  const rowKey = useRowKey('id')

  // 统计信息
  const statistics = reactive({
    total: 0,
    success: 0,
    fail: 0,
    info: 0,
  })

  // 状态选项
  const statusOptions = [
    { key: 0, title: '成功' },
    { key: 1, title: '失败' },
    { key: 2, title: '信息' },
  ]

  // 详情抽屉
  const detailDrawer = reactive({
    visible: false,
    data: null as MonitoringReport | null,
  })

  function getStatusColor(status: number): string {
    const colorMap: Record<number, string> = {
      0: 'green', // 成功
      1: 'red', // 失败
      2: 'orange', // 信息
    }
    return colorMap[status] || 'default'
  }

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getMonitoringReportList(value)
      .then((res: any) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize || 0)
        // 计算统计信息
        calculateStatistics(res.data || [])
      })
      .catch(console.log)
  }

  function calculateStatistics(data: MonitoringReport[]) {
    statistics.total = data.length
    statistics.success = data.filter((item) => item.status === 0).length
    statistics.fail = data.filter((item) => item.status === 1).length
    statistics.info = data.filter((item) => item.status === 2).length
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

  function onViewDetail(record: MonitoringReport) {
    detailDrawer.data = record
    detailDrawer.visible = true
  }

  onMounted(() => {
    nextTick(() => {
      doRefresh()
    })
  })
</script>

<style scoped lang="less">
  :deep(.arco-card-body) {
    padding: 16px;
  }
</style>


