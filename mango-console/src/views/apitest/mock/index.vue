<template>
  <TableBody plain class="mango-api-mock-list-page mango-detail-workbench-page">
    <template #header>
      <TableHeader title="Mock服务" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="selectedProduct"
        :reset-key="sidebarResetKey"
        @filter-change="onProjectChange"
        @search="autoSearch.run"
        @reset-search="autoSearch.cancel(); resetFilters(); autoSearch.sync()"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="autoSearch.run">
            <a-form-item label="ID"
              ><a-input @blur="autoSearch.schedule" @clear="autoSearch.schedule" @mouseleave="autoSearch.schedule" v-model="filters.id" allow-clear placeholder="请输入ID"
            /></a-form-item>
            <a-form-item label="接口名称"
              ><a-input @blur="autoSearch.schedule" @clear="autoSearch.schedule" @mouseleave="autoSearch.schedule" v-model="filters.name" allow-clear placeholder="请输入接口名称"
            /></a-form-item>
            <a-form-item label="请求路径"
              ><a-input @blur="autoSearch.schedule" @clear="autoSearch.schedule" @mouseleave="autoSearch.schedule" v-model="filters.mock_key" allow-clear placeholder="请输入路径关键字"
            /></a-form-item>
            <a-form-item label="方法"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.method"
                multiple
                :max-tag-count="1"
                allow-clear
                :options="methodOptions"
                placeholder="请选择方法"
            /></a-form-item>
            <a-form-item label="启用状态"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.enabled"
                multiple
                :max-tag-count="1"
                allow-clear
                :options="booleanOptions"
                placeholder="请选择状态"
            /></a-form-item>
            <a-form-item label="调用记录"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.record_call_log"
                multiple
                :max-tag-count="1"
                allow-clear
                :options="logOptions"
                placeholder="请选择状态"
            /></a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-button size="small" type="primary" @click="createConfig">新增 Mock 接口</a-button>
            <a-button size="small" status="danger" :loading="clearAllLoading" @click="clearAllLogs">
              清空全部 Mock 日志
            </a-button>
          </a-space>
        </template>
        <a-table
          class="mango-native-scroll-table"
          :columns="tableColumns"
          :data="rows"
          :loading="table.tableLoading.value"
          :pagination="false"
          :scroll="{ x: tableScrollX, y: '100%' }"
          row-key="id"
        >
          <template #columns>
            <a-table-column
              v-for="column in tableColumns"
              :key="column.key"
              :align="column.align"
              :data-index="column.dataIndex"
              :ellipsis="column.ellipsis"
              :fixed="column.fixed"
              :title="column.title"
              :tooltip="column.tooltip"
              :width="column.width"
            >
              <template #cell="{ record }">
                <template v-if="column.key === 'index'">{{ record.id }}</template>
                <template v-else-if="column.key === 'mock_url'">
                  <a-tooltip content="点击复制 cURL">
                    <a-link :loading="copyingIds.has(record.id)" @click="copyCurl(record)">{{
                      requestPath(record)
                    }}</a-link>
                  </a-tooltip>
                </template>
                <template v-else-if="column.key === 'method_name'">
                  <a-tag size="small" :color="enumStore.colors[record.method]">
                    {{ record.method_name || '-' }}
                  </a-tag>
                </template>
                <template v-else-if="column.key === 'enabled'">
                  <a-switch
                    :loading="updatingIds.has(record.id)"
                    :disabled="deletingIds.has(record.id)"
                    :model-value="record.enabled"
                    :before-change="(value) => changeState(record, { enabled: value })"
                  />
                </template>
                <template v-else-if="column.key === 'record_call_log'">
                  <a-tooltip content="关闭后合法请求不记录；断言失败和平台异常仍会记录">
                    <a-switch
                      :loading="updatingIds.has(record.id)"
                      :disabled="deletingIds.has(record.id)"
                      :model-value="record.record_call_log"
                      :before-change="(value) => changeState(record, { record_call_log: value })"
                    />
                  </a-tooltip>
                </template>
                <template v-else-if="column.key === 'update_user'">{{
                  record.update_user?.name || '-'
                }}</template>
                <template v-else-if="column.key === 'project_product'">{{
                  formatProjectProductPath(record.project_product)
                }}</template>
                <template v-else-if="column.key === 'actions'">
                  <MangoTableActions
                    :actions="[
                      { label: '配置', onClick: () => openConfig(record.id) },
                      { label: '调用记录', onClick: () => openLogs(record) },
                      {
                        label: '复制 cURL',
                        loading: copyingIds.has(record.id),
                        onClick: () => copyCurl(record),
                      },
                      {
                        label: '删除',
                        danger: true,
                        loading: deletingIds.has(record.id),
                        disabled: updatingIds.has(record.id),
                        onClick: () => removeConfig(record),
                      },
                    ]"
                  />
                </template>
                <template v-else>{{ cellValue(record, column.dataIndex) }}</template>
              </template>
            </a-table-column>
          </template>
        </a-table>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <MockCallLogsPanel
    v-if="logsTarget"
    v-model:visible="logsVisible"
    :mock-id="logsTarget.id"
    :mock-key="logsTarget.mock_key"
  />
</template>

<script lang="ts" setup>
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onMounted,
    onActivated,
    onDeactivated,
    onBeforeUnmount,
    reactive,
    ref,
  } from 'vue'
  import { useRouter } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { useEnum } from '@/store/modules/get-enum'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MockCallLogsPanel from './components/MockCallLogsPanel.vue'
  import {
    clearAllMockLogs,
    deleteMockConfig,
    getMockConfigs,
    getMockEndpointUrl,
    updateMockConfigState,
  } from '@/api/apitest/mock'
  import {
    booleanOptions,
    createMockFilters,
    logOptions,
    methodOptions,
    tableColumns,
    tableScrollX,
  } from './config'
  import { buildMockQuery } from './query'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import type { MockListRecord, MockStatePatch } from './types'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const router = useRouter(),
    enumStore = useEnum(),
    table = useTable()
  const rows = computed(() => table.dataList as MockListRecord[])
  const filters = createMockFilters()
  const selectedProduct = computed<string | number | null>(() =>
    getOptionId(filters.project_product)
  )
  const sidebarResetKey = ref(0),
    clearAllLoading = ref(false),
    logsVisible = ref(false),
    listFailed = ref(false)
  const logsTarget = ref<Pick<MockListRecord, 'id' | 'mock_key'> | null>(null)
  const updatingIds = reactive(new Set<number>()),
    deletingIds = reactive(new Set<number>()),
    copyingIds = reactive(new Set<number>())
  const { beginRequest, isLatestRequest, invalidateRequests } = useLatestRequest()
  const pagination = usePagination(
    () => refresh(true),
    () => table.tableLoading
  )
  let pageActive = true,
    pageVersion = 0,
    mounted = false
  let confirmation: ReturnType<typeof Modal.confirm> | null = null

  function current(version: number) {
    return pageActive && version === pageVersion
  }
  function invalidateList() {
    invalidateRequests()
    table.tableLoading.value = false
  }
  function closeContext() {
    ++pageVersion
    invalidateList()
    confirmation?.close()
    confirmation = null
    logsVisible.value = false
    logsTarget.value = null
  }
  async function refresh(showLoading = true) {
    if (!pageActive) return
    const requestId = beginRequest()
    if (showLoading) table.tableLoading.value = true
    listFailed.value = false
    const params = buildMockQuery(filters, pagination.page, pagination.pageSize)
    try {
      const response = await getMockConfigs(params)
      if (!pageActive || !isLatestRequest(requestId)) return
      table.handleSuccess(response)
      pagination.setTotalSize(response.totalSize)
    } catch (loadFailure0) {
      if (pageActive && isLatestRequest(requestId)) (reportLoadError(loadFailure0, "加载失败，请重试", false), listFailed.value = true)
    } finally {
      if (isLatestRequest(requestId)) table.tableLoading.value = false
    }
  }
  function search() {
    closeContext()
    pagination.page = 1
    void refresh(true)
  }
  function onProjectChange({ projectProduct }: { projectProduct: string | number | null }) {
    filters.project_product = projectProduct
    search()
  }
  function resetFilters() {
    Object.assign(filters, {
      project_product: null,
      id: '',
      name: '',
      mock_key: '',
      method: [],
      enabled: [],
      record_call_log: [],
    })
    sidebarResetKey.value += 1
    search()
  }
  function createConfig() {
    const product = getOptionId(navigationCreateRef.value?.getCreateDefaults().projectProduct)
    router.push({
      path: '/apitest/mock/details',
      query: product !== null && product !== '' ? { project_product: product } : {},
    })
  }
  function openConfig(id: number) {
    router.push({ path: '/apitest/mock/details', query: { id } })
  }
  function openLogs(record: Pick<MockListRecord, 'id' | 'mock_key'>) {
    if (!pageActive) return
    logsTarget.value = { id: record.id, mock_key: record.mock_key }
    logsVisible.value = true
  }
  function cellValue(record: MockListRecord, dataIndex?: string) {
    return dataIndex && dataIndex in record ? record[dataIndex as keyof MockListRecord] ?? '-' : '-'
  }
  function requestPath(record: Pick<MockListRecord, 'mock_key' | 'path'>) {
    return `/${record.mock_key}${record.path && record.path !== '/' ? record.path : ''}`
  }
  async function copyCurl(record: MockListRecord) {
    const id = record.id,
      version = pageVersion
    if (!pageActive || copyingIds.has(id)) return
    const method =
      record.method_name === '全部' ? 'GET' : String(record.method_name || 'GET').split(' / ')[0]
    const url = getMockEndpointUrl(requestPath(record)).replace(/'/g, `'"'"'`)
    copyingIds.add(id)
    try {
      await navigator.clipboard.writeText(`curl -X ${method} '${url}'`)
      if (current(version)) Message.success('cURL 已复制')
    } catch {
      if (current(version)) Message.error('复制失败，请检查剪贴板权限')
    } finally {
      copyingIds.delete(id)
    }
  }
  async function changeState(record: MockListRecord, value: MockStatePatch) {
    const id = record.id,
      version = pageVersion,
      patch = { ...value }
    if (!pageActive || updatingIds.has(id) || deletingIds.has(id)) return false
    updatingIds.add(id)
    invalidateList()
    try {
      await updateMockConfigState(id, patch)
      if (!current(version)) return false
      const index = rows.value.findIndex((item) => item.id === id)
      if (index >= 0) table.dataList.splice(index, 1, { ...rows.value[index], ...patch })
      invalidateList()
      await refresh(false)
      return true
    } catch {
      return false
    } finally {
      updatingIds.delete(id)
    }
  }
  function removeConfig(record: MockListRecord) {
    const id = record.id,
      version = pageVersion
    if (!pageActive || confirmation || updatingIds.has(id) || deletingIds.has(id)) return
    const dialog = Modal.confirm({
      title: '删除 Mock 接口',
      content: '删除后配置及其全部调用记录都会被清理，确认继续吗？',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!current(version) || deletingIds.has(id) || updatingIds.has(id)) return false
        deletingIds.add(id)
        invalidateList()
        try {
          await deleteMockConfig(id)
          if (!current(version)) return true
          Message.success('删除成功')
          if (rows.value.length === 1 && pagination.page > 1) pagination.page--
          await refresh(true)
          return true
        } catch {
          return false
        } finally {
          deletingIds.delete(id)
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  function clearAllLogs() {
    const version = pageVersion
    if (!pageActive || clearAllLoading.value || confirmation) return
    const dialog = Modal.confirm({
      title: '清空全部 Mock 日志',
      content:
        '将暂停 Mock 日志写入，并永久清空所有 Mock 接口的调用记录。该操作会立即释放日志表占用的物理空间，且无法恢复，确认继续吗？',
      okText: '确认全部清空',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (!current(version) || clearAllLoading.value) return false
        clearAllLoading.value = true
        try {
          const response = await clearAllMockLogs()
          if (!current(version)) return true
          logsVisible.value = false
          logsTarget.value = null
          Message.success(`已清空 ${response.data?.deleted_count || 0} 条 Mock 日志`)
          return true
        } catch {
          return false
        } finally {
          clearAllLoading.value = false
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  function deactivate() {
    pageActive = false
    closeContext()
  }
  onMounted(() => {
    mounted = true
    void refresh(true)
  })
  onActivated(() => {
    if (!pageActive) {
      pageActive = true
      if (mounted) void refresh(true)
    }
  })
  onDeactivated(deactivate)
  onBeforeUnmount(deactivate)

  const autoSearch = useDebouncedSearch(search, () => filters)
</script>
