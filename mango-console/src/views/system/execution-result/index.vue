<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="自动化执行结果"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="selectOptions(item.key)"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'range'">
                <a-range-picker
                  v-model="item.value"
                  show-time
                  value-format="YYYY-MM-DD HH:mm:ss"
                  @change="doRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-spin :loading="data.configLoading">
        <a-alert type="info" show-icon>
          完整执行结果保留 {{ data.config.retention_days || '-' }} 天，定时任务
          {{ data.config.cleanup_cron || '-' }} 执行，下次清理时间
          {{ data.config.next_cleanup_at || '-' }}。清理只移除完整 JSON 或结果文件，执行记录会保留。
          当前有 {{ data.config.expired_pending_count || 0 }} 条过期结果待清理。
        </a-alert>
      </a-spin>

      <TableTabs>
        <template #extra>
          <a-button
            v-if="canCleanup"
            size="small"
            status="danger"
            :loading="data.cleanupLoading"
            @click="onCleanup"
            data-testid="qa-views-system-execution-result-button-手动清理"
          >
            手动清理
          </a-button>
        </template>
      </TableTabs>

      <a-table
        :scroll="{ x: tableScrollX }"
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :rowKey="rowKey"
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
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'source_type'" #cell="{ record }">
              <a-tag :color="optionTagColor('source_type', record.source_type)" size="small">
                {{ record.source_type_name || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'target_type'" #cell="{ record }">
              <a-tag :color="optionTagColor('target_type', record.target_type)" size="small">
                {{ record.target_type_name || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="statusColor(record.status)" size="small">
                {{ record.status_name || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag :color="optionTagColor('test_env', record.test_env)" size="small">
                {{ record.test_env_name || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'duration'" #cell="{ record }">
              {{ formatDuration(record.duration) }}
            </template>
            <template v-else-if="item.key === 'is_latest'" #cell="{ record }">
              <a-tag :color="optionTagColor('is_latest', record.is_latest)" size="small">
                {{ record.is_latest ? '最新结果' : '历史结果' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'result_state'" #cell="{ record }">
              <a-tag :color="resultState(record).color" size="small">
                {{ resultState(record).text }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'result_size'" #cell="{ record }">
              {{ formatBytes(record.result_size) }}
            </template>
            <template
              v-else-if="
                ['test_suite', 'test_suite_detail', 'revision_id', 'release_id'].includes(
                  String(item.key)
                )
              "
              #cell="{ record }"
            >
              {{ record[item.key] ?? '-' }}
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>

    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { getFormItems } from '@/utils/datacleaning'
  import { getUserName } from '@/api/user/user'
  import {
    getExecutionResultAdminConfig,
    getExecutionResultAdminList,
    postExecutionResultAdminCleanup,
  } from '@/api/system/execution_result'
  import usePermissionStore from '@/store/modules/permission'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'
  import { conditionItems, tableColumns, tableScrollX } from './config'
  import TableTabs from '@/components/table/TableTabs.vue'

  const permissionStore = usePermissionStore()
  const enumStore = useEnum()
  const canCleanup = computed(() => permissionStore.hasPermission('system.execution_result:delete'))
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const table = useTable()
  const rowKey = useRowKey('id')
  const data = reactive<any>({
    configLoading: true,
    cleanupLoading: false,
    config: {},
    userOptions: [],
  })

  function selectOptions(key: string | number) {
    if (key === 'trigger_user_id') return data.userOptions
    return data.config[`${String(key)}_options`] || []
  }

  function optionTagColor(key: string, value: string | number) {
    return getEnumTagColor(selectOptions(key), value, enumStore.colors)
  }

  function buildQuery() {
    const values = getFormItems(conditionItems)
    const createTime = Array.isArray(values.create_time) ? values.create_time : []
    delete values.create_time
    if (createTime.length === 2) {
      values.create_time_start = createTime[0]
      values.create_time_end = createTime[1]
    }
    return Object.fromEntries(
      Object.entries(values).filter(
        ([, value]) => value !== '' && value !== null && value !== undefined
      )
    )
  }

  function doRefresh() {
    table.tableLoading.value = true
    return getExecutionResultAdminList({
      ...buildQuery(),
      page: pagination.page,
      pageSize: pagination.pageSize,
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(() => {
        table.tableLoading.value = false
      })
  }

  function loadConfig() {
    data.configLoading = true
    return getExecutionResultAdminConfig()
      .then((res) => {
        data.config = res.data || {}
      })
      .finally(() => {
        data.configLoading = false
      })
  }

  function loadUsers() {
    return getUserName().then((res) => {
      data.userOptions = res.data || []
    })
  }

  function onResetSearch() {
    conditionItems.forEach((item) => {
      item.value = item.type === 'range' || item.multiple ? [] : ''
    })
    doRefresh()
  }

  function onCleanup() {
    const retentionDays = data.config.retention_days || 30
    const pendingCount = data.config.expired_pending_count || 0
    Modal.confirm({
      title: '手动清理执行结果',
      content:
        `确认清理 ${retentionDays} 天前的完整执行结果吗？当前预计有 ${pendingCount} 条待清理。` +
        '该操作会删除完整 JSON 或结果文件，但会保留 execution_result 执行记录。',
      okText: '确认清理',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      onBeforeOk: () => {
        data.cleanupLoading = true
        return postExecutionResultAdminCleanup()
          .then(async (res) => {
            Message.success(`清理完成，共清理 ${res.data?.updated_count || 0} 条完整结果`)
            await Promise.all([loadConfig(), doRefresh()])
          })
          .finally(() => {
            data.cleanupLoading = false
          })
      },
    })
  }

  function statusColor(status: number | null) {
    if (status === 0) return 'red'
    if (status === 1) return 'green'
    if (status === 2) return 'gray'
    if (status === 3) return 'blue'
    if (status === 4) return 'orange'
    return 'gray'
  }

  function resultState(record: any) {
    if (record.result_cleaned) return { text: '已清理', color: 'gray' }
    if (record.has_result_data) return { text: '结果可用', color: 'green' }
    return { text: '无完整结果', color: 'orange' }
  }

  function formatDuration(value: unknown) {
    if (value === null || value === undefined || value === '') return '-'
    const duration = Number(value)
    return Number.isFinite(duration) ? `${duration.toFixed(2)} 秒` : `${value} 秒`
  }

  function formatBytes(value: unknown) {
    const size = Number(value || 0)
    if (!Number.isFinite(size) || size <= 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1)
    return `${(size / 1024 ** index).toFixed(index === 0 ? 0 : 2)} ${units[index]}`
  }

  onMounted(() => {
    nextTick(async () => {
      await Promise.all([enumStore.getEnum(), loadConfig(), loadUsers()])
      doRefresh()
    })
  })
</script>
