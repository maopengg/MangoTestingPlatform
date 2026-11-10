<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader
        title="执行记录"
        :show-filter="true"
        @search="onSearchRefresh"
        @reset-search="onReset"
      >
        <template #search-content>
          <a-form layout="inline" :model="query" @keyup.enter="onSearchRefresh">
            <a-form-item label="灰度Key">
              <a-input
                v-model="query.feature_key"
                allow-clear
                placeholder="请输入灰度Key"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-input-请输入灰度key"
              />
            </a-form-item>
            <a-form-item label="目标值">
              <a-input
                v-model="query.target_value"
                allow-clear
                placeholder="请输入目标值"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-input-请输入目标值"
              />
            </a-form-item>
            <a-form-item label="状态">
              <a-select
                v-model="query.status"
                multiple
                :max-tag-count="1"
                :options="executionStatusOptions"
                allow-clear
                placeholder="请选择状态"
                @change="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-select-请选择状态"
              />
            </a-form-item>
            <a-form-item label="配置类型">
              <a-select
                v-model="query.config_type"
                multiple
                :max-tag-count="1"
                :options="configTypeOptions"
                allow-clear
                placeholder="请选择类型"
                @change="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-select-请选择类型"
              />
            </a-form-item>
            <a-form-item label="用例类型">
              <a-select
                v-model="query.case_type"
                multiple
                :max-tag-count="1"
                :options="caseTypeOptions"
                allow-clear
                placeholder="请选择用例类型"
                @change="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-select-请选择用例类型"
              />
            </a-form-item>
            <a-form-item label="用例名称">
              <a-input
                v-model="query.case_name"
                allow-clear
                placeholder="请输入用例名称"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-input-请输入用例名称"
              />
            </a-form-item>
            <a-form-item label="报告ID">
              <a-input
                v-model="query.test_suite_id"
                allow-clear
                placeholder="请输入测试报告ID"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-input-请输入测试报告id"
              />
            </a-form-item>
            <a-form-item label="用例ID">
              <a-input
                v-model="query.case_id"
                allow-clear
                placeholder="请输入用例ID"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-input-请输入用例id"
              />
            </a-form-item>
            <a-form-item label="配置文件">
              <a-select
                v-model="query.yaml_file"
                multiple
                :max-tag-count="1"
                :options="yamlOptions"
                :loading="optionsLoading"
                allow-clear
                allow-search
                placeholder="请选择配置文件"
                @change="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-select-请选择配置文件"
              />
            </a-form-item>
            <a-form-item label="来源分支">
              <a-input
                v-model="query.source_branch"
                allow-clear
                placeholder="请输入来源分支"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-input-请输入来源分支"
              />
            </a-form-item>
            <a-form-item label="目标分支">
              <a-input
                v-model="query.target_branch"
                allow-clear
                placeholder="请输入目标分支"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-execution-log-input-请输入目标分支"
              />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <TableTabs>
        <template #extra>
          <div class="mango-gray-execution-tools">


            <a-button
              size="small"
              status="danger"
              :loading="actions.pending.value?.kind === 'cleanup'"
              :disabled="actionBusy"
              @click="onCleanupExpired"
              data-testid="qa-views-gray-execution-log-button-清理1个月前"
            >
              清理1个月前
            </a-button>
          </div>
        </template>
      </TableTabs>
      <a-table
        :bordered="false"
        :columns="logColumns"
        :data="rows"
        :loading="listLoading"
        :pagination="false"
        :scroll="{ x: grayPageConfig.scrollX }"
        row-key="id"
      >
        <template #columns>
          <a-table-column v-for="item in logColumns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="executionStatusColor(record.status)" size="small">{{
                statusText(record.status)
              }}</a-tag>
            </template>
            <template v-else-if="item.key === 'case'" #cell="{ record }">
              {{ record.case_name || record.case_id || '-' }}
            </template>
            <template v-else-if="item.key === 'merge_request'" #cell="{ record }">
              <a-link
                v-if="externalUrl(record.merge_request_url)"
                :href="externalUrl(record.merge_request_url) || undefined"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ record.merge_request_iid || record.merge_request_id || '查看PR' }}
              </a-link>
              <span v-else>-</span>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions :actions="rowActions(record)" />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>

    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <BaseSidePanel
    :visible="detail.id !== null"
    :title="`灰度执行详情 / ${detail.id ?? '-'}`"
    :width="820"
    cancel-button-text="关闭"
    @update:visible="
      (value) => {
        if (!value) closeDetail()
      }
    "
    @cancel="closeDetail"
  >
    <template #default>
      <div class="mango-gray-execution-detail"
        ><CodeEditor
          v-model="detail.content"
          readonly
          language="json"
          placeholder="暂无详情"
          :code-style="{ height: '100%' }"
      /></div>
    </template>
    <template #footer-buttons>
      <a-button @click="closeDetail" data-testid="qa-views-gray-execution-log-button-关闭"
        >关闭</a-button
      >
    </template>
  </BaseSidePanel>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
    watch,
  } from 'vue'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import TableTabs from '@/components/table/TableTabs.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import { usePagination } from '@/hooks/table'
  import { createIdSearchValue } from '@/utils/id-search'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { getGrayExecutionLog, getGrayYamlFile } from '@/api/gray'
  import {
    caseTypeOptions,
    configTypeOptions,
    executionStatusOptions,
    executionStatusColors,
    grayPageConfig,
  } from './config'
  import {
    canRestore,
    createQuery,
    executionPage,
    externalUrl,
    requestParams as mapParams,
    yamlOptions as mapOptions,
  } from './records'
  import type { ExecutionQuery, ExecutionRow, YamlOption } from './records'
  import { useExecutionActions } from './composables/useExecutionActions'

  const query: ExecutionQuery = reactive({
    ...createQuery(),
    test_suite_id: createIdSearchValue('', false),
    case_id: createIdSearchValue('', false),
  })
  const rows = ref<ExecutionRow[]>([]),
    listLoading = ref(false),
    listError = ref(false)
  const optionRows = ref<YamlOption[]>([]),
    optionsLoading = ref(false),
    optionsError = ref(false)
  const pagination = usePagination(onSearch, listLoading)
  const detail = reactive<{ id: number | null; content: string }>({ id: null, content: '' })
  const user = useUserStore(),
    route = useRoute(),
    viewEpoch = ref(0)
  let active = true,
    mounted = false,
    listSequence = 0,
    optionSequence = 0
  const isPageRoute = () => route.fullPath.split('?')[0] === '/gray/execution-log/index'
  const identityKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      user.userId,
      user.roleId,
      user.token,
      user.selected_environment,
    ])
  )
  const requestKey = computed(() => JSON.stringify(requestParams()))
  const contextKey = computed(() =>
    JSON.stringify([identityKey.value, viewEpoch.value, requestKey.value])
  )
  const actions = useExecutionActions({
    contextKey: () => contextKey.value,
    blocked: () => !active || !isPageRoute(),
    applied: async () => {
      invalidateList(false)
      closeDetail()
      return onSearch()
    },
  })
  const actionBusy = computed(() => !!actions.pending.value || actions.confirming.value)
  const logColumns = grayPageConfig.columns
  const yamlOptions = computed(() => [
    ...optionRows.value,
    ...query.yaml_file
      .filter((id) => !optionRows.value.some((item) => item.value === id))
      .map((id) => ({ value: id, label: `ID ${id}` })),
  ])

  function requestParams() {
    return mapParams(query, pagination.page, pagination.pageSize)
  }
  function invalidateList(clear = true) {
    ++listSequence
    listLoading.value = false
    listError.value = false
    if (clear) {
      rows.value = []
      pagination.setTotalSize(0)
    }
  }
  async function loadOptions(): Promise<boolean> {
    if (!active || !isPageRoute()) return false
    const sequence = ++optionSequence,
      identity = identityKey.value,
      epoch = viewEpoch.value
    const current = () =>
      active &&
      isPageRoute() &&
      sequence === optionSequence &&
      identity === identityKey.value &&
      epoch === viewEpoch.value
    optionsLoading.value = true
    optionsError.value = false
    try {
      const response = await getGrayYamlFile({})
      if (!current()) return false
      optionRows.value = mapOptions(response)
      return true
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), optionsError.value = true)
      return false
    } finally {
      if (current()) optionsLoading.value = false
    }
  }
  async function onSearch(): Promise<boolean> {
    if (!active || !isPageRoute()) {
      listLoading.value = false
      return false
    }
    const sequence = ++listSequence,
      context = contextKey.value,
      params = requestParams()
    const current = () =>
      active && isPageRoute() && sequence === listSequence && context === contextKey.value
    listLoading.value = true
    listError.value = false
    try {
      const response = await getGrayExecutionLog(params)
      if (!current()) return false
      const result = executionPage(response)
      if (result.rows.length > pagination.pageSize) throw Error('Invalid execution page length')
      const lastPage = Math.max(1, Math.ceil(result.total / pagination.pageSize))
      if (pagination.page > lastPage) {
        pagination.page = lastPage
        return await onSearch()
      }
      rows.value = result.rows
      pagination.setTotalSize(result.total)
      return true
    } catch (loadFailure1) {
      if (current()) (reportLoadError(loadFailure1, "加载失败，请重试", false), listError.value = true)
      return false
    } finally {
      if (current()) listLoading.value = false
    }
  }
  function onSearchRefresh() {
    pagination.page = 1
    void onSearch()
  }
  function onReset() {
    Object.assign(query, createQuery())
    pagination.page = 1
    void onSearch()
  }
  function statusText(status: number) {
    return executionStatusOptions.find((item) => item.value === status)?.label ?? '-'
  }
  function executionStatusColor(status: number) {
    return executionStatusColors[status] || 'gray'
  }
  function rowActions(record: ExecutionRow) {
    return [
      { label: '详情', onClick: () => onDetail(record) },
      ...(canRestore(record.status)
        ? [
            {
              label: '恢复',
              loading:
                actions.pending.value?.kind === 'restore' && actions.pending.value.id === record.id,
              disabled: actionBusy.value,
              onClick: () => onRetryRestore(record),
            },
          ]
        : []),
    ]
  }
  function closeDetail() {
    detail.id = null
    detail.content = ''
  }
  function onDetail(record: ExecutionRow) {
    if (!active || !isPageRoute()) return
    const current = rows.value.find((row) => row.id === record.id)
    if (current) {
      detail.id = current.id
      detail.content = current.detail
    }
  }
  function onRetryRestore(record: ExecutionRow) {
    const current = rows.value.find((row) => row.id === record.id)
    if (current) actions.restore({ id: current.id, status: current.status })
  }
  function onCleanupExpired() {
    actions.cleanupExpired()
  }
  function invalidatePage() {
    viewEpoch.value++
    ++optionSequence
    optionRows.value = []
    optionsLoading.value = false
    optionsError.value = false
    invalidateList()
    closeDetail()
  }
  watch(
    requestKey,
    () => {
      invalidateList()
      closeDetail()
    },
    { flush: 'sync' }
  )
  watch(
    identityKey,
    () => {
      invalidatePage()
      pagination.page = 1
      if (mounted && active && isPageRoute()) {
        void onSearch()
        void loadOptions()
      }
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    void onSearch()
    void loadOptions()
  })
  onDeactivated(() => {
    active = false
    invalidatePage()
  })
  onActivated(() => {
    if (active) return
    active = true
    if (mounted) {
      void onSearch()
      void loadOptions()
    }
  })
  onBeforeUnmount(() => {
    active = false
    invalidatePage()
  })
</script>

<style scoped>
  .mango-gray-execution-tools {
    display: flex;
    align-items: center;
    gap: var(--m-page-gap);
  }
  .mango-gray-execution-error {
    color: var(--m-danger);
  }
  .mango-gray-execution-detail {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }
</style>
