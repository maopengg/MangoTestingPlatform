<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader title="预警监控报告" @search="onSearchRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form layout="inline" :model="{}" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="enumStore.monitoring_log_status"
                  @change="onSearchRefresh"
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
      <div class="mango-monitoring-report">
        
        <a-table
          :scroll="{ x: reportTableScrollX }"
          :bordered="false"
          :loading="listLoading"
          :data="rows"
          :columns="tableColumns"
          :pagination="false"
          row-key="id"
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
                <span class="mango-monitoring-report__id">{{ record.id }}</span>
              </template>
              <template v-else-if="item.key === 'task_name'" #cell="{ record }">
                {{ record.task_name }}
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-tag :color="monitoringLogStatusColor(record.status)" size="small"
                  >{{ statusTitle(record) }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'msg'" #cell="{ record }">
                <span :title="record.msg ?? undefined">{{ record.msg }}</span>
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
                <MangoTableActions
                  :actions="[{ label: '查看详情', onClick: () => onViewDetail(record) }]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
      </div>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <!-- 详情抽屉 -->
  <BaseSidePanel v-model:visible="detailVisible" :width="600" title="报告详情" :show-footer="false">
    <a-descriptions :column="1" bordered v-if="selectedReport">
      <a-descriptions-item label="报告ID">{{ selectedReport.id }}</a-descriptions-item>
      <a-descriptions-item label="关联任务">
        <span class="mango-monitoring-report__name">{{ selectedReport.task_name || '-' }}</span>
      </a-descriptions-item>
      <a-descriptions-item label="状态">
        <a-tag :color="monitoringLogStatusColor(selectedReport.status)">
          {{ statusTitle(selectedReport) }}
        </a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="创建时间"
        >{{ selectedReport.create_time }}
      </a-descriptions-item>
      <a-descriptions-item label="是否通知">
        <a-tag :color="selectedReport.is_notice === 1 ? 'green' : 'gray'" size="small">
          {{ selectedReport.is_notice === 1 ? '是' : '否' }}
        </a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="通知组" v-if="selectedReport.task_notice_group">
        <span class="mango-monitoring-report__name">{{ selectedReport.task_notice_group.name }}</span>
      </a-descriptions-item>
      <a-descriptions-item label="消息内容">
        <div class="mango-monitoring-report__text mango-monitoring-report__text--short">
          {{ selectedReport.msg }}
        </div>
      </a-descriptions-item>
      <a-descriptions-item label="详细信息" v-if="selectedReport.send_text">
        <div class="mango-monitoring-report__text">
          {{ selectedReport.send_text }}
        </div>
      </a-descriptions-item>
    </a-descriptions>
  </BaseSidePanel>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { usePagination } from '@/hooks/table'
  import { computed, ref, watch, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
  import { useRoute } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { createConditionItems, tableColumns, reportTableScrollX } from './config'
  import { createReportQuery, readMonitoringReport, readReportPage } from './records'
  import { getMonitoringReportList } from '@/api/monitoring/report'
  import type { MonitoringReport } from '@/api/monitoring/report'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { getStatusTagColor, MONITORING_LOG_STATUS_COLORS } from '@/utils/status-color'

  const conditionItems = createConditionItems()
  const rows = ref<MonitoringReport[]>([])
  const listLoading = ref(false)
  const loadFailed = ref(false)
  const selectedReport = ref<MonitoringReport | null>(null)
  const detailVisible = ref(false)
  const pagination = usePagination(doRefresh, listLoading)
  const enumStore = useEnum()
  const route = useRoute()
  const user = useUserStore()
  const identity = computed(() => JSON.stringify([route.fullPath, user.userId, user.roleId, user.token, user.selected_environment]))
  let requestSequence = 0
  let mounted = false
  let active = false
  let pendingKey: string | null = null
  let pending: Promise<void> | null = null
  const available = () => mounted && active && route.path === '/monitoring/report/index'
  const monitoringLogStatusColor = (value: number) => getStatusTagColor(MONITORING_LOG_STATUS_COLORS, value)
  const statusTitle = (record: MonitoringReport) =>
    enumStore.monitoring_log_status.find(item => String(item.key) === String(record.status))?.title || record.status_display || '-'

  function closeDetail() {
    detailVisible.value = false
    selectedReport.value = null
  }
  watch(detailVisible, visible => { if (!visible) selectedReport.value = null }, { flush: 'sync' })

  function invalidate() {
    ++requestSequence
    pendingKey = null
    pending = null
    rows.value = []
    pagination.setTotalSize(0)
    listLoading.value = false
    loadFailed.value = false
    closeDetail()
  }

  function doRefresh(): Promise<void> {
    if (!available()) { listLoading.value = false; return Promise.resolve() }
    const query = createReportQuery(conditionItems, pagination.page, pagination.pageSize)
    const key = JSON.stringify(query)
    if (pending && pendingKey === key) return pending
    const request = ++requestSequence
    const context = identity.value
    const current = () => available() && request === requestSequence && context === identity.value
    listLoading.value = true
    loadFailed.value = false
    pendingKey = key
    pending = (async () => {
      try {
        const response = await getMonitoringReportList(query)
        if (!current()) return
        const page = readReportPage(response)
        rows.value = page.rows
        pagination.setTotalSize(page.total)
      } catch (loadFailure0) {
        if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true)
      } finally {
        if (current()) {
          listLoading.value = false
          pendingKey = null
          pending = null
        }
      }
    })()
    return pending
  }

  function onSearchRefresh() {
    closeDetail()
    pagination.page = 1
    return doRefresh()
  }
  function onResetSearch() {
    conditionItems.forEach(item => item.reset())
    return onSearchRefresh()
  }
  function onViewDetail(record: MonitoringReport) {
    if (!available()) return
    selectedReport.value = readMonitoringReport(record)
    detailVisible.value = true
  }

  watch(identity, () => {
    invalidate()
    if (available()) void doRefresh()
  }, { flush: 'sync' })
  function resume() {
    if (!mounted || active) return
    active = true
    void doRefresh()
  }
  function suspend() { active = false; invalidate() }
  onMounted(() => { mounted = true; resume() })
  onActivated(resume)
  onDeactivated(suspend)
  onBeforeUnmount(() => { mounted = false; suspend() })
</script>

<style scoped lang="less">
  .mango-monitoring-report { min-width: 0; }
  .mango-monitoring-report__error { margin-bottom: var(--m-page-gap); }
  .mango-monitoring-report__name { overflow-wrap: anywhere; }
  .mango-monitoring-report__text {
    max-height: 300px;
    overflow: auto;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    color: var(--m-text-2);
  }
  .mango-monitoring-report__text--short { max-height: 200px; }
</style>
