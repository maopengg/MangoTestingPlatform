<template>
  <TableBody>
    <template #header>
      <TableHeader
        :show-filter="true"
        title="自动化执行结果"
        @search="onSearch"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearch">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="onSearch" />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="selectOptions(item.key)"
                  :loading="selectLoading(item.key)"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearch"
                />
              </template>
              <template v-else-if="item.type === 'range'">
                <a-range-picker
                  v-model="item.value"
                  show-time
                  value-format="YYYY-MM-DD HH:mm:ss"
                  @change="onSearch"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-spin :loading="configLoading">
        <a-alert v-if="!configError" type="info" show-icon>
          完整执行结果保留 {{ config?.retention_days ?? '-' }} 天，定时任务
          {{ config?.cleanup_cron || '-' }} 执行，下次清理时间
          {{ config?.next_cleanup_at || '-' }}。清理只移除完整 JSON 或结果文件，执行记录会保留。
          当前有 {{ config?.expired_pending_count ?? '-' }} 条过期结果待清理。
        </a-alert>
        <div v-else class="mango-execution-admin-error" role="alert">
          {{ configError }} <a-button size="small" :loading="configLoading" @click="loadConfig">重试</a-button>
        </div>
      </a-spin>
      
      
      

      <TableTabs>
        <template #extra>
          <a-button
            size="small"
            status="danger"
            :loading="cleanupLoading"
            :disabled="!cleanupReady"
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
        :data="rows"
        :loading="listLoading"
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
import { reportLoadError } from '@/utils/load-error'

  import { computed, onMounted, onBeforeUnmount, onActivated, onDeactivated, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { usePagination, useRowKey } from '@/hooks/table'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
  import { getUserName } from '@/api/user/user'
  import { getExecutionResultAdminConfig, getExecutionResultAdminList, postExecutionResultAdminCleanup } from '@/api/system/execution_result'
  import type { ExecutionResultAdminQuery } from '@/api/system/execution_result'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'
  import { createConditionItems, tableColumns, tableScrollX } from './config'
  import { buildExecutionAdminQuery, resetExecutionAdminConditions, parseExecutionAdminRows, parseExecutionAdminConfig, parseExecutionAdminOptions, parseExecutionAdminCleanup } from './execution-admin'
  import type { ExecutionAdminConfig, ExecutionAdminRow, ExecutionAdminOption, ExecutionAdminOptionKey } from './execution-admin'
  import { useExecutionAdminRead } from './composables/useExecutionAdminRead'
  import TableTabs from '@/components/table/TableTabs.vue'

  const route = useRoute(), pagePath = route.path, user = useUserStore(), permission = usePermissionStore(), enumStore = useEnum()
  const conditionItems = createConditionItems(), rows = ref<ExecutionAdminRow[]>([]), config = ref<ExecutionAdminConfig | null>(null)
  const userOptions = ref<ExecutionAdminOption[]>([]), cleanupLoading = ref(false), rowKey = useRowKey('id')
  let mounted = false, active = true, disposed = false, needsLoad = true, epoch = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  let listSnapshot: ExecutionResultAdminQuery = {}
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  const identity = () => JSON.stringify([route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const context = () => JSON.stringify([identity(), epoch])
  const listRead = useExecutionAdminRead({ available, context: () => JSON.stringify([context(), listSnapshot]),
    read: async () => parseExecutionAdminRows(await getExecutionResultAdminList({ ...listSnapshot })),
    apply: value => { rows.value = value.rows; pagination.setTotalSize(value.total) }, clear: () => { rows.value = []; pagination.setTotalSize(0) }, message: '执行结果加载失败，请重试' })
  const { loading: listLoading, error: listError } = listRead
  const pagination = usePagination(doRefresh, listLoading)
  const configRead = useExecutionAdminRead({ available, context, read: async () => parseExecutionAdminConfig(await getExecutionResultAdminConfig()),
    apply: value => { config.value = value }, clear: () => { config.value = null }, message: '保留策略加载失败，请重试' })
  const { loading: configLoading, error: configError, run: loadConfig } = configRead
  const usersRead = useExecutionAdminRead({ available, context, read: async () => parseExecutionAdminOptions(await getUserName()),
    apply: value => { userOptions.value = value }, clear: () => { userOptions.value = [] }, message: '触发人选项加载失败，请重试' })
  const { loading: usersLoading, error: usersError, run: loadUsers } = usersRead
  const enumRead = useExecutionAdminRead({ available, context, read: () => enumStore.getEnum(), apply: () => {}, clear: () => {}, message: '枚举颜色加载失败，请重试' })
  const { loading: enumLoading, error: enumError, run: loadEnums } = enumRead
  const cleanupReady = computed(() => config.value !== null && !configLoading.value && !configError.value)
  function selectOptions(key: string | number): ExecutionAdminOption[] {
    if (key === 'trigger_user_id') return userOptions.value
    switch (key) {
      case 'source_type': case 'target_type': case 'status': case 'test_env': case 'result_state': case 'is_latest': return config.value?.options[key] ?? []
      default: return []
    }
  }
  function selectLoading(key: string | number) { return key === 'trigger_user_id' ? usersLoading.value : configLoading.value }
  function optionTagColor(key: ExecutionAdminOptionKey, value: string | number | boolean | null) {
    return getEnumTagColor(selectOptions(key), typeof value === 'boolean' ? String(value) : value, enumStore.colors)
  }
  function buildQuery() { return buildExecutionAdminQuery(conditionItems) }
  function doRefresh(): Promise<void> {
    if (!available()) { needsLoad = true; listLoading.value = false; return Promise.resolve() }
    try { listSnapshot = { ...buildQuery(), page: pagination.page, pageSize: pagination.pageSize } }
    catch (loadFailure0) { listRead.invalidate(); rows.value = []; pagination.setTotalSize(0); (reportLoadError(loadFailure0, "加载失败，请重试", false), listError.value = '搜索条件无效，请检查 ID 和创建时间'); return Promise.resolve() }
    return listRead.run()
  }
  function onSearch() { pagination.page = 1; return doRefresh() }
  function onResetSearch() { resetExecutionAdminConditions(conditionItems); return onSearch() }
  function onCleanup() {
    if (!available() || cleanupLoading.value || confirmation || !cleanupReady.value || !config.value) return
    const retentionDays = config.value.retention_days, pendingCount = config.value.expired_pending_count, key = context()
    let closed = false
    const valid = () => !closed && available() && key === context() && confirmation === handle
    const close = () => { closed = true; if (confirmation === handle) confirmation = null }
    const handle = Modal.confirm({
      title: '手动清理执行结果',
      content: `确认清理 ${retentionDays} 天前的完整执行结果吗？当前预计有 ${pendingCount} 条待清理。` + '该操作会删除完整 JSON 或结果文件，但会保留 execution_result 执行记录。',
      okText: '确认清理', cancelText: '取消', okButtonProps: { status: 'danger' }, onCancel: close,
      onBeforeOk: async () => {
        if (!valid() || cleanupLoading.value) return false
        if (!cleanupReady.value || config.value?.retention_days !== retentionDays) {
          close(); handle.close(); Message.warning('保留策略已变化，请重新确认清理范围'); return false
        }
        cleanupLoading.value = true
        let applied = false
        try {
          const count = parseExecutionAdminCleanup(await postExecutionResultAdminCleanup())
          if (!valid()) return false
          applied = true
          Message.success(`清理完成，共清理 ${count} 条完整结果`)
          close(); configRead.invalidate(); listRead.invalidate(); void loadConfig(); void doRefresh(); return true
        } catch {
          if (valid()) Message.error('清理失败，请重试')
          return false
        } finally {
          cleanupLoading.value = false
          if (!applied && !valid()) { listRead.invalidate(); configRead.invalidate(); needsLoad = true; resume() }
        }
      },
    })
    confirmation = handle
  }
  function statusColor(status: number | null) {
    if (status === 0) return 'red'
    if (status === 1) return 'green'
    if (status === 2) return 'gray'
    if (status === 3) return 'blue'
    if (status === 4) return 'orange'
    return 'gray'
  }
  function resultState(record: ExecutionAdminRow) {
    if (record.result_cleaned) return { text: '已清理', color: 'gray' }
    if (record.has_result_data) return { text: '结果可用', color: 'green' }
    return { text: '无完整结果', color: 'orange' }
  }
  function formatDuration(value: number | null) { return value === null ? '-' : `${value.toFixed(2)} 秒` }
  function formatBytes(value: number) {
    if (!Number.isFinite(value) || value <= 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB'], index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
    return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 2)} ${units[index]}`
  }
  function pause() {
    epoch++; needsLoad = true
    listRead.invalidate(); configRead.invalidate(); usersRead.invalidate(); enumRead.invalidate()
    confirmation?.close(); confirmation = null
  }
  function resume() {
    if (!available() || !needsLoad) return
    needsLoad = false
    void doRefresh(); void loadConfig(); void loadUsers(); void loadEnums()
  }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
  watch(identity, () => { pause(); rows.value = []; config.value = null; userOptions.value = []; pagination.setTotalSize(0); pagination.page = 1; resume() }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
  onActivated(() => { active = true; resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; pause(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
  .mango-execution-admin-error,
  .mango-execution-admin-feedback {
    padding: var(--m-page-gap);
    color: var(--m-muted);
  }
  .mango-execution-admin-error {
    color: var(--m-danger);
  }
</style>
